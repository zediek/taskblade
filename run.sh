#!/bin/bash
CONFIG_FILE="my-config.json"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "❌ Config file not found: $CONFIG_FILE"
  exit 1
fi

echo "Running TASKBLADE..."
python3 api_task_runer.py -c "$CONFIG_FILE"