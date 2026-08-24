@echo off
title My Desktop Agent
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo Application exited. Press any key to close this window.
    pause >nul
)
