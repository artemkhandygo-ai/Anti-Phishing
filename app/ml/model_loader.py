from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import sklearn

from app.core.config import settings


def _model_path() -> Path:
    return Path(settings.MODEL_PATH)


@lru_cache(maxsize=1)
def load_model() -> Any | None:
    path = _model_path()
    if not path.exists():
        return None
    return joblib.load(path)


@lru_cache(maxsize=1)
def load_model_file_metadata() -> dict[str, Any]:
    path = _model_path()
    if not path.exists():
        return {
            "model_path": str(path),
            "model_exists": False,
            "model_size_bytes": 0,
            "model_mtime": None,
            "loaded_in_memory": False,
            "runtime_sklearn_version": sklearn.__version__,
        }
    stat = path.stat()
    return {
        "model_path": str(path),
        "model_exists": True,
        "model_size_bytes": stat.st_size,
        "model_mtime": stat.st_mtime,
        "loaded_in_memory": True,
        "runtime_sklearn_version": sklearn.__version__,
    }


def refresh_model_cache() -> None:
    load_model.cache_clear()
    load_model_file_metadata.cache_clear()


def get_model_bundle_metadata() -> dict[str, Any]:
    model = load_model()
    info = load_model_file_metadata().copy()
    if isinstance(model, dict):
        metadata = model.get("metadata", {}) or {}
        info.update({
            "model_type": model.get("type"),
            "trained_with_sklearn_version": metadata.get("trained_with_sklearn_version"),
            "training_completed_at": metadata.get("training_completed_at"),
            "dataset_count": metadata.get("dataset_count"),
            "samples": metadata.get("samples"),
            "labels_distribution": metadata.get("labels_distribution"),
            "sources": metadata.get("sources"),
            "components": metadata.get("components") or [
                "word_tfidf_sgd",
                "char_tfidf_sgd",
                "tabular_random_forest",
            ],
            "blend_weights": model.get("blend_weights"),
            "thresholds": model.get("thresholds"),
        })
    return info
