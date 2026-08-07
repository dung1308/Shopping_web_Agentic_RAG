#!/usr/bin/env bash
set -e

echo "========================================================================"
echo " 🚀 GITHUB CODESPACES — AUTOMATED ENVIRONMENT & SERVICE BOOTSTRAP"
echo "========================================================================"

# 1. Initialize .env from .env.example if missing
if [ ! -f .env ]; then
    echo "📋 Creating .env from .env.example..."
    cp .env.example .env
fi

# 2. Upgrade pip and install package dependencies
echo "📦 Installing Python package and dev dependencies..."
pip install --upgrade pip
pip install -e ".[dev]"

# 3. Install Playwright browser dependencies
echo "🌐 Installing Playwright Chromium browser..."
playwright install chromium --with-deps || true

# 4. Install and start Ollama for Local LLM
echo "🤖 Installing Ollama Local LLM engine..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh || true
fi

# Start Ollama service in background if installed
if command -v ollama &> /dev/null; then
    echo "⚡ Starting Ollama service daemon..."
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 3

    echo "📥 Pulling local default LLM model (phi3.5)..."
    ollama pull phi3.5 || true
    
    if [ -d "models" ] && [ -f "models/Modelfile" ]; then
        echo "🔧 Building custom phi3.5-local GGUF model..."
        (cd models && ollama create phi3.5-local -f Modelfile || true)
    fi
fi

# 5. Pre-download BAAI/bge-m3 Embedding Model weights
echo "🧠 Pre-downloading BAAI/bge-m3 embedding model weights..."
python -c "
try:
    from sentence_transformers import SentenceTransformer
    print('Downloading BAAI/bge-m3 model...')
    SentenceTransformer('BAAI/bge-m3')
    print('✅ BAAI/bge-m3 embedding model downloaded successfully.')
except Exception as e:
    print(f'Embedding pre-download notice: {e}')
" || true

# 6. Run diagnostic connection probe
echo "🔎 Running initial diagnostic check..."
python scripts/check_all_connections.py || true

echo "========================================================================"
echo " 🎉 CODESPACES BOOTSTRAP COMPLETE! Ready to run backend API & UI:"
echo "    > uvicorn backend.main:app --port 8000 --reload"
echo "========================================================================"
