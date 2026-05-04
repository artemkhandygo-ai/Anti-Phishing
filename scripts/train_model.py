from pathlib import Path
import json

from app.core.config import settings
from app.ml.train import train_model


def main():
    dataset_dir = Path("data/datasets")
    dataset_paths = sorted(str(path) for path in dataset_dir.glob("*.csv"))
    metrics = train_model(dataset_paths)
    out_path = Path("data/models/train_metrics.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"\nModel saved to: {settings.MODEL_PATH}")
    print(f"Metrics saved to: {out_path}")


if __name__ == "__main__":
    main()
