@echo off
chcp 65001 >nul 2>&1
title ExAI-App

echo ========================================
echo    ExAI-App
echo ========================================

pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo ========================================
echo http://127.0.0.1:8100
echo http://127.0.0.1:8100/docs
echo ========================================
echo.

python backend.py
