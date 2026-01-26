from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings


engine = create_engine(f"sqlite:///{settings.db_path}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _sqlite_has_column(conn, table: str, column: str) -> bool:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == column for r in rows)


def _sqlite_create_index_if_missing(conn, index_name: str, ddl: str) -> None:
    rows = conn.execute(text("SELECT name FROM sqlite_master WHERE type='index' AND name=:name"), {"name": index_name}).fetchall()
    if rows:
        return
    conn.execute(text(ddl))


def migrate_db() -> None:
    """
    SQLite 轻量迁移：用于 demo 环境下的增量字段/索引升级，避免用户已有 data/demo.db 时无法自动获得新字段。
    """
    with engine.begin() as conn:
        # devices：新增 last_report_at / last_message_type
        if _sqlite_has_column(conn, "devices", "deviceCode"):
            if not _sqlite_has_column(conn, "devices", "last_report_at"):
                conn.execute(text("ALTER TABLE devices ADD COLUMN last_report_at DATETIME"))
            if not _sqlite_has_column(conn, "devices", "last_message_type"):
                conn.execute(text("ALTER TABLE devices ADD COLUMN last_message_type INTEGER"))

        # 索引：使用 IF NOT EXISTS 兼容
        _sqlite_create_index_if_missing(conn, "ix_device_data_created_at", "CREATE INDEX ix_device_data_created_at ON device_data(created_at)")
        _sqlite_create_index_if_missing(
            conn,
            "ix_device_data_device_created_at",
            "CREATE INDEX ix_device_data_device_created_at ON device_data(deviceCode, created_at)",
        )
        _sqlite_create_index_if_missing(conn, "ix_device_data_message_type", "CREATE INDEX ix_device_data_message_type ON device_data(messageType)")
        _sqlite_create_index_if_missing(conn, "ix_alarm_deals_created_at", "CREATE INDEX ix_alarm_deals_created_at ON alarm_deals(created_at)")
        _sqlite_create_index_if_missing(conn, "ix_alarm_deals_device", "CREATE INDEX ix_alarm_deals_device ON alarm_deals(deviceCode)")
        _sqlite_create_index_if_missing(conn, "ix_audit_logs_created_at", "CREATE INDEX ix_audit_logs_created_at ON audit_logs(created_at)")
        _sqlite_create_index_if_missing(conn, "ix_file_exchange_received_at", "CREATE INDEX ix_file_exchange_received_at ON file_exchange(received_at)")
        _sqlite_create_index_if_missing(conn, "ix_middle_exchange_created_at", "CREATE INDEX ix_middle_exchange_created_at ON middle_exchange(created_at)")
        _sqlite_create_index_if_missing(conn, "ix_mq_records_published_at", "CREATE INDEX ix_mq_records_published_at ON message_queue_records(published_at)")
        _sqlite_create_index_if_missing(conn, "ix_devices_province", "CREATE INDEX ix_devices_province ON devices(provinceName)")
        _sqlite_create_index_if_missing(conn, "ix_devices_city", "CREATE INDEX ix_devices_city ON devices(cityName)")
        _sqlite_create_index_if_missing(conn, "ix_devices_farm", "CREATE INDEX ix_devices_farm ON devices(farmName)")
        _sqlite_create_index_if_missing(conn, "ix_devices_updated_at", "CREATE INDEX ix_devices_updated_at ON devices(updated_at)")


def init_db() -> None:
    from . import models

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    migrate_db()
