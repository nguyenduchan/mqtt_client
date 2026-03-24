import json
import time
from fastapi import FastAPI, Depends, HTTPException
from fastapi_mqtt import FastMQTT, MQTTConfig
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models, database

# --- 1. Cấu hình MQTT ---
mqtt_config = MQTTConfig(
    host="local-mqtt-broker",  # Tên service trong docker-compose
    port=1883,
    keepalive=60,
    username=None,  # Thêm nếu broker yêu cầu
    password=None
)

app = FastAPI(title="Industrial IIoT Gateway")
mqtt = FastMQTT(config=mqtt_config)
mqtt.init_app(app)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# BIẾN LƯU TRỮ TRONG RAM (Lớp đệm tốc độ cao)
# Dashboard sẽ GET dữ liệu từ đây
latest_iot_data = {
    "temp": 0.0,
    "press": 0.0,
    "status": "Offline",
    "last_seen": 0
}

# Tự động tạo bảng khi khởi động (Dành cho bản Dev)
models.Base.metadata.create_all(bind=database.engine)

# Lưu trữ phản hồi từ BeagleBone
last_responses = {}


# --- 2. Xử lý sự kiện MQTT (Decorator) ---
@mqtt.on_connect()
def connect(client, flags, rc, properties):
    # Dòng này cực kỳ quan trọng, nếu không hiện nghĩa là FastAPI chưa kết nối được Broker
    print(f"🔗 FastAPI đã kết nối Broker với mã lỗi: {rc}")
    mqtt.client.subscribe("sensor/data")

@mqtt.on_message()
async def message(client, topic, payload, qos, properties):
    global latest_iot_data
    try:
        # KIỂM TRA TOPIC TRƯỚC KHI XỬ LÝ
        if topic == "sensor/data":
            try:
                # Giải mã dữ liệu JSON từ Node-RED
                data = json.loads(payload.decode())
                latest_iot_data["sensor/data"] = data
                
                print(f"[SUCCESS] Nhận dữ liệu hợp lệ: {data}")
                
                # TODO: Cập nhật vào Database (SQLite/Postgres) tại đây
                
            except json.JSONDecodeError:
                print("[ERROR] Dữ liệu nhận được không phải định dạng JSON")
        else:
            print(f"[IGNORE] Bỏ qua dữ liệu từ topic lạ: {topic}")
    except Exception as e:
        print(f"❌ Lỗi xử lý MQTT: {e}")


# Giả lập dữ liệu từ Database
CONFIG_DATA = {
    "has_subscription": False,
    "expiry_date": "2026-12-31",
    "factories": [
        {
            "f_id": "F01", "f_name": "Nhà máy Bắc Ninh",
            "gateways": [{
                "gw_id": "BBB-001",
                "devices": [
                    {"type": "sensor", "id": "temp_01", "label": "Nhiệt độ Lò 1", "unit": "°C", "icon": "THERMOSTAT"},
                    {"type": "sensor", "id": "press_01", "label": "Áp suất Khí", "unit": "Bar", "icon": "SPEED"},
                    {"type": "control", "id": "pump_01", "label": "Bơm Làm Mát", "sub_type": "toggle"},
                    {"type": "camera", "id": "cam_01", "label": "Camera Cổng Chính", "url": "https://unsplash.com"}
                ]
            }]
        },
        {
            "f_id": "F02", "f_name": "Xưởng Bình Dương",
            "gateways": [{
                "gw_id": "BBB-002",
                "devices": [
                    {"type": "sensor", "id": "energy_01", "label": "Điện năng", "unit": "kWh", "icon": "BOLT"},
                    {"type": "control", "id": "fan_01", "label": "Quạt Thông Gió", "sub_type": "toggle"}
                ]
            }]
        }
    ]
}

@app.get("/api/config")
async def get_config():
    return CONFIG_DATA

# API ĐỂ DASHBOARD GỌI (Mỗi 2 giây)
@app.get("/get-data")
async def get_data():
    # Kiểm tra nếu quá 30s không có dữ liệu mới thì báo Offline
    if time.time() - latest_iot_data["last_seen"] > 30:
        latest_iot_data["status"] = "Offline"

    return latest_iot_data


# --- 3. API Endpoints ---

@app.post("/control/{command}")
async def send_command(command: str, params: dict):
    msg = {
        "cmd": command,
        "payload": params
    }

    # Gửi lệnh xuống BeagleBone
    mqtt.publish("device/bbb-01/command", json.dumps(msg))

    # Chờ phản hồi (Cơ chế Async cực nhanh)
    import asyncio
    for _ in range(50):
        await asyncio.sleep(0.1)
        if command in last_responses:
            return last_responses.pop(command)

    return {"status": "timeout", "message": "No response from Board"}


@app.get("/status")
async def get_status():
    return {"mqtt_connected": mqtt.client.is_connected()}


# 1. API: Đồng bộ từng file từ PC lên DB
@app.post("/dev/sync-to-db")
async def sync_file(data: dict, db: Session = Depends(database.get_db)):
    config = db.query(models.GatewayConfig).filter(
        models.GatewayConfig.board_id == data['board_id'],
        models.GatewayConfig.filename == data['filename']
    ).first()

    if config:
        config.content = data['content']
        config.version += 1
    else:
        config = models.GatewayConfig(
            board_id=data['board_id'],
            filename=data['filename'],
            content=data['content']
        )
        db.add(config)
    db.commit()
    return {"status": "success", "file": data['filename']}

# 2. API: Lấy toàn bộ source code của 1 khách hàng từ DB
@app.get("/dev/get-source/{board_id}")
async def get_source(board_id: str, db: Session = Depends(database.get_db)):
    files = db.query(models.GatewayConfig).filter(models.GatewayConfig.board_id == board_id).all()
    return [{"filename": f.filename, "content": f.content} for f in files]

# 3. API: Đẩy lệnh đồng bộ xuống Gateway (MQTT)
@app.post("/dev/push-to-gateway/{board_id}")
async def push_to_gateway(board_id: str, db: Session = Depends(database.get_db)):
    # 1. Kiểm tra quyền từ bảng Customers
    customer = db.query(models.Customer).filter(models.Customer.board_id == board_id).first()

    if not customer.allow_remote_debug:
        raise HTTPException(status_code=403, detail="Khách hàng hiện đang khóa chế độ cập nhật từ xa!")

    files = db.query(models.GatewayConfig).filter(models.GatewayConfig.board_id == board_id).all()
    payload = {
        "action": "rsync",
        "files": [{"n": f.filename, "c": f.content} for f in files]
    }
    # Giả sử 'mqtt' là instance FastMQTT đã init
    mqtt.publish(f"gateway/{board_id}/sync", json.dumps(payload), qos=1)
    return {"message": f"Sent {len(files)} files to {board_id}"}