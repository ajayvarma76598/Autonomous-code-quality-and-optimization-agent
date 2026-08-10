@echo off
echo Starting Scalene Profiler with Uvicorn...
echo Press Ctrl+C to stop the server and generate the scalene report.
uv run scalene run --cpu-only --html --outfile scalene_report.html main.py
echo.
echo Scalene report has been generated and saved to scalene_report.html!
