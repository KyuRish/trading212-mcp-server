@echo off
REM Trading 212 Gold Tracker Daemon
REM Runs continuously, analyzes daily at specified time
REM Make sure 'uv' is in your PATH

cd /d "%~dp0.."
uv run python scripts/daily_analyzer.py --daemon --time 09:30
