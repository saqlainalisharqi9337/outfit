cd "c:\fyp saqlain\adore\ml_service"
$env:PYTHONUNBUFFERED = "1"
.\.venv_m48\Scripts\python.exe -u training\train_maskrcnn.py --max-train-images 2000 --max-val-images 250 --epochs 3 --batch-size 1 --num-workers 0 --class-aware-subset --score-threshold 0.5 --checkpoint-dir ..\checkpoints\maskrcnn\m4_8 --init-from ..\checkpoints\maskrcnn\m4_6\best_model.pth --min-size 320 --max-size 480 --print-every 50 --device cpu
