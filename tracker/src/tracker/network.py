import socket
import json
import time
import logging
from typing import List, Dict, Any

try:
    from pythonosc import udp_client
    HAS_PYTHON_OSC = True
except ImportError:
    HAS_PYTHON_OSC = False

logger = logging.getLogger("tracker.network")

class UdpSender:
    """Envia telemetria de tokens tanto via JSON UDP bruto (porta 8888) quanto via OSC (porta 8000) para Unreal Engine."""

    def __init__(self, ip: str, port: int, osc_port: int = 8000, enable_osc: bool = True):
        self.ip = ip
        self.port = port
        self.osc_port = osc_port
        self.enable_osc = enable_osc and HAS_PYTHON_OSC

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self.osc_client = None
        if self.enable_osc:
            try:
                self.osc_client = udp_client.SimpleUDPClient(self.ip, self.osc_port)
                logger.info(f"OSC Client configurado para {self.ip}:{self.osc_port}")
            except Exception as e:
                logger.warning(f"Falha ao inicializar cliente OSC: {e}")

        self.sent_packets_count = 0
        self.last_send_time = time.time()
        logger.info(f"UdpSender configurado para JSON UDP {self.ip}:{self.port} (OSC={self.enable_osc} na porta {self.osc_port})")

    def send_tokens(self, tokens: List[Dict[str, Any]], timestamp: float = None) -> bool:
        """Formata e envia a lista de tokens detectados nos formatos esperados pela Unreal."""
        if timestamp is None:
            timestamp = time.time()

        payload = {
            "timestamp": round(timestamp, 3),
            "tokens": tokens
        }

        success = True

        # 1. Envio de JSON UDP bruto (porta 8888)
        try:
            data = json.dumps(payload).encode("utf-8")
            self.sock.sendto(data, (self.ip, self.port))
            self.sent_packets_count += 1
            self.last_send_time = timestamp
        except Exception as e:
            logger.error(f"Erro ao enviar pacote UDP para {self.ip}:{self.port}: {e}")
            success = False

        # 2. Envio OSC nativo para o plugin OSC da Unreal Engine (porta 8000)
        if self.osc_client:
            try:
                for t in tokens:
                    self.osc_client.send_message(
                        "/token/update",
                        [
                            int(t["id"]),
                            str(t.get("type", "token")),
                            float(t["x"]),
                            float(t["y"]),
                            float(t["rotation"])
                        ]
                    )
            except Exception as e:
                logger.debug(f"Erro ao enviar mensagem OSC: {e}")

        return success

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
