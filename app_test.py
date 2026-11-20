
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

import uvicorn

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel, Field

# ============================================================
# 1. BACKEND IMPORTS
# ============================================================

# LangGraph supervisor
from agents.supervisor_test_3 import run_DSA_tutor_agent

# Docker-based Python code executor
from services.code_executor_test import execute_python


# ============================================================
# 2. APPLICATION CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("dsa_tutor")


# ============================================================
# 3. PYDANTIC REQUEST MODELS
# ============================================================

class DSA_tutorRequest(BaseModel):
    """
    Request model for the main DSA tutor endpoint.
    """

    message: str = Field(
        ...,
        min_length=1,
        description="User's question, coding request, or DSA topic.",
    )

    thread_id: str | None = None


class ExecuteRequest(BaseModel):
    """
    Request model for standalone Python code execution.
    """

    code: str = Field(
        ...,
        min_length=1,
        description="Python source code to execute.",
    )

    stdin: str = ""


# ============================================================
# 4. INITIALIZE FASTAPI
# ============================================================

app = FastAPI(
    title="Agentic DSA Tutor Interactive Code Evaluator",
    description=(
        "LangGraph Multi-Agent DSA Tutor "
        "and Interactive Code Evaluator"
    ),
    version="1.1.0",
)


# ============================================================
# 5. STATIC FILES AND TEMPLATES
# ============================================================

if STATIC_DIR.is_dir():

    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )

else:

    logger.warning(
        "Static directory not found: %s",
        STATIC_DIR,
    )


templates = Jinja2Templates(
    directory=str(TEMPLATES_DIR)
)


# ============================================================
# 6. FRONTEND HOME PAGE
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    index_file = TEMPLATES_DIR / "index.html"

    if not index_file.is_file():

        raise HTTPException(
            status_code=500,
            detail="Frontend template templates/index.html was not found.",
        )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


# ============================================================
# 7. MAIN DSA TUTOR API
# ============================================================

@app.post("/api/DSA_tutor")
async def dsa_tutor(
    request_data: DSA_tutorRequest,
):

    user_message = request_data.message.strip()

    # --------------------------------------------------------
    # Validate user input
    # --------------------------------------------------------

    if not user_message:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Message cannot be empty.",
            },
        )

    try:

        logger.info(
            "Processing DSA tutor request. Thread ID: %s",
            request_data.thread_id,
        )

        # ----------------------------------------------------
        # Execute LangGraph supervisor
        # ----------------------------------------------------
        #
        # run_DSA_tutor_agent is synchronous.
        # asyncio.to_thread prevents blocking FastAPI's
        # asynchronous event loop.
        #
        # ----------------------------------------------------

        result: Any = await asyncio.to_thread(
            run_DSA_tutor_agent,
            user_input=user_message,
            thread_id=request_data.thread_id,
        )

        # ----------------------------------------------------
        # Validate supervisor response
        # ----------------------------------------------------

        if not isinstance(result, dict):

            raise TypeError(
                "Supervisor must return a dictionary."
            )

        # ----------------------------------------------------
        # Extract supervisor results
        # ----------------------------------------------------

        response_data = {

            "success": True,

            "thread_id": (
                result.get("thread_id")
                or request_data.thread_id
            ),

            "answer": (
                result.get("answer")
                or ""
            ),

            "generated_challenge": (
                result.get("generated_challenge")
                or ""
            ),

            "student_code": (
                result.get("student_code")
                or ""
            ),

            "execution_result": (
                result.get("execution_result")
                or ""
            ),

            "complexity_analysis": (
                result.get("complexity_analysis")
                or ""
            ),

            "next_agent": (
                result.get("next_agent")
                or ""
            ),

            "llm_calls": result.get(
                "llm_calls",
                0,
            ),
        }

        # ----------------------------------------------------
        # Ensure frontend-compatible string values
        # ----------------------------------------------------
        #
        # Your frontend script.js expects these fields
        # to be strings for Markdown rendering.
        #
        # ----------------------------------------------------

        string_fields = [

            "answer",

            "generated_challenge",

            "student_code",

            "execution_result",

            "complexity_analysis",

            "next_agent",

        ]

        for field in string_fields:

            value = response_data[field]

            if not isinstance(value, str):

                response_data[field] = str(value)

        logger.info(
            "DSA tutor request completed successfully."
        )

        # ----------------------------------------------------
        # Return response to frontend
        # ----------------------------------------------------

        return JSONResponse(
            content=response_data
        )

    except Exception:

        logger.exception(
            "Error while processing DSA tutor request."
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": (
                    "The DSA tutor could not process "
                    "your request. Check the server logs "
                    "for details."
                ),
            },
        )


# ============================================================
# 8. STANDALONE PYTHON CODE EXECUTION API
# ============================================================

@app.post("/api/execute")
async def execute(
    payload: ExecuteRequest,
):

    code = payload.code.strip()

    # --------------------------------------------------------
    # Validate code
    # --------------------------------------------------------

    if not code:

        raise HTTPException(
            status_code=400,
            detail="Enter Python code before running.",
        )

    # --------------------------------------------------------
    # Code size limit
    # --------------------------------------------------------

    max_code_bytes = int(
        os.getenv(
            "DSA_MAX_CODE_CHARS",
            "50000",
        )
    )

    if len(code.encode("utf-8")) > max_code_bytes:

        raise HTTPException(
            status_code=413,
            detail=(
                f"Code exceeds the configured "
                f"{max_code_bytes}-byte limit."
            ),
        )

    try:

        logger.info(
            "Executing submitted Python code."
        )

        # ----------------------------------------------------
        # Execute code inside Docker
        # ----------------------------------------------------
        #
        # Docker execution is synchronous.
        # Run it in a worker thread to avoid blocking
        # FastAPI's event loop.
        #
        # ----------------------------------------------------

        result = await asyncio.to_thread(
            execute_python,
            code,
            payload.stdin,
        )

        if not isinstance(result, dict):

            raise TypeError(
                "execute_python must return a dictionary."
            )

        # ----------------------------------------------------
        # Return execution result
        # ----------------------------------------------------

        return {
            "success": True,
            **result,
        }

    except RuntimeError as exc:

        logger.warning(
            "Code execution service unavailable: %s",
            exc,
        )

        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except HTTPException:

        raise

    except Exception as exc:

        logger.exception(
            "Python code execution failed."
        )

        raise HTTPException(
            status_code=500,
            detail="Code execution service failed.",
        ) from exc


# ============================================================
# 9. HEALTH CHECK API
# ============================================================

@app.get("/health")
async def health_check():

    return {

        "status": "ok",

        "message": (
            "Agentic DSA tutor API is running"
        ),

    }


# ============================================================
# 10. FAVICON
# ============================================================

@app.get("/favicon.ico")
async def favicon():

    return JSONResponse(
        content={}
    )


# ============================================================
# 11. APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":

    uvicorn.run(

        "app:app",

        host=os.getenv(
            "HOST",
            "127.0.0.1",
        ),

        port=int(
            os.getenv(
                "PORT",
                "8000",
            )
        ),

        reload=os.getenv(
            "RELOAD",
            "true",
        ).lower() == "true",

    )
