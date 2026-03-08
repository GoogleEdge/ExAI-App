#!/bin/bash

echo "========================================"
echo "   ExAI-App Deployment (macOS)"
echo "========================================"
echo

if ! command -v python3 &> /dev/null; then
    echo "[Error] Python not found"
    exit 1
fi

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple > /dev/null 2>&1
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple > /dev/null 2>&1

if [ ! -f ".env" ]; then
    echo "ZHIPU_API_KEY=your_api_key_here" > .env
fi

echo "Done."
echo "Run: source venv/bin/activate && python backend.py"
echo "Docs: http://127.0.0.1:8100/docs"
echo

python backend.py
