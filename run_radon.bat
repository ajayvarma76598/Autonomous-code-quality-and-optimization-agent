@echo off
echo Running Radon Code Complexity Analysis on backend...

echo ================================================== > radon_report.txt
echo CYCLOMATIC COMPLEXITY (CC) >> radon_report.txt
echo ================================================== >> radon_report.txt
uv run radon cc backend -a >> radon_report.txt
echo. >> radon_report.txt

echo ================================================== >> radon_report.txt
echo MAINTAINABILITY INDEX (MI) >> radon_report.txt
echo ================================================== >> radon_report.txt
uv run radon mi backend >> radon_report.txt
echo. >> radon_report.txt

echo ================================================== >> radon_report.txt
echo RAW METRICS >> radon_report.txt
echo ================================================== >> radon_report.txt
uv run radon raw backend >> radon_report.txt

echo.
echo Radon analysis complete. Report saved to radon_report.txt!
