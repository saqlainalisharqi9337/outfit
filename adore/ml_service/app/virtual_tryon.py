"""Virtual try-on with the Magic Hour Python client (AI Clothes Changer).

Uses the same Client pattern as Magic Hour docs:

    from magic_hour import Client
    client = Client(token=...)
    client.v1.ai_clothes_changer.generate(...)

The API key is read from ADORE_MAGIC_HOUR_API_KEY / MAGIC_HOUR_API_KEY
or ml_service/.env. It is never written into source.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

logger = logging.getLogger("adore.ml.tryon")

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class TryOnError(Exception):
    def __init__(self, message: str, status: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def api_key() -> str:
    """Same Client pattern as Magic Hour docs: Client(token=getenv(...))."""
    from os import getenv

    for name in ("ADORE_MAGIC_HOUR_API_KEY", "MAGIC_HOUR_API_KEY"):
        existing = (getenv(name) or "").strip()
        if existing:
            return existing
    if not _ENV_FILE.is_file():
        return ""
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        name, value = raw.split("=", 1)
        if name.strip() in {"ADORE_MAGIC_HOUR_API_KEY", "MAGIC_HOUR_API_KEY"}:
            return value.strip().strip('"').strip("'")
    return ""


def generate_try_on(
    person: Image.Image,
    clothing: Image.Image,
    garment_type: str = "entire_outfit",
) -> tuple[bytes, str]:
    from os import getenv

    from magic_hour import Client

    key = api_key() or (getenv("ADORE_MAGIC_HOUR_API_KEY") or "").strip()
    if not key:
        raise TryOnError(
            "Virtual try-on needs the Magic Hour API key on the clothing service.",
            status=503,
        )

    with tempfile.TemporaryDirectory(prefix="adore_tryon_") as tmp:
        person_path = Path(tmp) / "person.jpg"
        garment_path = Path(tmp) / "garment.jpg"
        _save_jpeg(person, person_path)
        _save_jpeg(clothing, garment_path)
        # Direct Magic Hour client — clothes changer, not ai_image_generator.
        client = Client(token=key)
        try:
            result = client.v1.ai_clothes_changer.generate(
                assets={
                    "person_file_path": str(person_path),
                    "garment_file_path": str(garment_path),
                    "garment_type": garment_type,
                },
                name="Adore virtual try-on",
                wait_for_completion=True,
                download_outputs=True,
                download_directory=tmp,
            )
        except Exception as exc:  # noqa: BLE001
            raise _map_sdk_error(exc) from exc

        status = getattr(result, "status", None) or ""
        if status != "complete":
            error = getattr(result, "error", None)
            message = None
            if error is not None:
                message = getattr(error, "message", None) or (
                    error.get("message") if isinstance(error, dict) else None
                )
            raise TryOnError(
                str(message)
                if message
                else "Magic Hour could not create the try-on image."
            )

        paths = list(getattr(result, "downloaded_paths", None) or [])
        if not paths:
            raise TryOnError("Magic Hour finished without a try-on photo.")
        data = Path(paths[0]).read_bytes()
        if not data:
            raise TryOnError("Magic Hour finished without a try-on photo.")
        mime = "image/png" if str(paths[0]).lower().endswith(".png") else "image/jpeg"
        return data, mime


def image_from_payload(payload: dict[str, Any]) -> tuple[bytes, str] | None:
    """Compatibility helper for older unit tests."""
    downloads = payload.get("downloads") or []
    if downloads and isinstance(downloads[0], dict):
        url = downloads[0].get("url")
        if isinstance(url, str) and url:
            return b"", "image/jpeg"
    return None


def _save_jpeg(image: Image.Image, path: Path) -> None:
    rgb = image.convert("RGB")
    rgb.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
    rgb.save(path, format="JPEG", quality=85)


def _map_sdk_error(exc: Exception) -> TryOnError:
    text = str(exc)
    lower = text.lower()
    if "401" in text or "unauthorized" in lower:
        return TryOnError("Magic Hour rejected the API key.", status=401)
    if "402" in text or "credit" in lower or "payment" in lower:
        return TryOnError(
            "Magic Hour needs more credits. Add credits, then try again.",
            status=402,
        )
    logger.warning("Magic Hour clothes changer failed: %s", exc)
    return TryOnError("Magic Hour could not create the try-on image. Try again.")
