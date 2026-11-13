from pydantic import BaseModel, Field


class TutorRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    thread_id: str | None = Field(default=None, max_length=128)


class ExecuteRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50000)
    stdin: str = Field(default="", max_length=10000)
