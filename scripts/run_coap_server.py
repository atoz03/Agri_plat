import asyncio
from app.services.coap_server import start_coap_server


if __name__ == "__main__":
    asyncio.run(start_coap_server())
