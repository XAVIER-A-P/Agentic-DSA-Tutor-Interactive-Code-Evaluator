from pathlib import Path
import traceback
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from agents.supervisor import run_DSA_tutor_agent

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Agentic DSA Tutor Interactive Code Evaluator",
    description="LagGraph Multi-Agent DSA Tutor Interactive Code Evaluator",
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