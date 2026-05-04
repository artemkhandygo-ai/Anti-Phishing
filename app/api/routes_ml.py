from __future__ import annotations

import json
from pathlib import Path

import joblib
import sklearn
from celery.result import AsyncResult
from fastapi import APIRouter

from app.core.config import settings
from app.ml.model_loader import get_model_bundle_metadata
from app.tasks.celery_app import celery_app
from app.tasks.training_tasks import train_model_task

router = APIRouter(prefix="/ml", tags=["ml"])


@router.post(
    "/train",
    summary="Запустить обучение модели",
    description="Ставит задачу обучения в очередь trainer-сервиса.",
)
def train():
    task = train_model_task.delay()
    model_path = Path(settings.MODEL_PATH)
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "Training started in a separate trainer service.",
        "model_path": str(model_path),
        "model_exists": model_path.exists(),
    }


@router.get(
    "/train/status/{task_id}",
    summary="Статус обучения модели",
    description="Показывает состояние задачи обучения по task_id.",
)
def train_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    payload = {
        "task_id": task_id,
        "state": result.state,
    }
    if result.state == "STARTED" and result.info:
        payload["meta"] = result.info
    elif result.successful():
        payload["result"] = result.result
    elif result.failed():
        payload["error"] = str(result.result)
        if getattr(result, "info", None):
            payload["meta"] = result.info
    return payload


@router.get(
    "/model/info",
    summary="Информация о текущей модели",
    description="Показывает путь к модели, наличие файла модели, сведения о runtime и последние метрики обучения.",
)
def model_info():
    model_path = Path(settings.MODEL_PATH)
    metrics_path = Path("data/models/train_metrics.json")
    info = {
        **get_model_bundle_metadata(),
        "metrics_path": str(metrics_path),
        "metrics_exists": metrics_path.exists(),
        "runtime_joblib_version": joblib.__version__,
        "runtime_sklearn_version": sklearn.__version__,
    }
    if metrics_path.exists():
        try:
            info["metrics"] = json.loads(metrics_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    if model_path.exists() and "trained_with_sklearn_version" in info:
        info["version_match"] = info.get("trained_with_sklearn_version") == sklearn.__version__
    return info
