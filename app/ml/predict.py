from app.ml.model_loader import load_model
from app.ml.preprocess import build_tabular_features, clean_text


def predict_email_text(text: str, features: dict | None = None) -> dict:
    model = load_model()
    if model is None:
        return {
            "label": "suspicious",
            "score": 0.5,
            "probabilities": {"safe": 0.5, "phishing": 0.5},
            "model_version": "no_model_fallback",
        }

    clean = clean_text(text)

    if isinstance(model, dict) and model.get("type") in {"hybrid_ensemble_v3", "hybrid_ensemble_v4"}:
        word_vectorizer = model["word_vectorizer"]
        word_model = model["word_model"]
        char_vectorizer = model["char_vectorizer"]
        char_model = model["char_model"]
        tab_model = model["tab_model"]
        weights = model.get("blend_weights", {"word": 0.45, "char": 0.35, "tabular": 0.20})

        word_proba = word_model.predict_proba(word_vectorizer.transform([clean]))[0]
        word_classes = list(word_model.classes_)
        word_phish = float(word_proba[word_classes.index("phishing")])

        char_proba = char_model.predict_proba(char_vectorizer.transform([clean]))[0]
        char_classes = list(char_model.classes_)
        char_phish = float(char_proba[char_classes.index("phishing")])

        if features is not None:
            tab_df = build_tabular_features([clean])
            for col in tab_df.columns:
                if col in features:
                    tab_df.loc[0, col] = features[col]
        else:
            tab_df = build_tabular_features([clean])
        tab_phish = float(tab_model.predict_proba(tab_df)[0][1])

        phish_score = (
            (word_phish * weights.get("word", 0.45))
            + (char_phish * weights.get("char", 0.35))
            + (tab_phish * weights.get("tabular", 0.20))
        )
        safe_score = 1.0 - phish_score
        thresholds = model.get("thresholds", {})
        phishing_threshold = thresholds.get("phishing", 0.80)
        suspicious_threshold = thresholds.get("suspicious", 0.55)
        if phish_score >= phishing_threshold:
            label = "phishing"
        elif phish_score >= suspicious_threshold:
            label = "suspicious"
        else:
            label = "safe"

        return {
            "label": label,
            "score": float(phish_score),
            "probabilities": {"safe": float(safe_score), "phishing": float(phish_score)},
            "component_scores": {
                "word_phishing_probability": word_phish,
                "char_phishing_probability": char_phish,
                "tabular_phishing_probability": tab_phish,
            },
            "model_version": str(model.get("type", "hybrid_ensemble_v4")),
            "trained_with_sklearn_version": model.get("metadata", {}).get("trained_with_sklearn_version"),
        }

    label = model.predict([clean])[0]
    score = 0.5
    probabilities = {}
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba([clean])[0]
        classes = list(model.classes_)
        probabilities = {cls: float(val) for cls, val in zip(classes, proba)}
        score = probabilities.get("phishing", max(probabilities.values()))
    return {
        "label": label,
        "score": float(score),
        "probabilities": probabilities,
        "model_version": "legacy_model",
    }
