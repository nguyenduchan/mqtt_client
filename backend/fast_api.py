import time
from fastapi import FastAPI
from mqtt_manager import MqttManager
from dashboard import Dashboard
from nicegui import ui
import json
import os

# --- CẤU HÌNH ---
BROKER = os.getenv('BROKER_IP', '192.168.1.18') 
BOARD_ID = os.getenv('BOARD_ID', 'BBB-DEFAULT')
PORT = 1883
RECONNECT_DELAY = 5 

TOPIC_CMD = f"device/{BOARD_ID}/command"
TOPIC_RES = f"device/{BOARD_ID}/response"
TOPIC_SYNC = f"gateway/{BOARD_ID}/sync"
TOPIC_STATUS = f"gateway/{BOARD_ID}/status"
TOPIC_DATA = f"gateway/{BOARD_ID}/sensor/data" # Topic gửi dữ liệu cảm biến

class IoTBackend:
    def __init__(self, app: FastAPI):
        self.app = app
        self.full_config = self.load_full_config()
        self.dashboard = Dashboard(self.full_config) 
        
        # State lưu trữ
        self.latest_iot_data = {
            "sensor/data": None,
            "status": "Offline",
            "last_seen": 0
        }

        # Khởi tạo MQTT (Truyền callback update_state vào)
        self.mqtt = MqttManager(
            fastapi_app=self.app,
            board_id=os.getenv('BOARD_ID', 'BBB-DEFAULT'),
            remote_broker=os.getenv('BROKER_IP', '192.168.1.18'),
            on_data_received=self.update_state
        )
        
        self.setup_routes()

    async def update_state(self, data):
        """Hàm nhận data từ MQTT và đẩy lên UI"""
        self.latest_iot_data["sensor/data"] = data
        self.latest_iot_data["status"] = "Online"
        self.latest_iot_data["last_seen"] = time.time()
        
        # CẬP NHẬT UI TỨC THÌ (Websocket nội bộ của NiceGUI)
        if self.dashboard:
            self.dashboard.update_ui_data(data)

    def setup_routes(self):
        @self.app.get("/get-data")
        async def get_data():
            if time.time() - self.latest_iot_data["last_seen"] > 30:
                self.latest_iot_data["status"] = "Offline"
            return self.latest_iot_data

    def load_full_config(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"factories": [], "has_subscription": False}


app = FastAPI()
backend = IoTBackend(app)

ui.run_with(
    app, 
    storage_secret='thiet_ke_by_me_2025' # Nhập một chuỗi ký tự bất kỳ vào đây
)