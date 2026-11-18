"""One-off check: can this PC run DistilBERT (SST-2), and how does it compare with VADER?"""
import os
import time
from pathlib import Path

# Keep the model cache inside the project (D: drive), not in C:\Users\...
CACHE_DIR = Path(__file__).resolve().parent / ".hf_cache"
os.environ.setdefault("HF_HOME", str(CACHE_DIR))
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

MODEL_ID = "distilbert-base-uncased-finetuned-sst-2-english"

SAMPLES = [
    "Excellent laptop, very fast and reliable.",
    "The battery drains very quickly.",
    "Delivery was delayed by four days.",
    "The product stopped working after two days.",
    "Good performance but expensive.",
    "Customer support was extremely helpful.",
    "Customer service did not resolve my issue.",
    "Average product, nothing special.",
    "The laptop works perfectly.",
    "The screen quality is disappointing.",
]

import torch
from transformers import pipeline

from nlp_backends import vader_sentiment

print("HF cache folder:", CACHE_DIR)
print("Device: CPU" if not torch.cuda.is_available() else "Device: CUDA available (still using CPU)")

start = time.time()
try:
    clf = pipeline("text-classification", model=MODEL_ID, device=-1)
except Exception as exc:
    print("\nCould not load the model:", type(exc).__name__)
    print(str(exc)[:300])
    raise SystemExit(1)
print(f"Model loaded in {time.time() - start:.1f} s\n")

print(f"{'DistilBERT':<18}{'VADER':<18}Review")
print("-" * 90)
start = time.time()
for text in SAMPLES:
    out = clf(text, truncation=True)[0]
    v = vader_sentiment(text)
    bert = f"{out['label'][:3]} {float(out['score']):.3f}"
    vader = f"{v['label'][:3]} {v['score']:+.3f}"
    print(f"{bert:<18}{vader:<18}{text}")
per_review = (time.time() - start) / len(SAMPLES)
print(f"\nAverage speed: {per_review * 1000:.0f} ms per review ({1 / per_review:.1f} reviews/second)")

size_mb = sum(f.stat().st_size for f in CACHE_DIR.rglob("*") if f.is_file()) / 1024 / 1024
print(f"Model cache size: {size_mb:.0f} MB")
