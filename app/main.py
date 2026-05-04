from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes_emails import router as emails_router
from app.api.routes_health import router as health_router
from app.api.routes_incidents import router as incidents_router
from app.api.routes_ml import router as ml_router
from app.api.routes_stats import router as stats_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.migrate import run_migrations

configure_logging()

openapi_tags = [
    {"name": "health", "description": "Быстрая проверка, что API запущено и отвечает."},
    {"name": "incidents", "description": "Список инцидентов и экспорт результатов анализа."},
    {"name": "ml", "description": "Запуск обучения модели и просмотр информации о текущей модели."},
]

app = FastAPI(
    title="Anti-Phishing",
    description="",
    version="1.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_tags=openapi_tags,
)

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

app.include_router(health_router)
app.include_router(emails_router)
app.include_router(incidents_router)
app.include_router(stats_router)
app.include_router(ml_router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.on_event("startup")
def on_startup() -> None:
    if settings.AUTO_MIGRATE:
        run_migrations()


@app.get("/docs", include_in_schema=False)
def custom_docs() -> HTMLResponse:
    template_path = Path(__file__).parent / "templates" / "docs.html"
    html = template_path.read_text(encoding="utf-8").format(openapi_url=app.openapi_url)
    return HTMLResponse(html)
