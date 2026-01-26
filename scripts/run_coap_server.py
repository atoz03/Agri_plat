import sys
from pathlib import Path

# 允许从项目根目录直接执行：python scripts/run_coap_server.py
sys.path.append(str(Path(__file__).resolve().parent.parent))

import asyncio
from app.services.coap_server import start_coap_server


if __name__ == "__main__":
    asyncio.run(start_coap_server())
