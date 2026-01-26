from typing import List, Optional, Any
from pydantic import BaseModel, Field


class CommonRequest(BaseModel):
    busId: str
    cipher: str
    sign: str
    timestamp: int


class TokenRequest(BaseModel):
    appkey: str


class TokenResponse(BaseModel):
    code: str
    msg: str
    token: Optional[str] = None


class CommonResponse(BaseModel):
    resultCode: str
    msg: str


class DeviceSyncPayload(BaseModel):
    deviceName: str
    deviceCode: str
    version: Optional[str] = None
    productKey: Optional[str] = None
    MAC: Optional[str] = None
    deviceTypeName: str
    productionDate: Optional[str] = None
    batchProduction: Optional[str] = None
    manufacturer: str
    gateway: Optional[str] = None
    extendInfo: Optional[str] = None
    linkType: int
    integrator: Optional[str] = None
    installDate: Optional[str] = None
    installPerson: Optional[str] = None
    provinceCode: str
    provinceName: str
    cityCode: str
    cityName: str
    farmName: str
    managementArea: str
    fieldsName: Optional[str] = None
    lng: str
    lat: str
    state: int
    connStatus: int
    manageStatus: int
    disabledType: Optional[int] = None
    reason: Optional[str] = None
    transmissionIntercal: int
    dept: str
    manager: Optional[str] = None
    user: Optional[str] = None
    scene1: str
    scene2: str
    scene3: str
    unifiedAddressCode: str


class DeviceDataContent(BaseModel):
    topic: str
    name: str
    dataType: Optional[int] = None
    dataSchema: Optional[str] = None
    updateValue: Optional[str] = None
    unit: Optional[str] = None
    alarmCode: Optional[str] = None
    alarmType: Optional[int] = None
    alarmLevel: Optional[int] = None


class DeviceDataPayload(BaseModel):
    deviceCode: str
    messageType: int
    reportTime: str
    content: List[DeviceDataContent]


class AlarmDealEnclosure(BaseModel):
    url: Optional[str] = None
    type: Optional[int] = None


class AlarmDealPayload(BaseModel):
    deviceCode: str
    alarmCode: str
    alarmName: str
    alarmStatus: int
    dealTime: str
    handler: str
    dept: str
    explanation: Optional[str] = None
    enclosures: Optional[List[AlarmDealEnclosure]] = None


class AddressSearchPayload(BaseModel):
    addr: str
    page: int = 1
    limit: int = 10
    equal: bool = False
    where: Any


class ExchangePublishPayload(BaseModel):
    topic: str
    payload: dict


class MiddleExchangePayload(BaseModel):
    table_name: str
    payload: dict


class ExportRequest(BaseModel):
    format: str = Field(default="json", pattern="^(json|xml|xls)$")

