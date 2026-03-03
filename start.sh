#!/bin/bash
# Quick start script for Memory Bridge

echo "========================================"
echo "  Memory Bridge Setup"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

# Check environment
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_KEY" ]; then
    echo "❌ Environment variables not set"
    echo ""
    echo "Please set:"
    echo "  export SUPABASE_URL=https://your-project.supabase.co"
    echo "  export SUPABASE_SERVICE_KEY=your-service-key"
    echo ""
    exit 1
fi

echo "✅ Environment variables set"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q flask flask-cors supabase sentence-transformers

# Download supporting files if not exist
if [ ! -f "embedding_service.py" ]; then
    echo "📥 Downloading embedding service..."
    curl -fsSL https://raw.githubusercontent.com/n00n0i/ollama-model-manager/main/supabase-local-embedding/embedding_service.py -o embedding_service.py
fi

# Start server
echo ""
echo "🚀 Starting Memory Bridge..."
echo ""
python3 memory_bridge.py
