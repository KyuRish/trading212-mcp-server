@echo off
REM Trading 212 Gold Tracker Service
REM Runs HTTP server on port 8212 for HA integration
REM Make sure 'uv' is in your PATH

cd /d "%~dp0.."
uv run python scripts/analyzer_service.py --port 8212 --time 09:30
