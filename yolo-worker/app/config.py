from pathlib import Path
import os
import torch

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = BASE_DIR / "models" / "modelo.pt"

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8002"))
HTTP_PORT = int(os.getenv("HTTP_PORT", "8003"))

REQUESTED_DEVICE = os.getenv("DEVICE", "cpu")

if REQUESTED_DEVICE != "cpu":
    if torch.cuda.is_available():
        DEVICE = REQUESTED_DEVICE
        print(f"GPU disponível. Utilizando: {DEVICE}")
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    else:
        DEVICE = "cpu"
        print("GPU não disponível. Utilizando CPU.")
else:
    DEVICE = "cpu"
    print("Utilizando CPU.")

IMAGE_SIZE = int(os.getenv("IMAGE_SIZE", "320"))
INFERENCE_HALF = os.getenv("INFERENCE_HALF", "true").lower() in {
    "1", "true", "yes", "on"
}
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.01"))