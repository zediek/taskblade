@echo off
set CONFIG_FILE=my-config.json

if not exist %CONFIG_FILE% (
    echo ❌ Config file not found: %CONFIG_FILE%
    pause
    exit /b
)

echo Running TASKBLADE...
python api_task_runer.py -c %CONFIG_FILE%
pause