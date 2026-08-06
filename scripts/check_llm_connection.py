"""
scripts/check_llm_connection.py — Diagnostic tool to test local Ollama LLM endpoint.
"""

import sys
import httpx
from backend.config import get_settings

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def check_connection():
    settings = get_settings()
    base_url = str(settings.llm_base_url).rstrip("/")
    model = settings.llm_model

    print(f"🔎 Testing connection to Ollama at: {base_url}")
    print(f"🤖 Configured Model: {model}")

    try:
        # Check /v1/models endpoint
        resp = httpx.get(f"{base_url}/models", timeout=5.0)
        if resp.status_code == 200:
            models_data = resp.json()
            raw_list = models_data.get("data") or []   # guard against null
            available_models = [m.get("id") for m in raw_list]
            print(f"✅ Ollama service is RUNNING!")

            if not available_models:
                print(f"⚠️  No models are loaded in Ollama yet.")
                print(f"   The GGUF file exists but hasn't been imported.")
                print(f"")
                print(f"   Run these commands to import your local GGUF:")
                print(f"   > cd e:\\VINSMART_Future_Thuc_Tap\\portfolio\\models")
                print(f"   > ollama create phi3.5-local -f Modelfile")
                print(f"")
                print(f"   Then re-run this script to verify.")
                return

            print(f"📋 Available models in Ollama: {available_models}")

            if any(model in m for m in available_models):
                print(f"🎉 Model '{model}' is connected and ready to use in your project!")
                # Quick inference test
                try:
                    test_resp = httpx.post(
                        f"{base_url}/chat/completions",
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": "Reply with just: OK"}],
                            "max_tokens": 10,
                        },
                        timeout=30.0,
                    )
                    if test_resp.status_code == 200:
                        reply = test_resp.json()["choices"][0]["message"]["content"]
                        print(f"🧪 Inference test passed! Model replied: {reply!r}")
                    else:
                        print(f"⚠️  Inference test failed: HTTP {test_resp.status_code}")
                except Exception as inf_exc:
                    print(f"⚠️  Inference test error: {inf_exc}")
            else:
                print(f"⚠️  Model '{model}' not found. Available: {available_models}")
                print(f"   Update LLM_MODEL in .env to one of the above, or run:")
                print(f"   > ollama create {model} -f models/Modelfile")
        else:
            print(f"❌ Ollama server returned status {resp.status_code}")

    except Exception as exc:
        print(f"❌ Could not connect to Ollama server at {base_url}: {exc}")
        print("💡 Make sure Ollama desktop app or 'ollama serve' is running.")

if __name__ == "__main__":
    check_connection()

