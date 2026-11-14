"""Local, single-user API. Start with uvicorn aulalocale.app:app."""
from contextlib import asynccontextmanager, closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4
import hmac
import os
import sqlite3

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .lessons import lessons_router, migrate_lessons


class SubjectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)

    @field_validator("title", "description", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class Subject(SubjectInput):
    id: UUID
    created_at: datetime


def create_app(data_dir: Path | None = None, token: str | None = None) -> FastAPI:
    secret = token if token is not None else os.environ.get("AULALOCALE_TOKEN", "")
    root = data_dir if data_dir is not None else Path(os.environ.get("AULALOCALE_DATA_DIR", "data"))
    database = root / "aulalocale.sqlite3"

    def connect():
        connection = sqlite3.connect(database, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @asynccontextmanager
    async def lifespan(application):
        if len(secret) < 32 or not secret.isascii():
            raise RuntimeError("AULALOCALE_TOKEN must contain at least 32 ASCII characters")
        root.mkdir(parents=True, exist_ok=True)
        with closing(connect()) as connection, connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS subjects (
                id TEXT PRIMARY KEY, title TEXT NOT NULL,
                description TEXT NOT NULL, created_at TEXT NOT NULL)""")
            migrate_lessons(connection)
        yield

    api = FastAPI(title="AulaLocale", version="0.2.0", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    bearer = HTTPBearer(auto_error=False)

    def authenticate(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if credentials is None or not hmac.compare_digest(
            credentials.credentials.encode(), secret.encode()
        ):
            raise HTTPException(status_code=401, detail="Unauthorized",
                                headers={"WWW-Authenticate": "Bearer"})

    @api.get("/health")
    def health():
        return {"status": "ok"}

    @api.post("/api/v1/subjects", response_model=Subject, status_code=201,
              dependencies=[Depends(authenticate)])
    def create_subject(subject: SubjectInput):
        record = dict(id=str(uuid4()), title=subject.title,
                      description=subject.description,
                      created_at=datetime.now(timezone.utc).isoformat())
        with closing(connect()) as connection, connection:
            connection.execute(
                "INSERT INTO subjects (id,title,description,created_at) VALUES (:id,:title,:description,:created_at)", record)
        return record

    @api.get("/api/v1/subjects", response_model=list[Subject],
             dependencies=[Depends(authenticate)])
    def list_subjects(limit: int = 50, offset: int = 0):
        if not 1 <= limit <= 200 or offset < 0:
            raise HTTPException(status_code=422, detail="Invalid pagination")
        with closing(connect()) as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM subjects ORDER BY created_at, id LIMIT ? OFFSET ?", (limit, offset))]

    @api.get("/api/v1/subjects/{subject_id}", response_model=Subject,
             dependencies=[Depends(authenticate)])
    def get_subject(subject_id: UUID):
        with closing(connect()) as connection:
            record = connection.execute("SELECT * FROM subjects WHERE id = ?", (str(subject_id),)).fetchone()
        if record is None:
            raise HTTPException(status_code=404, detail="Subject not found")
        return dict(record)

    api.include_router(lessons_router(root, connect, authenticate))
    return api


app = create_app()
