@echo off
REM Daily Trading Analyzer - Run once
REM Make sure 'uv' is in your PATH, or update the path below

cd /d "%~dp0.."
uv run python scripts/daily_analyzer.py

pause
