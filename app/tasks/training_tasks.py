from __future__ import annotations

import json
import traceback
from pathlib import Path

from app.core.config import settings
from app.ml.model_loader import refresh_model_cache
from app.ml.train import train_model
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="app.tasks.training_tasks.train_model_task", track_started=True)
def train_model_task(self) -> dict:
    try:
        self.update_state(state="STARTED", meta={"stage": "loading_datasets"})
        dataset_dir = Path("data/datasets")
        dataset_paths = sorted(str(path) for path in dataset_dir.glob("*.csv"))
        self.update_state(state="STARTED", meta={"stage": "training", "datasets": dataset_paths})
        metrics = train_model(dataset_paths)
        refresh_model_cache()
        out_path = Path("data/models/train_metrics.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "status": "completed",
            "model_path": str(settings.MODEL_PATH),
            "metrics_path": str(out_path),
            "metrics": metrics,
        }
    except Exception as exc:
        traceback.print_exc()
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise
