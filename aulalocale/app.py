"""Local, single-user API. Start with uvicorn aulalocale.app:app."""
from contextlib import asynccontextmanager, closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4
import hmac
import os
import sqlite3
from threading import Lock

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .lessons import lessons_router, migrate_lessons
from .enhancement import AudioWorker, enhancement_router, migrate_enhancement
from .models import ModelManager, models_router
from .materials import migrate_materials, materials_router
from .study import StudyEngine, study_router, migrate_study


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


def create_app(data_dir: Path | None = None, token: str | None = None, bootstrap_nonce: str | None = None, shutdown_callback=None) -> FastAPI:
    secret = token if token is not None else os.environ.get("AULALOCALE_TOKEN", "")
    root = data_dir if data_dir is not None else Path(os.environ.get("AULALOCALE_DATA_DIR", "data"))
    database = root / "aulalocale.sqlite3"

    def connect():
        connection = sqlite3.connect(database, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    worker = AudioWorker(root, connect)
    models = ModelManager(root)
    worker.models = models
    study = StudyEngine(root, connect, worker, models)
    worker.study = study
    from .speakers import SpeakerService,speakers_router
    from .recording import recording_router
    speakers=SpeakerService(root,connect,worker,models);study.speakers=speakers

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
            migrate_enhancement(connection)
            migrate_study(connection)
            migrate_materials(connection)
        worker.start()
        try:
            yield
        finally:
            worker.stop()
            models.close()

    api = FastAPI(title="AulaLocale", version="0.9.0", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    bearer = HTTPBearer(auto_error=False)

    session_cookie = "aulalocale_session_" + hmac.new(secret.encode(), b"cookie-name", "sha256").hexdigest()[:12]
    bootstrap_lock = Lock()
    session_value = hmac.new(secret.encode(), b"browser-session-v1", "sha256").hexdigest()

    def unauthorized():
        raise HTTPException(status_code=401, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Bearer"})

    def authenticate(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if credentials is not None:
            if not hmac.compare_digest(credentials.credentials.encode(), secret.encode()):
                unauthorized()
            return
        cookie = request.cookies.get(session_cookie, "")
        if not cookie or not hmac.compare_digest(cookie.encode(), session_value.encode()):
            unauthorized()
        expected_origin = str(request.base_url).rstrip("/")
        origin = request.headers.get("origin")
        if (origin and origin != expected_origin) or request.headers.get("sec-fetch-site") in {"cross-site", "same-site"}:
            raise HTTPException(403, "Cross-origin session request refused")
        if request.method not in {"GET", "HEAD", "OPTIONS"} and origin != expected_origin:
            raise HTTPException(403, "Same-origin request required")

    @api.get("/api/v1/environment", dependencies=[Depends(authenticate)])
    def environment():
        return {"desktop": shutdown_callback is not None}

    @api.post("/api/v1/desktop-session", status_code=204)
    def desktop_session(request: Request, response: Response):
        nonlocal bootstrap_nonce
        supplied = request.headers.get("X-Desktop-Access", "")
        if request.headers.get("origin") != str(request.base_url).rstrip("/"):
            raise HTTPException(403, "Same-origin request required")
        with bootstrap_lock:
            if not bootstrap_nonce or not hmac.compare_digest(supplied.encode(), bootstrap_nonce.encode()):
                unauthorized()
            bootstrap_nonce = None
        response.set_cookie(session_cookie, session_value, httponly=True, samesite="strict",
                            secure=request.url.scheme == "https", path="/api/v1", max_age=28800)
        response.headers["Cache-Control"] = "no-store"

    @api.post("/api/v1/shutdown", status_code=204, dependencies=[Depends(authenticate)])
    def shutdown(response: Response):
        if shutdown_callback is None:
            raise HTTPException(404, "Only available in desktop mode")
        from starlette.background import BackgroundTask
        return Response(status_code=204, background=BackgroundTask(shutdown_callback))

    @api.post("/api/v1/session", status_code=204)
    def login(request: Request, response: Response,
              credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if credentials is None or not hmac.compare_digest(credentials.credentials.encode(), secret.encode()):
            unauthorized()
        response.set_cookie(session_cookie, session_value, httponly=True, samesite="strict",
                            secure=request.url.scheme == "https", path="/api/v1", max_age=28800)
        response.headers["Cache-Control"] = "no-store"

    @api.delete("/api/v1/session", status_code=204, dependencies=[Depends(authenticate)])
    def logout(response: Response):
        response.delete_cookie(session_cookie, path="/api/v1", httponly=True, samesite="strict")
        response.headers["Cache-Control"] = "no-store"

    api.include_router(speakers_router(speakers,study,authenticate))
    api.include_router(recording_router(root,connect,authenticate))

    web = Path(__file__).parent / "web"
    api.mount("/static", StaticFiles(directory=web), name="static")

    @api.get("/", include_in_schema=False)
    def interface():
        return FileResponse(web / "index.html", headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self' blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
            "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"})

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
    api.include_router(enhancement_router(root, connect, authenticate, worker))
    api.include_router(models_router(models, authenticate))
    api.include_router(study_router(study, authenticate))
    api.include_router(materials_router(root, connect, authenticate, worker))
    return api


app = create_app()
