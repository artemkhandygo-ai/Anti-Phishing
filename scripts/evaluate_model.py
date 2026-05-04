from pathlib import Path
from joblib import load


if __name__ == "__main__":
    model_path = Path("data/models/phishguard_model.joblib")
    if not model_path.exists():
        print("Model not found")
    else:
        print(f"Model exists: {model_path}")
