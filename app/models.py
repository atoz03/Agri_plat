from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class AppCredential(Base):
    __tablename__ = "app_credentials"

    appkey: Mapped[str] = mapped_column(String(64), primary_key=True)
    appsecret: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TokenRecord(Base):
    __tablename__ = "tokens"

    token: Mapped[str] = mapped_column(String(512), primary_key=True)
    appkey: Mapped[str] = mapped_column(String(64), nullable=False)
    sm4_key_b64: Mapped[str] = mapped_column(String(256), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    bus_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    appkey: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        Index("ix_devices_province", "provinceName"),
        Index("ix_devices_city", "cityName"),
        Index("ix_devices_farm", "farmName"),
        Index("ix_devices_updated_at", "updated_at"),
    )

    deviceCode: Mapped[str] = mapped_column(String(32), primary_key=True)
    deviceName: Mapped[str] = mapped_column(String(128))
    version: Mapped[str] = mapped_column(String(32), nullable=True)
    productKey: Mapped[str] = mapped_column(String(64), nullable=True)
    MAC: Mapped[str] = mapped_column(String(64), nullable=True)
    deviceTypeName: Mapped[str] = mapped_column(String(64))
    productionDate: Mapped[str] = mapped_column(String(32), nullable=True)
    batchProduction: Mapped[str] = mapped_column(String(64), nullable=True)
    manufacturer: Mapped[str] = mapped_column(String(128))
    gateway: Mapped[str] = mapped_column(String(64), nullable=True)
    extendInfo: Mapped[str] = mapped_column(Text, nullable=True)
    linkType: Mapped[int] = mapped_column(Integer)
    integrator: Mapped[str] = mapped_column(String(128), nullable=True)
    installDate: Mapped[str] = mapped_column(String(32), nullable=True)
    installPerson: Mapped[str] = mapped_column(String(64), nullable=True)
    provinceCode: Mapped[str] = mapped_column(String(32))
    provinceName: Mapped[str] = mapped_column(String(64))
    cityCode: Mapped[str] = mapped_column(String(32))
    cityName: Mapped[str] = mapped_column(String(64))
    farmName: Mapped[str] = mapped_column(String(64))
    managementArea: Mapped[str] = mapped_column(String(64))
    fieldsName: Mapped[str] = mapped_column(String(64), nullable=True)
    lng: Mapped[str] = mapped_column(String(32))
    lat: Mapped[str] = mapped_column(String(32))
    state: Mapped[int] = mapped_column(Integer)
    connStatus: Mapped[int] = mapped_column(Integer)
    manageStatus: Mapped[int] = mapped_column(Integer)
    disabledType: Mapped[int] = mapped_column(Integer, nullable=True)
    reason: Mapped[str] = mapped_column(String(256), nullable=True)
    transmissionIntercal: Mapped[int] = mapped_column(Integer)
    dept: Mapped[str] = mapped_column(String(128))
    manager: Mapped[str] = mapped_column(String(64), nullable=True)
    user: Mapped[str] = mapped_column(String(64), nullable=True)
    scene1: Mapped[str] = mapped_column(String(16))
    scene2: Mapped[str] = mapped_column(String(16))
    scene3: Mapped[str] = mapped_column(String(16))
    unifiedAddressCode: Mapped[str] = mapped_column(String(64))
    last_report_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_message_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DeviceData(Base):
    __tablename__ = "device_data"
    __table_args__ = (
        Index("ix_device_data_created_at", "created_at"),
        Index("ix_device_data_device_created_at", "deviceCode", "created_at"),
        Index("ix_device_data_message_type", "messageType"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deviceCode: Mapped[str] = mapped_column(String(32))
    messageType: Mapped[int] = mapped_column(Integer)
    reportTime: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlarmDeal(Base):
    __tablename__ = "alarm_deals"
    __table_args__ = (
        Index("ix_alarm_deals_created_at", "created_at"),
        Index("ix_alarm_deals_device", "deviceCode"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deviceCode: Mapped[str] = mapped_column(String(32))
    alarmCode: Mapped[str] = mapped_column(String(64))
    alarmName: Mapped[str] = mapped_column(String(128))
    alarmStatus: Mapped[int] = mapped_column(Integer)
    dealTime: Mapped[str] = mapped_column(String(32))
    handler: Mapped[str] = mapped_column(String(64))
    dept: Mapped[str] = mapped_column(String(64))
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    enclosures: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str] = mapped_column(Text)
    ip: Mapped[str] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FileExchangeRecord(Base):
    __tablename__ = "file_exchange"
    __table_args__ = (Index("ix_file_exchange_received_at", "received_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(256))
    checksum: Mapped[str] = mapped_column(String(128))
    size: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(64))
    path: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MiddleExchangeRecord(Base):
    __tablename__ = "middle_exchange"
    __table_args__ = (Index("ix_middle_exchange_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_name: Mapped[str] = mapped_column(String(128))
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MessageQueueRecord(Base):
    __tablename__ = "message_queue_records"
    __table_args__ = (Index("ix_mq_records_published_at", "published_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(128))
    payload: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
