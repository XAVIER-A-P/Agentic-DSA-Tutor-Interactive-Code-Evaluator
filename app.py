from pathlib import Path
import traceback
import uvicorn
import logging
import os
import asyncio

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from agents.supervisor import run_DSA_tutor_agent
from services.code_executor import execute_python
from schemas.requests import TutorRequest, ExecuteRequest

BASE_DIR = Path(__file__).resolve().parent
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("dsa_tutor")

app = FastAPI(
    title="Agentic DSA Tutor Interactive Code Evaluator",
    description="LagGraph Multi-Agent DSA Tutor & Interactive Code Evaluator",
    version="1.0.0"
)


app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)


templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)



class DSA_tutorRequest(BaseModel):
    message: str
    thread_id: str | None = None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


@app.post("/api/DSA_tutor")
async def dsa_tutor(request_data: DSA_tutorRequest):
    try:
        user_message = request_data.message.strip()

        if not user_message:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Message cannot be empty."
                }
            )

        result = run_DSA_tutor_agent(
            user_input=user_message,
            thread_id=request_data.thread_id
        )

        return JSONResponse(
            content={
                "success": True,
                "thread_id": result["thread_id"],
                "answer": result["answer"],
                "generated_challenge": result["generated_challenge"],
                "student_code": result["student_code"],
                "execution_result": result["execution_result"],
                "complexity_analysis": result["complexity_analysis"],
                "next_agent": result["next_agent"],
                "llm_calls": result["llm_calls"]
            }
        )

    except Exception as e:
        print("ERROR:", e)
        traceback.print_exc()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )


@app.get("/health")
async def health_check():
    return{
        "status": "ok",
        "message": "Agentic DSA tutor API is running"
    }


@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(content={})


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
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
    