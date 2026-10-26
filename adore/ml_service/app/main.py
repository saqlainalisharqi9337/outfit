"""FastAPI clothing + skin-tone analysis service (production-hardened).

Clothing accessories/footwear use local ImageNet MobileNetV2 weights.
Long dress vs pants vs long skirt uses models/dress_pants_skirt_mobilenetv2.keras
when present. Trousers vs shorts vs skirt uses
models/trousers_shorts_skirt_mobilenetv2.keras. Other garments use
clothing_mobilenetv2.keras, then ImageNet.
"""

from __future__ import annotations

import base64
import io
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image

from . import dress_upperwear_gate, footwear_classifier, garment_classifier
from . import object_detector, region_proposals
from . import maskrcnn_detector
from . import outfit20_detector
from .clothing_classifier import model_status
from .config import get_settings
from .object_detector import status as detector_status
from .gemini_clothing import apply_if_low
from .outfit_parser import parse_outfit
from .virtual_tryon import TryOnError, generate_try_on
from .skin_tone import analyze_skin_tone
from .teach import save_example
from .color_analysis import analyze_garment_colors, render_debug_collage

logger = logging.getLogger("adore.ml")

# 12 MB upload cap — enough for phone photos, blocks multi-GB abuse.
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
_ready = False
_warmup_error = ""
_OPEN_PATHS = {"/", "/health", "/health/live", "/health/ready", "/docs", "/openapi.json", "/redoc"}


def _warmup() -> None:
    """Load classifiers once at startup so the first user request is fast."""
    global _ready, _warmup_error
    try:
        # Touch status loaders (lazy) and a tiny blank image through the gate.
        model_status()
        detector_status()
        garment_classifier.status()
        footwear_classifier.status()
        dress_upperwear_gate.status()
        blank = Image.new("RGB", (224, 224), (200, 200, 200))
        parse_outfit(blank)
        _ready = True
        _warmup_error = ""
        logger.info("adore-ml warmup complete")
    except Exception as exc:  # noqa: BLE001
        _ready = False
        _warmup_error = str(exc)
        logger.exception("adore-ml warmup failed: %s", exc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _warmup()
    yield


app = FastAPI(
    title="Adore ML Service",
    version="1.2.0",
    lifespan=lifespan,
)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_api_key(request: Request, call_next):
    """When ADORE_API_KEY is set, require matching X-API-Key on non-health routes."""
    key = get_settings().api_key
    if key and request.url.path not in _OPEN_PATHS:
        provided = request.headers.get("x-api-key", "")
        if provided != key:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key."})
    return await call_next(request)


@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    if request.method == "POST":
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > MAX_UPLOAD_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Image too large (max {MAX_UPLOAD_BYTES // (1024*1024)}MB)."},
            )
    return await call_next(request)


def _read_image(data: bytes) -> Image.Image:
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large (max {MAX_UPLOAD_BYTES // (1024*1024)}MB).",
        )
    try:
        image = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Could not read image") from exc
    # Guard pathological resolutions that blow up memory.
    w, h = image.size
    if w * h > 40_000_000:
        raise HTTPException(status_code=400, detail="Image resolution too large")
    if max(w, h) > 4096:
        image.thumbnail((4096, 4096), Image.Resampling.LANCZOS)
    return image


@app.get("/health/live")
def health_live() -> dict[str, Any]:
    """Liveness probe — does not load models (safe for load balancers)."""
    return {"ok": True, "status": "alive", "service": "adore-ml", "version": app.version}


@app.get("/health/ready")
def health_ready() -> dict[str, Any]:
    """Readiness probe — true after warmup."""
    return {
        "ok": _ready,
        "status": "ready" if _ready else "warming",
        "error": _warmup_error,
        "service": "adore-ml",
        "version": app.version,
    }


@app.get("/health")
def health() -> dict[str, Any]:
    classifiers = model_status()
    detector = detector_status()
    return {
        "ok": True,
        "status": "ok" if _ready else "warming",
        "ready": _ready,
        "service": "adore-ml",
        "version": app.version,
        "model": classifiers,
        "classifiers": {
            "available": bool(classifiers),
            **({"detail": classifiers} if isinstance(classifiers, dict) else {}),
        },
        "detector": detector,
        "gate": dress_upperwear_gate.status(),
        "outfit20": outfit20_detector.status(),
        "maskrcnn": maskrcnn_detector.status(),
        "pipeline": (
            "Mask R-CNN M4.11 clothing detection, "
            "then Lab/K-Means colour + pattern on each garment box"
            if get_settings().maskrcnn_enabled
            else (
                "Fashionpedia/YOLOv8 20-class multi-item detection, "
                "MobileNetV2/ResNet specialists for garment type, "
                "then Lab/K-Means colour + pattern on each garment crop"
            )
        ),
    }


@app.post("/detect")
async def detect(file: UploadFile = File(...)) -> dict[str, Any]:
    """Detector-only view, for validating localisation without classification."""
    data = await file.read()
    image = _read_image(data)
    result = object_detector.analyze(image)
    strategy, regions = region_proposals.body_regions(
        person=result.person,
        keypoints=result.keypoints,
    )
    settings = get_settings()
    return {
        "detectorAvailable": result.available,
        "detector": detector_status(),
        "strategy": strategy,
        "person": (
            {"bbox": result.person, "confidence": round(result.person_confidence, 4)}
            if result.person
            else None
        ),
        "poseKeypoints": len(result.keypoints) if result.keypoints else 0,
        "detections": [
            {
                "label": p.detector_label,
                "cocoLabel": p.detector_label,
                "confidence": round(p.confidence, 4),
                "bbox": p.bbox,
                "source": p.source,
                "region": p.region,
                "allowedWardrobeLabels": sorted(p.allowed),
            }
            for p in result.objects
        ],
        "regions": [
            {"region": name, "bbox": list(box), "allowed": sorted(allowed)}
            for name, box, allowed in regions
        ],
        "thresholds": {
            "detectorConfidence": settings.detector_confidence,
            "detectorIou": settings.detector_iou,
            "classifierMinConfidence": settings.classifier_min_confidence,
            "refineMinConfidence": settings.refine_min_confidence,
        },
        "note": (
            "COCO detector: person and carried bags only. Garment labels come "
            "from the MobileNetV2 classifiers, not from this endpoint."
        ),
    }


@app.post("/analyze-clothing")
async def analyze_clothing(file: UploadFile = File(...)) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        data = await file.read()
        image = _read_image(data)
        result = parse_outfit(image)
        result = apply_if_low(image, dict(result))
        result["latencyMs"] = round((time.perf_counter() - started) * 1000)
        result["serviceVersion"] = app.version
        return result
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("analyze-clothing failed")
        raise HTTPException(
            status_code=500,
            detail="Clothing analysis failed. Please retry with another photo.",
        ) from exc


@app.post("/virtual-try-on")
async def virtual_try_on(
    person: UploadFile = File(...),
    clothing: UploadFile = File(...),
    garment_type: str = Form("entire_outfit"),
) -> dict[str, Any]:
    """Return a photo of the person wearing the clothing item (Magic Hour)."""
    allowed = {"entire_outfit", "upper_body", "lower_body", "dresses"}
    kind = garment_type.strip().lower() if garment_type else "entire_outfit"
    if kind not in allowed:
        kind = "entire_outfit"
    try:
        person_image = _read_image(await person.read())
        clothing_image = _read_image(await clothing.read())
        image_bytes, mime = generate_try_on(
            person_image,
            clothing_image,
            garment_type=kind,
        )
    except TryOnError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("virtual-try-on failed")
        raise HTTPException(
            status_code=500,
            detail="Virtual try-on failed. Please retry with another photo.",
        ) from exc
    return {
        "imageBase64": base64.b64encode(image_bytes).decode("ascii"),
        "mimeType": mime,
    }


@app.post("/teach-clothing")
async def teach_clothing(
    file: UploadFile = File(...),
    label: str = Form(...),
) -> dict[str, Any]:
    """Save a user-labeled photo for later fine-tuning. Does not retrain live."""
    data = await file.read()
    image = _read_image(data)
    try:
        result = save_example(image, label)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **result}


@app.post("/debug-colors")
async def debug_colors(
    file: UploadFile = File(...),
    x1: float | None = Form(None),
    y1: float | None = Form(None),
    x2: float | None = Form(None),
    y2: float | None = Form(None),
) -> dict[str, Any]:
    """Visual colour QA: crop, mask, clusters, and percentages for one garment."""
    data = await file.read()
    image = _read_image(data)
    box = None
    if None not in (x1, y1, x2, y2):
        box = [float(x1), float(y1), float(x2), float(y2)]
    analysis = analyze_garment_colors(image, bbox=box, debug=True)
    collage = render_debug_collage(image, analysis)
    buf = io.BytesIO()
    collage.save(buf, format="PNG")
    return {
        "ok": True,
        "item": "garment",
        **analysis.to_api(),
        "debug": analysis.debug,
        "collagePngBase64": base64.b64encode(buf.getvalue()).decode("ascii"),
    }


@app.post("/analyze-skin-tone")
async def analyze_skin(file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        data = await file.read()
        image = _read_image(data)
        tone, ita, used_fallback, message = analyze_skin_tone(image)
        return {
            "skinTone": tone,
            "ita": ita,
            "usedFallback": used_fallback,
            "message": message,
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("analyze-skin-tone failed")
        raise HTTPException(status_code=500, detail="Skin-tone analysis failed.") from exc


@app.get("/")
def root() -> dict[str, str]:
    return {"docs": "/docs", "health": "/health/live", "ready": "/health/ready"}
