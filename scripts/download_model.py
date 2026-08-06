"""
scripts/download_model.py — Python script to pull Ollama models or download GGUF models directly.

Usage:
    python scripts/download_model.py --model phi3.5
    python scripts/download_model.py --model qwen2.5:7b-instruct
    python scripts/download_model.py --direct-gguf
"""

import os
import sys
import json
import argparse
from pathlib import Path
import urllib.request

# Fix Windows console Unicode print errors (e.g. cp1252 encoding)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure OLLAMA_MODELS points to the portfolio folder
PORTFOLIO_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = PORTFOLIO_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
os.environ["OLLAMA_MODELS"] = str(MODELS_DIR)

OLLAMA_API_BASE = "http://localhost:11434"

# Direct GGUF download fallback links
HF_GGUF_URLS = {
    "phi3.5": "https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf",
    "llama3.2:3b": "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
    "qwen2.5:7b-instruct": "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf",
}


def pull_via_ollama_api(model_name: str) -> bool:
    """Pull model via Ollama HTTP REST API endpoint (http://localhost:11434/api/pull)."""
    import httpx

    url = f"{OLLAMA_API_BASE}/api/pull"
    payload = {"name": model_name, "stream": True}

    print(f"🚀 Sending pull request to Ollama API for model: '{model_name}'...")
    print(f"📁 Storage location: {MODELS_DIR}")

    try:
        with httpx.stream("POST", url, json=payload, timeout=None) as response:
            if response.status_code != 200:
                print(f"❌ Ollama API returned status code {response.status_code}")
                return False

            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    status = data.get("status", "")
                    completed = data.get("completed", 0)
                    total = data.get("total", 0)

                    if total > 0:
                        percent = (completed / total) * 100
                        mb_done = completed / (1024 * 1024)
                        mb_total = total / (1024 * 1024)
                        print(f"\r⏳ [{status}] {mb_done:.1f} MB / {mb_total:.1f} MB ({percent:.1f}%)", end="", flush=True)
                    else:
                        print(f"\r⏳ {status}", end="", flush=True)

        print("\n✅ Ollama model pull completed successfully!")
        return True

    except Exception as err:
        print(f"\n⚠️ Could not connect to local Ollama API server at {OLLAMA_API_BASE}: {err}")
        return False


def download_gguf_direct(model_alias: str):
    """Directly download GGUF file from Hugging Face into portfolio/models."""
    url = HF_GGUF_URLS.get(model_alias.lower())
    if not url:
        print(f"❌ No direct GGUF mapping for '{model_alias}'. Available aliases: {list(HF_GGUF_URLS.keys())}")
        return

    filename = url.split("/")[-1]
    target_path = MODELS_DIR / filename

    print(f"🌐 Downloading GGUF directly from Hugging Face: {filename}")
    print(f"📁 Destination: {target_path}")

    def progress_hook(count, block_size, total_size):
        downloaded = count * block_size
        if total_size > 0:
            percent = min(100.0, (downloaded / total_size) * 100)
            mb_done = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            sys.stdout.write(f"\r⏳ Downloaded: {mb_done:.1f} MB / {mb_total:.1f} MB ({percent:.1f}%)")
            sys.stdout.flush()

    try:
        urllib.request.urlretrieve(url, target_path, reporthook=progress_hook)
        print(f"\n✅ Direct download completed successfully! Saved to {target_path}")
    except Exception as exc:
        print(f"\n❌ Download failed: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Pull Ollama model or download GGUF to portfolio/models")
    parser.add_argument("--model", type=str, default="phi3.5", help="Model name (e.g., phi3.5, qwen2.5:7b-instruct, llama3.2:3b)")
    parser.add_argument("--direct-gguf", action="store_true", help="Download GGUF directly from Hugging Face")

    args = parser.parse_args()

    if args.direct_gguf:
        download_gguf_direct(args.model)
    else:
        success = pull_via_ollama_api(args.model)
        if not success:
            print("\n💡 Falling back to direct GGUF download from Hugging Face...")
            download_gguf_direct(args.model)


if __name__ == "__main__":
    main()
