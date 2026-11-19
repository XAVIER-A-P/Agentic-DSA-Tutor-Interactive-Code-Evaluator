from __future__ import annotations

import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel, Field

from agents.supervisor_test_2 import run_DSA_tutor_agent
from services.code_executor import execute_python
from schemas.requests import TutorRequest, ExecuteRequest

BASE_DIR = Path(__file__).resolve().parent
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("dsa_tutor")

app = FastAPI(
    title="Agentic DSA Tutor",
    description="Multi-agent DSA learning and isolated Python code evaluation",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agentic-dsa-tutor"}


@app.post("/api/tutor")
async def tutor(payload: TutorRequest):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    thread_id = payload.thread_id or str(uuid.uuid4())
    try:
        result = await asyncio.to_thread(run_DSA_tutor_agent, message, thread_id)
        return {"success": True, **result}
    except Exception:
        logger.exception("Tutor agent failed")
        raise HTTPException(status_code=500, detail="The tutor workflow failed. Check server logs.")


@app.post("/api/execute")
async def execute(payload: ExecuteRequest):
    code = payload.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="Enter Python code before running.")
    if len(code.encode("utf-8")) > 50_000:
        raise HTTPException(status_code=413, detail="Code exceeds the 50 KB limit.")
    try:
        result = await asyncio.to_thread(execute_python, code, payload.stdin)
        return {"success": True, **result}
    except RuntimeError as exc:
        logger.warning("Execution service unavailable: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Code execution failed")
        raise HTTPException(status_code=500, detail="Code execution service failed.")


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
