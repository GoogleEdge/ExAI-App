@echo off
chcp 65001 >nul 2>&1

echo ========================================
echo    ExAI-App Deployment (Windows)
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

if not exist "venv" (
    python -m venv venv
)

call venv\Scripts\activate.bat >nul 2>&1

pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple >nul 2>&1
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple >nul 2>&1

if not exist ".env" (
    echo ZHIPU_API_KEY=your_api_key_here > .env
)

echo Done.
echo.
echo Run: python backend.py
echo Docs: http://127.0.0.1:8100/docs
echo.

python backend.py
