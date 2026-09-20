import socket
import json
import time
import logging
from typing import List, Dict, Any

logger = logging.getLogger("tracker.network")

class UdpSender:
    """Envia pacotes JSON de telemetria de tokens via UDP para a Unreal Engine."""

    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Permite broadcast caso queira usar ip de broadcast local (ex: 255.255.255.255)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sent_packets_count = 0
        self.last_send_time = time.time()
        logger.info(f"UdpSender configurado para {self.ip}:{self.port}")

    def send_tokens(self, tokens: List[Dict[str, Any]], timestamp: float = None) -> bool:
        """Formata e envia a lista de tokens detectados no formato esperado pela Unreal."""
        if timestamp is None:
            timestamp = time.time()

        payload = {
            "timestamp": round(timestamp, 3),
            "tokens": tokens
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            self.sock.sendto(data, (self.ip, self.port))
            self.sent_packets_count += 1
            self.last_send_time = timestamp
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar pacote UDP para {self.ip}:{self.port}: {e}")
            return False

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
