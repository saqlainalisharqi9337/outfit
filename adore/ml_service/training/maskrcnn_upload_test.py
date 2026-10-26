"""Local upload page for a Mask R-CNN checkpoint. Not used by FastAPI or Flutter."""

from __future__ import annotations

import argparse
import io
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from training.label_map import load_label_map
from training.preview_maskrcnn import render_predictions
from training.train_maskrcnn import apply_cpu_fast, build_maskrcnn, load_checkpoint

PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Mask R-CNN upload test</title>
<style>
body { font-family: sans-serif; max-width: 920px; margin: 32px auto; }
img { max-width: 100%; }
</style>
</head>
<body>
<h1>Mask R-CNN upload test</h1>
<p>This page is local only. It is not part of the Adore app.</p>
<form method="post" enctype="multipart/form-data">
<input type="file" name="image" accept="image/*" required>
<button type="submit">Detect</button>
</form>
</body>
</html>
"""

MODEL = None
NAMES: list[str] = []
THRESH = 0.3


def load_model(checkpoint: Path, thresh: float) -> None:
    global MODEL, NAMES, THRESH
    THRESH = thresh
    meta = torch.load(checkpoint, map_location="cpu", weights_only=False)
    cfg = meta.get("config") or {}
    NAMES = list(meta.get("class_names") or load_label_map().detector_classes)
    model = build_maskrcnn(
        int(meta.get("num_classes") or 16),
        pretrained=False,
        min_size=int(cfg.get("min_size") or 320),
        max_size=int(cfg.get("max_size") or 480),
        smoke_rpn=True,
    )
    load_checkpoint(checkpoint, model, map_location="cpu")
    apply_cpu_fast(model)
    model.eval()
    MODEL = model
    print(f"Loaded {checkpoint} epoch={meta.get('epoch')} classes={len(NAMES)} thresh={thresh}")


def predict(raw: bytes) -> tuple[bytes, str]:
    rgb = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    array = np.array(rgb, dtype=np.float32).transpose(2, 0, 1) / 255.0
    image = torch.from_numpy(array)
    with torch.no_grad():
        pred = MODEL([image])[0]
    overlay = render_predictions(image, pred, NAMES, score_thresh=THRESH)
    scores = pred["scores"].detach().cpu()
    labels = pred["labels"].detach().cpu()
    lines = []
    for i in range(int(scores.shape[0])):
        if float(scores[i]) < THRESH:
            continue
        name = NAMES[int(labels[i]) - 1]
        lines.append(f"{name} {float(scores[i]):.2f}")
    buf = io.BytesIO()
    overlay.save(buf, format="JPEG", quality=90)
    summary = ", ".join(lines) if lines else "no detections at this threshold"
    return buf.getvalue(), summary


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length)
        marker = b'name="image"'
        start = payload.find(marker)
        if start < 0:
            self.send_error(400, "missing image")
            return
        data = payload[start:]
        data = data.split(b"\r\n\r\n", 1)[1]
        data = data.rsplit(b"\r\n--", 1)[0]
        try:
            jpeg, summary = predict(data)
        except Exception as exc:
            message = f"Could not read that image: {exc}".encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            self.wfile.write(message)
            return
        html = (
            PAGE.replace(
                "</form>",
                f"</form><p>{summary}</p><img alt=\"detection\" src=\"data:image/jpeg;base64,{_b64(jpeg)}\">",
            )
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def log_message(self, fmt: str, *args) -> None:
        print(fmt % args)


def _b64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description="Local Mask R-CNN image upload test")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=REPO_ROOT / "checkpoints" / "maskrcnn" / "m4_11" / "best_model.pth",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--score-threshold", type=float, default=0.3)
    args = parser.parse_args()
    if not args.checkpoint.is_file():
        print(f"Checkpoint not found: {args.checkpoint}")
        return 2
    load_model(args.checkpoint, args.score_threshold)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Open http://127.0.0.1:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
