import sys
from pathlib import Path

# 允许从项目根目录直接执行：python scripts/run_mqtt_ingest.py
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.services.mqtt_ingest import run_mqtt_ingest


if __name__ == "__main__":
    run_mqtt_ingest()
