from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = base_dir / "data"
    db_path: Path = data_dir / "demo.db"
    key_dir: Path = data_dir / "keys"
    rsa_private_key_path: Path = key_dir / "rsa_private.pem"
    rsa_public_key_path: Path = key_dir / "rsa_public.pem"
    token_ttl_seconds: int = 7200
    timestamp_window_seconds: int = 300
    retention_days: int = 365
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_topic_prefix: str = "iot"
    coap_host: str = "0.0.0.0"
    coap_port: int = 5683
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"


settings = Settings()
