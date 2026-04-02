import json
import os
from fastapi_mqtt import FastMQTT, MQTTConfig
from paho.mqtt import client as mqtt_client

class MqttManager:
    def __init__(self, fastapi_app, board_id, remote_broker, on_data_received):
        self.board_id = board_id
        self.on_data_received = on_data_received # Callback gửi data về Backend
        
        # --- 1. Cấu hình Local MQTT (FastMQTT) ---
        mqtt_host = os.getenv("BROKER", "local-mqtt-broker")
        self.local_client = FastMQTT(config=MQTTConfig(
            host=mqtt_host, port=1883, keepalive=60
        ))
        self.local_client.init_app(fastapi_app)
        
        # --- 2. Cấu hình Remote MQTT (Paho) ---
        self.remote_client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
        self.remote_broker = remote_broker
        self.setup_local_handlers()
        self.setup_remote_handlers()

    def setup_local_handlers(self):
        @self.local_client.on_connect()
        def connect(client, flags, rc, properties):
            print(f"🔗 Local Broker Connected (RC: {rc})")
            self.local_client.client.subscribe("sensor/data")

        @self.local_client.on_message()
        async def message(client, topic, payload, qos, properties):
            if topic == "sensor/data":
                try:
                    data = json.loads(payload.decode())
                    # Gửi sang Remote Broker
                    self.remote_client.publish(f"gateway/{self.board_id}/sensor/data", payload, qos=1)
                    # Gửi về class Backend để update UI/DB
                    await self.on_data_received(data)
                except Exception as e:
                    print(f"❌ Local Msg Error: {e}")

    def setup_remote_handlers(self):
        self.remote_client.on_connect = lambda c, u, f, rc, p: print(f"✅ Remote Connected to {self.remote_broker}")
        self.remote_client.connect_async(self.remote_broker, 1883)
        self.remote_client.loop_start()

    def publish_remote(self, topic, payload):
        self.remote_client.publish(topic, json.dumps(payload))
