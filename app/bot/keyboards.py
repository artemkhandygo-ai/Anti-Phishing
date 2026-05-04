def feedback_keyboard(incident_id: int | None = None) -> dict:
    suffix = f":{incident_id}" if incident_id is not None else ""
    return {
        "inline_keyboard": [
            [
                {"text": "Это безопасно", "callback_data": f"feedback:safe{suffix}"},
                {"text": "Это фишинг", "callback_data": f"feedback:confirmed_phishing{suffix}"},
            ],
            [
                {"text": "Ложное срабатывание", "callback_data": f"feedback:false_positive{suffix}"},
            ],
        ]
    }
