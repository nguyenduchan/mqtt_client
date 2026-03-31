import socket
import logging
from zeroconf import ServiceBrowser, Zeroconf, ServiceListener

logger = logging.getLogger("uvicorn.error")

class IoTDiscoveryService(ServiceListener):
    def __init__(self):
        self.zeroconf = Zeroconf()
        self.discovered_devices = {}  # Lưu trữ thiết bị phát hiện được
        self.browser = None

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
            ip = addresses[0] if addresses else "N/A"
            
            # Phân loại cơ bản
            dev_type = "Generic"
            if "wled" in name.lower(): dev_type = "WLED"
            elif "esphome" in name.lower(): dev_type = "ESPHome"

            self.discovered_devices[name] = {
                "name": name.split('.')[0],
                "ip": ip,
                "port": info.port,
                "type": dev_type
            }
            logger.info(f"✨ Found {dev_type}: {name} at {ip}")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        if name in self.discovered_devices:
            del self.discovered_devices[name]
            logger.info(f"❌ Device left: {name}")

    def start(self):
        services = ["_http._tcp.local.", "_esphomelib._tcp.local."]
        self.browser = ServiceBrowser(self.zeroconf, services, self)

    def stop(self):
        if self.browser:
            self.browser.cancel()
        self.zeroconf.close()

# Khởi tạo một instance duy nhất (Singleton)
discovery_service = IoTDiscoveryService()
