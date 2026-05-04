from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from app.core.config import settings
from app.ml.preprocess import build_tabular_features, clean_text, unify_dataset

MAX_PER_CLASS = 4000
WORD_MAX_FEATURES = 12000
CHAR_MAX_FEATURES = 8000


def load_training_data(dataset_paths: list[str]) -> pd.DataFrame:
    parts = []
    for path in dataset_paths:
        path_obj = Path(path)
        if not path_obj.exists() or path_obj.suffix.lower() != ".csv":
            continue
        if path_obj.name.lower() == "spam.csv":
            df = pd.read_csv(path_obj, encoding="latin1")
        else:
            df = pd.read_csv(path_obj)
        uni = unify_dataset(df)
        uni["source"] = path_obj.name
        parts.append(uni)
    if not parts:
        raise ValueError("No datasets found for training")
    full = pd.concat(parts, ignore_index=True)
    full["text"] = full["text"].astype(str).map(clean_text)
    full = full.drop_duplicates(subset=["text", "label"]).reset_index(drop=True)
    full = full[full["text"].str.len() > 3].reset_index(drop=True)

    balanced_parts = []
    for label, part in full.groupby("label", group_keys=False):
        if len(part) > MAX_PER_CLASS:
            balanced_parts.append(part.sample(MAX_PER_CLASS, random_state=42))
        else:
            balanced_parts.append(part)
    full = pd.concat(balanced_parts, ignore_index=True).sample(frac=1.0, random_state=42).reset_index(drop=True)
    return full


def _blend(word_proba, char_proba, tab_proba, weights=(0.45, 0.35, 0.20)):
    w1, w2, w3 = weights
    return (word_proba * w1) + (char_proba * w2) + (tab_proba * w3)


def train_model(dataset_paths: list[str]) -> dict:
    df = load_training_data(dataset_paths)
    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df["label"], test_size=0.2, random_state=42, stratify=df["label"]
    )

    word_vectorizer = TfidfVectorizer(
        max_features=WORD_MAX_FEATURES,
        ngram_range=(1, 2),
        min_df=2,
        sublinear_tf=True,
    )
    Xw_train = word_vectorizer.fit_transform(X_train)
    Xw_test = word_vectorizer.transform(X_test)
    word_model = SGDClassifier(
        loss="log_loss",
        max_iter=800,
        tol=1e-3,
        class_weight="balanced",
        random_state=42,
    )
    word_model.fit(Xw_train, y_train)
    word_phish = word_model.predict_proba(Xw_test)[:, list(word_model.classes_).index("phishing")]

    char_vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        max_features=CHAR_MAX_FEATURES,
        min_df=2,
        sublinear_tf=True,
    )
    Xc_train = char_vectorizer.fit_transform(X_train)
    Xc_test = char_vectorizer.transform(X_test)
    char_model = SGDClassifier(
        loss="log_loss",
        max_iter=800,
        tol=1e-3,
        class_weight="balanced",
        random_state=42,
    )
    char_model.fit(Xc_train, y_train)
    char_phish = char_model.predict_proba(Xc_test)[:, list(char_model.classes_).index("phishing")]

    Xt_train = build_tabular_features(X_train)
    Xt_test = build_tabular_features(X_test)
    y_train_bin = (y_train == "phishing").astype(int)
    y_test_bin = (y_test == "phishing").astype(int)
    tab_model = RandomForestClassifier(
        n_estimators=48,
        max_depth=10,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        n_jobs=1,
        random_state=42,
    )
    tab_model.fit(Xt_train, y_train_bin)
    tab_phish = tab_model.predict_proba(Xt_test)[:, 1]

    blended_phish = _blend(word_phish, char_phish, tab_phish)
    thresholds = {"phishing": 0.80, "suspicious": 0.55}
    y_pred = ["phishing" if p >= thresholds["suspicious"] else "safe" for p in blended_phish]

    model_path = Path(settings.MODEL_PATH)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "type": "hybrid_ensemble_v4",
        "word_vectorizer": word_vectorizer,
        "word_model": word_model,
        "char_vectorizer": char_vectorizer,
        "char_model": char_model,
        "tab_model": tab_model,
        "blend_weights": {"word": 0.45, "char": 0.35, "tabular": 0.20},
        "thresholds": thresholds,
        "metadata": {
            "samples": int(len(df)),
            "labels_distribution": df["label"].value_counts().to_dict(),
            "sources": df["source"].value_counts().to_dict(),
            "word_max_features": WORD_MAX_FEATURES,
            "char_max_features": CHAR_MAX_FEATURES,
            "max_per_class": MAX_PER_CLASS,
            "dataset_count": len(dataset_paths),
            "components": ["word_tfidf_sgd", "char_tfidf_sgd", "tabular_random_forest"],
            "trained_with_sklearn_version": sklearn.__version__,
            "training_completed_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    joblib.dump(bundle, model_path)

    return {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision_macro": float(precision_score(y_test, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_test, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_test, y_pred, average="macro", zero_division=0)),
        "roc_auc_phishing": float(roc_auc_score(y_test_bin, blended_phish)),
        "samples": int(len(df)),
        "labels_distribution": df["label"].value_counts().to_dict(),
        "sources": df["source"].value_counts().to_dict(),
        "model_path": str(model_path),
        "model_type": "hybrid_ensemble_v4",
        "components": ["word_tfidf_sgd", "char_tfidf_sgd", "tabular_random_forest"],
        "trained_with_sklearn_version": sklearn.__version__,
        "training_completed_at": bundle["metadata"]["training_completed_at"],
    }
