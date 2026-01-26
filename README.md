# 农业物联网大田环境感知数据接入平台 Demo

本项目用于演示《农业物联网 大田环境感知数据接入要求》标准的接入、校验与交换能力。

## 功能覆盖

- HTTPS 接口接入（附录A全量接口）
- 严格安全链路（RSA+SM4-GCM+SHA256签名）
- MQTT/CoAP 接入示例
- 数据文件交换、数据中间库交换、消息队列交换
- 数据字典（附录B表格自动抽取）
- 审计日志与数据保留

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_data_dictionary.py
python scripts/seed_demo_data.py
uvicorn app.main:app --reload
```

默认账号：
- appkey: `DEMO_APP`
- appsecret: `DEMO_SECRET`

## 演示前端（零构建）

启动服务后访问：

- `http://127.0.0.1:8000/ui`
- `http://127.0.0.1:8000/ui/bigscreen`（绿色大屏，默认 10 秒刷新，适合投屏/大屏展示）

页面会通过 `POST /api/sp-token` 获取 token，然后调用：

- `GET /admin/api/summary`
- `GET /admin/api/devices`
- `GET /admin/api/device-data`
- `GET /admin/api/alarm-deals`
- `GET /admin/api/bigscreen/*`

## 标准合规说明（关键点）

- 标准 URL 兼容：除 `/api/...` 外，同时支持 `/uip-wgateway/iot/api/...`（不重复展示到 OpenAPI 文档）。
- token 校验：过期返回 `resultCode=402`（对应表 A.4）。
- 设备编码：`deviceCode` 按标准 20 位数字编码校验（8 位厂商编码 + 12 位设备自身ID）。
- 运行数据校验：`dataBatchSync` 的 `content` 按附录B参数表进行 topic/unit/dataType 校验，校验失败返回 `resultCode=422`。

### 获取 token

```bash
curl -X POST http://127.0.0.1:8000/api/sp-token \
  -H "Content-Type: application/json" \
  -d '{"appkey":"DEMO_APP"}'
```

### MQTT/CoAP

```bash
python scripts/run_mqtt_ingest.py
python scripts/run_coap_server.py
```

## 数据字典

```bash
curl http://127.0.0.1:8000/data/dictionary
```

## 交换能力

- 文件接收：`POST /exchange/file/receive`
- 文件拉取：`GET /exchange/file/{file_id}/download`
- 文件列表：`GET /exchange/file/list`
- 文件共享访问：`GET /exchange/files/<filename>`
- 中间库：`POST /exchange/middle/push`、`GET /exchange/middle/pull`
- 消息队列：`POST /exchange/mq/publish`
- 导入导出：`POST /exchange/import`、`POST /exchange/export`

## docker-compose（可选）

```bash
docker compose up -d
```
