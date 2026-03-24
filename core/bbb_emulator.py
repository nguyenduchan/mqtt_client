import json
import time
import os
import random # Dùng để giả lập dữ liệu cảm biến
from paho.mqtt import client as mqtt_client

# --- CẤU HÌNH ---
BROKER = os.getenv('BROKER_IP', 'host.docker.internal') 
BOARD_ID = os.getenv('BOARD_ID', 'BBB-DEFAULT')
PORT = 1883
RECONNECT_DELAY = 5 

TOPIC_CMD = f"device/{BOARD_ID}/command"
TOPIC_RES = f"device/{BOARD_ID}/response"
TOPIC_SYNC = f"gateway/{BOARD_ID}/sync"
TOPIC_STATUS = f"gateway/{BOARD_ID}/status"
TOPIC_DATA = f"gateway/{BOARD_ID}/data" # Topic gửi dữ liệu cảm biến

APP_DIR = "/app/edge_logic"
if not os.path.exists(APP_DIR):
    os.makedirs(APP_DIR)

# --- HÀM GIẢ LẬP ĐỌC CẢM BIẾN (Thay bằng Modbus thực tế sau này) ---
def read_sensors():
    # Giả lập nhiệt độ từ 30-45, áp suất từ 6.0-8.5
    temp = round(random.uniform(30.0, 45.0), 1)
    press = round(random.uniform(6.0, 8.5), 2)
    return temp, press

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"✅ Đã kết nối tới {BROKER}!")
        client.subscribe(TOPIC_CMD, qos=1)
        client.subscribe(TOPIC_SYNC, qos=1)
        print(f"📡 Đã đăng ký nhận lệnh và đồng bộ.")
    else:
        print(f"❌ Kết nối thất bại, mã lỗi: {rc}")

def on_message(client, userdata, msg):
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

def run():
    client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"🔄 Đang kết nối tới Broker {BROKER}...")
    client.connect_async(BROKER, PORT)
    
    # Chạy vòng lặp nhận tin nhắn trong thread riêng
    client.loop_start()

    try:
        while True:
            # 1. Đọc dữ liệu từ cảm biến
            temp, press = read_sensors()
            
            # 2. Đóng gói JSON đúng format Dashboard yêu cầu
            payload = {
                "temp": temp,
                "press": press,
                "status": "Online",
                "timestamp": time.time()
            }
            
            # 3. Publish lên topic data
            client.publish(TOPIC_DATA, json.dumps(payload), qos=1)
            print(f"📤 [SENT] Temp: {temp}°C | Press: {press} Bar")
            
            # 4. Đợi 2 giây trước khi gửi lần tiếp theo
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("🛑 Dừng Gateway...")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    print("🚀 Script đang bắt đầu khởi động...")
    run()
