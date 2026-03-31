import json
import time
import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi_mqtt import FastMQTT, MQTTConfig
from paho.mqtt import client as mqtt_client
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models, database
from discovery_service import discovery_service  # Import object 'discovery_service' từ file 'discovery_service.py'
import ui_dashboard
from nicegui import ui

# --- CẤU HÌNH ---
BROKER = os.getenv('BROKER_IP', 'host.docker.internal') 
BOARD_ID = os.getenv('BOARD_ID', 'BBB-DEFAULT')
PORT = 1884
RECONNECT_DELAY = 5 

TOPIC_CMD = f"device/{BOARD_ID}/command"
TOPIC_RES = f"device/{BOARD_ID}/response"
TOPIC_SYNC = f"gateway/{BOARD_ID}/sync"
TOPIC_STATUS = f"gateway/{BOARD_ID}/status"
TOPIC_DATA = f"gateway/{BOARD_ID}/sensor/data" # Topic gửi dữ liệu cảm biến

# --- 1. Cấu hình MQTT ---
mqtt_config = MQTTConfig(
    host="local-mqtt-broker",  # Tên service trong docker-compose
    port=1883,
    keepalive=60,
    username=None,  # Thêm nếu broker yêu cầu
    password=None
)

app = FastAPI(title="Industrial IIoT Gateway")
local_client = FastMQTT(config=mqtt_config)
local_client.init_app(app)

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
@local_client.on_connect()
def connect(client, flags, rc, properties):
    # Dòng này cực kỳ quan trọng, nếu không hiện nghĩa là FastAPI chưa kết nối được Broker
    print(f"🔗 FastAPI đã kết nối Broker với mã lỗi: {rc}")
    local_client.client.subscribe("sensor/data")

@local_client.on_message()
async def message(client, topic, payload, qos, properties):
    global latest_iot_data
    try:
        payload_decode = payload.decode()
        # KIỂM TRA TOPIC TRƯỚC KHI XỬ LÝ
        if topic == "sensor/data":
            try:
                # Giải mã dữ liệu JSON từ Node-RED
                data = json.loads(payload_decode)
                latest_iot_data["sensor/data"] = data
                
                print(f"[SUCCESS] Nhận dữ liệu hợp lệ: {data}")

                remote_client.publish(TOPIC_DATA, payload_decode, qos=1)
                
                # TODO: Cập nhật vào Database (SQLite/Postgres) tại đây
                
            except json.JSONDecodeError:
                print("[ERROR] Dữ liệu nhận được không phải định dạng JSON")
        else:
            print(f"[IGNORE] Bỏ qua dữ liệu từ topic lạ: {topic}")
    except Exception as e:
        print(f"❌ Lỗi xử lý MQTT: {e}")

def on_connect_remote(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"✅ Đã kết nối tới {BROKER}!")
        client.subscribe(TOPIC_CMD, qos=1)
        client.subscribe(TOPIC_SYNC, qos=1)
        print(f"📡 Đã đăng ký nhận lệnh và đồng bộ.")
    else:
        print(f"❌ Kết nối thất bại, mã lỗi: {rc}")


def on_message_remote(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        if data.get('action') == "sync_file":
            with open(os.path.join(APP_DIR, data['filename']), "w") as f:
                f.write(data['content'])
            client.publish(TOPIC_STATUS, json.dumps({"board_id": BOARD_ID, "status": "synced_ok"}))
            print(f"✔️ Đã đồng bộ file: {data['filename']}")
        
        elif msg.topic == TOPIC_CMD:
            # Xử lý các lệnh điều khiển relay/system_info như cũ của bạn
            print(f"🎮 Nhận lệnh điều khiển: {data}")
            # ... (giữ nguyên logic relay_control của bạn ở đây)

    except Exception as e:
        print(f"❌ Lỗi on_message: {e}")


remote_client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
remote_client.reconnect_delay_set(min_delay=1, max_delay=60)
remote_client.on_connect = on_connect_remote
remote_client.on_message = on_message_remote

print(f"🔄 Đang kết nối tới Broker {BROKER}...")
remote_client.connect_async(BROKER, PORT)

# Chạy vòng lặp nhận tin nhắn trong thread riêng
remote_client.loop_start()

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

@app.on_event("startup")
def startup():
    # Chạy service quét thiết bị khi backend khởi động
    discovery_service.start()

@app.on_event("shutdown")
def shutdown():
    # Dừng service khi tắt server
    discovery_service.stop()



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
    local_client.publish("device/bbb-01/command", json.dumps(msg))

    # Chờ phản hồi (Cơ chế Async cực nhanh)
    import asyncio
    for _ in range(50):
        await asyncio.sleep(0.1)
        if command in last_responses:
            return last_responses.pop(command)

    return {"status": "timeout", "message": "No response from Board"}


@app.get("/status")
async def get_status():
    return {"mqtt_connected": local_client.client.is_connected()}


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
    local_client.publish(f"gateway/{board_id}/sync", json.dumps(payload), qos=1)
    return {"message": f"Sent {len(files)} files to {board_id}"}


# Xây dựng giao diện NiceGUI
ui_dashboard.build_ui()


# 3. KẾT NỐI: Đây là lệnh quan trọng nhất
# Nó sẽ gộp các route của NiceGUI vào FastAPI
ui.run_with(
    app, 
    storage_secret='thiet_ke_by_me_2024' # Nhập một chuỗi ký tự bất kỳ vào đây
)