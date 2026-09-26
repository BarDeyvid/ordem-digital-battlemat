"""Ponte entre as decisões dos agentes LLM e o Battlemat (Unreal Engine e Bridge Server)."""

import json
import logging
import socket
import urllib.request
from typing import Dict, Any, Tuple

from ai_agents.config import config

logger = logging.getLogger("ai_agents.battlemat_bridge")


class BattlematBridgeClient:
    """Despacha movimentos UDP e efeitos de rituais/status para a Unreal Engine."""

    def __init__(self):
        self.udp_ip = config.unreal_udp_ip
        self.udp_port = config.unreal_udp_port
        self.bridge_url = config.bridge_http_url.rstrip("/")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    @staticmethod
    def grid_to_norm_coords(grid_pos: str, cols: int = 8, rows: int = 8) -> Tuple[float, float]:
        """Converte coordenada de xadrez (ex: 'C4', 'A1') para X, Y normalizados (0.0 a 1.0)."""
        if not grid_pos or len(grid_pos) < 2:
            return 0.5, 0.5

        col_char = grid_pos[0].upper()
        row_char = grid_pos[1:]

        try:
            col_idx = ord(col_char) - ord("A")  # A=0, B=1, C=2...
            row_idx = int(row_char) - 1         # 1=0, 2=1, 3=2...
            norm_x = round((col_idx + 0.5) / cols, 4)
            norm_y = round((row_idx + 0.5) / rows, 4)
            return max(0.0, min(1.0, norm_x)), max(0.0, min(1.0, norm_y))
        except Exception:
            return 0.5, 0.5

    def move_token_in_unreal(self, token_id: int, token_type: str, x: float, y: float, rotation: float = 0.0):
        """Envia pacote UDP para a porta 8888 da Unreal movimentando o ator no tabuleiro."""
        payload = {
            "timestamp": 0.0,
            "tokens": [
                {
                    "id": token_id,
                    "type": token_type,
                    "x": round(x, 4),
                    "y": round(y, 4),
                    "rotation": round(rotation, 1),
                }
            ],
        }
        try:
            data = json.dumps(payload).encode("utf-8")
            self.sock.sendto(data, (self.udp_ip, self.udp_port))
            logger.info(f"[Unreal UDP] Token {token_id} movido para ({x:.2f}, {y:.2f})")
        except Exception as e:
            logger.error(f"[Unreal UDP Erro] Falha ao enviar pacote UDP: {e}")

    def cast_ritual_vfx(self, token_id: int, ritual: str, elemento: str, alcance: str = "Curto", custo_pe: int = 1):
        """Aciona o VFX de Membrana e alcance na Unreal via Bridge Server."""
        url = f"{self.bridge_url}/api/token/cast"
        payload = {
            "token_id": token_id,
            "ritual": ritual,
            "elemento": elemento,
            "alcance": alcance,
            "custo_pe": custo_pe,
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3) as res:
                logger.info(f"[Bridge Cast] Ritual '{ritual}' ({elemento}) despachado para Unreal.")
        except Exception as e:
            logger.debug(f"[Bridge Cast] Servidor Bridge offline ({url}): {e}")

    def update_character_status(
        self,
        token_id: int,
        nome: str,
        classe: str,
        pv_atual: int,
        pv_max: int,
        san_atual: int,
        san_max: int,
        pe_atual: int,
        pe_max: int,
    ):
        """Atualiza a barra de status / HUD na Unreal Engine via Bridge Server."""
        url = f"{self.bridge_url}/api/token/status"
        payload = {
            "token_id": token_id,
            "nome": nome,
            "classe": classe,
            "pv_atual": pv_atual,
            "pv_max": pv_max,
            "san_atual": san_atual,
            "san_max": san_max,
            "pe_atual": pe_atual,
            "pe_max": pe_max,
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3) as res:
                logger.info(f"[Bridge Status] Status do Token {token_id} sincronizado.")
        except Exception as e:
            logger.debug(f"[Bridge Status] Servidor Bridge offline ({url}): {e}")
