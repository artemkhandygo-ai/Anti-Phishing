from app.features.attachment_features import extract_attachment_features
from app.features.header_features import extract_header_features
from app.features.text_features import extract_text_features
from app.features.url_features import extract_url_features


def build_features(parsed_email: dict) -> dict:
    features = {}
    features.update(extract_text_features(parsed_email.get("subject"), parsed_email.get("text_body")))
    features.update(extract_url_features(parsed_email.get("links", [])))
    features.update(extract_header_features(parsed_email.get("raw_headers"), parsed_email.get("from_email"), parsed_email.get("reply_to_email")))
    features.update(extract_attachment_features(parsed_email.get("attachments", [])))
    return features
