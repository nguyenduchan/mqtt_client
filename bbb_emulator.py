import json
import time
from paho.mqtt import client as mqtt_client

# --- Cấu hình kết nối tới Docker ---
# Vì Docker và WSL cùng chạy trên Windows, bạn có thể dùng địa chỉ IP của Windows
# hoặc thường là 172.x.x.x (IP của WSL host). 
# Cách đơn giản nhất: Dùng IP LAN của máy tính Windows của bạn (ví dụ 192.168.1.x)
BROKER = '192.168.1.20'  # <--- THAY BẰNG IP WINDOWS CỦA BẠN
PORT = 1883
TOPIC_CMD = "device/bbb-01/command"
TOPIC_RES = "device/bbb-01/response"

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        cmd = data.get("cmd")
        action = data.get("payload", {}).get("action")
        
        print(f"\n[WSL-BBB] Nhận lệnh: {cmd} | Hành động: {action}")
        
        response = {"cmd": cmd, "status": "success"}
        
        if cmd == "relay_control":
            if action == "ON":
                print(">>> GIẢ LẬP: ĐÃ BẬT RELAY (Đèn LED sáng) <<<")
                response["message"] = "Relay ảo đã BẬT"
            else:
                print(">>> GIẢ LẬP: ĐÃ TẮT RELAY (Đèn LED tắt) <<<")
                response["message"] = "Relay ảo đã TẮT"
        
        elif cmd == "system_info":
            response.update({
                "message": "Thông số từ WSL Ubuntu",
                "cpu": "10%", "ram": "256MB"
            })

        # Gửi phản hồi về cho Backend
        client.publish(TOPIC_RES, json.dumps(response))
        print(f"[WSL-BBB] Đã gửi phản hồi về Dashboard.")

    except Exception as e:
        print(f"Lỗi: {e}")

client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
client.on_message = on_message
client.connect(BROKER, PORT)
client.subscribe(TOPIC_CMD)

print("Đang chạy BeagleBone Giả lập trên WSL...")
client.loop_forever()
