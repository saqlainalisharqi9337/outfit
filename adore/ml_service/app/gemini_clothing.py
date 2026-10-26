"""Ask Gemini only when the local clothing model is unsure.

The API key is read from ADORE_GEMINI_API_KEY or ml_service/.env.
It is never written into source code.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image

from .clothing_taxonomy import CLASS_TO_CATEGORY
from .config import get_settings

logger = logging.getLogger("adore.ml.gemini")

_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-flash-latest:generateContent"
)
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
_ALLOWED = tuple(name for name in CLASS_TO_CATEGORY if name != "unknown")


def low_confidence(result: dict[str, Any]) -> bool:
    label = str(result.get("subcategory") or "").strip().lower()
    score = float(result.get("confidence") or 0)
    if result.get("usedFallback") or label in {"", "unknown"}:
        return True
    return score < get_settings().human_review_min_confidence


def api_key() -> str:
    existing = os.environ.get("ADORE_GEMINI_API_KEY", "").strip()
    if existing:
        return existing
    if not _ENV_FILE.is_file():
        return ""
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        name, value = raw.split("=", 1)
        if name.strip() == "ADORE_GEMINI_API_KEY":
            return value.strip().strip('"').strip("'")
    return ""


def apply_if_low(image: Image.Image, result: dict[str, Any]) -> dict[str, Any]:
    """Keep the local result when it is confident or Gemini is unavailable."""
    if not low_confidence(result):
        return result
    key = api_key()
    if not key:
        return result
    guess = _ask(image, key)
    if guess is None:
        return result
    return _merge(result, guess)


def _ask(image: Image.Image, key: str) -> dict[str, str] | None:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=85)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    labels = ", ".join(_ALLOWED)
    prompt = (
        "Identify the main clothing item in this photo. "
        "Reply with JSON only, no markdown. "
        f'Use exactly one subcategory from this list: {labels}. '
        '{"subcategory":"...","color":"a basic color word","confidence":0.0}'
    )
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": encoded,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
        },
    }
    request = urllib.request.Request(
        _ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-goog-api-key": key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Gemini clothing fallback failed: %s", exc)
        return None
    text = _response_text(payload)
    if not text:
        return None
    return _parse_label(text)


def _response_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    chunks = [str(part.get("text") or "") for part in parts if isinstance(part, dict)]
    return "\n".join(chunk for chunk in chunks if chunk).strip()


def _parse_label(text: str) -> dict[str, str] | None:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    label = str(data.get("subcategory") or "").strip().lower()
    if label == "tshirt":
        label = "t-shirt"
    if label not in CLASS_TO_CATEGORY or label == "unknown":
        return None
    try:
        score = float(data.get("confidence") or 0)
    except (TypeError, ValueError):
        score = 0.0
    if score < 0.4:
        return None
    color = str(data.get("color") or "").strip().lower()
    return {
        "subcategory": label,
        "category": CLASS_TO_CATEGORY[label],
        "confidence": f"{min(score, 0.99):.4f}",
        "color": color,
    }


def _merge(result: dict[str, Any], guess: dict[str, str]) -> dict[str, Any]:
    updated = dict(result)
    label = guess["subcategory"]
    score = float(guess["confidence"])
    updated["subcategory"] = label
    updated["category"] = guess["category"]
    updated["class"] = label
    updated["displayName"] = label
    updated["confidence"] = round(score, 4)
    updated["usedFallback"] = False
    updated["source"] = "gemini"
    updated["message"] = f"Detected {label} ({score * 100:.0f}%) with Gemini."
    if guess["color"] and not updated.get("color"):
        updated["color"] = guess["color"]
    item = {
        "category": guess["category"],
        "subcategory": label,
        "class": label,
        "confidence": round(score, 4),
        "color": updated.get("color"),
        "bbox": [0.0, 0.0, 1.0, 1.0],
        "source": "gemini",
        "region": "full",
        "usedFallback": False,
    }
    updated["detected"] = [item]
    updated["items"] = [item]
    return updated
