"""Servidor de Ponte (Battlemat Bridge) entre a Ficha Web e o Unreal Engine.

Recebe atualizações de status de personagens (PV, SAN, PE), rituais e ações
vindas do app web (fichas-web) e despacha comandos OSC/UDP para o Unreal Engine.
"""

import argparse
import json
import logging
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

from tracker import config
from tracker.network import UdpSender

logger = logging.getLogger("tracker.bridge")

# Armazena estado em memória dos personagens vinculados a cada Token ID
CONNECTED_CHARACTERS: Dict[int, Dict[str, Any]] = {}

# Instância global do remetente OSC / UDP
_udp_sender: UdpSender = None


def get_udp_sender() -> UdpSender:
    global _udp_sender
    if _udp_sender is None:
        _udp_sender = UdpSender(
            ip=config.UDP_IP,
            port=config.UDP_PORT,
            osc_port=config.OSC_PORT,
            enable_osc=config.ENABLE_OSC
        )
    return _udp_sender


class BridgeRequestHandler(BaseHTTPRequestHandler):
    """Manipulador HTTP com suporte a CORS total para conexões locais de navegadores."""

    def _set_cors_headers(self, status_code=200, content_type="application/json"):
        self.send_response(status_code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Type", content_type)
        self.end_headers()

    def do_OPTIONS(self):
        self._set_cors_headers(200)

    def do_GET(self):
        if self.path == "/api/status" or self.path == "/":
            self._set_cors_headers(200)
            resp = {
                "status": "online",
                "service": "Battlemat Bridge",
                "osc_port": config.OSC_PORT,
                "udp_port": config.UDP_PORT,
                "connected_tokens": list(CONNECTED_CHARACTERS.keys()),
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))

        elif self.path == "/api/characters":
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(CONNECTED_CHARACTERS).encode("utf-8"))

        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "Rota nao encontrada"}).encode("utf-8"))

    def do_POST(self):
        sender = get_udp_sender()

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data.decode("utf-8"))
        except Exception as e:
            self._set_cors_headers(400)
            self.wfile.write(json.dumps({"error": f"JSON invalido: {e}"}).encode("utf-8"))
            return

        # -------------------------------------------------------------
        # Rota 1: Atualização de Status da Ficha (PV, SAN, PE)
        # -------------------------------------------------------------
        if self.path == "/api/token/status":
            token_id = int(payload.get("token_id", 0))
            nome = str(payload.get("nome", f"Token {token_id}"))
            classe = str(payload.get("classe", "Investigador"))

            pv_atual = int(payload.get("pv_atual", 1))
            pv_max = max(1, int(payload.get("pv_max", 1)))
            san_atual = int(payload.get("san_atual", 1))
            san_max = max(1, int(payload.get("san_max", 1)))
            pe_atual = int(payload.get("pe_atual", 0))
            pe_max = max(1, int(payload.get("pe_max", 1)))

            pv_pct = round(pv_atual / pv_max, 3)
            san_pct = round(san_atual / san_max, 3)
            pe_pct = round(pe_atual / pe_max, 3)

            CONNECTED_CHARACTERS[token_id] = {
                "token_id": token_id,
                "nome": nome,
                "classe": classe,
                "pv_atual": pv_atual,
                "pv_max": pv_max,
                "pv_pct": pv_pct,
                "san_atual": san_atual,
                "san_max": san_max,
                "san_pct": san_pct,
                "pe_atual": pe_atual,
                "pe_max": pe_max,
                "pe_pct": pe_pct,
            }

            # Envia via OSC para a Unreal Engine
            # Endereço: /token/status [id, nome, pv_pct, san_pct, pe_pct, pv_atual, pv_max, san_atual, san_max, pe_atual, pe_max]
            if sender.osc_client:
                try:
                    sender.osc_client.send_message(
                        "/token/status",
                        [
                            token_id,
                            nome,
                            float(pv_pct),
                            float(san_pct),
                            float(pe_pct),
                            pv_atual,
                            pv_max,
                            san_atual,
                            san_max,
                            pe_atual,
                            pe_max,
                        ]
                    )
                except Exception as ex:
                    logger.error(f"Erro ao enviar OSC /token/status: {ex}")

            logger.info(f"[Bridge Status] Token {token_id} ({nome}): PV {pv_atual}/{pv_max} ({pv_pct*100:.0f}%), SAN {san_atual}/{san_max}, PE {pe_atual}/{pe_max}")

            self._set_cors_headers(200)
            self.wfile.write(json.dumps({"success": True, "token_id": token_id}).encode("utf-8"))

        # -------------------------------------------------------------
        # Rota 2: Conjuração de Ritual no Tabuleiro
        # -------------------------------------------------------------
        elif self.path == "/api/token/cast":
            token_id = int(payload.get("token_id", 0))
            ritual_nome = str(payload.get("ritual", "Ritual Desconhecido"))
            elemento = str(payload.get("elemento", "Morte"))
            alcance = str(payload.get("alcance", "Curto"))
            custo_pe = int(payload.get("custo_pe", 1))

            # Converte alcance textual em metros para a Unreal calcular o raio em Unreal Units (1m = 100 UU)
            alcance_lower = alcance.lower()
            if "toque" in alcance_lower:
                alcance_m = 1.5
            elif "curto" in alcance_lower:
                alcance_m = 9.0
            elif "médio" in alcance_lower or "medio" in alcance_lower:
                alcance_m = 18.0
            elif "longo" in alcance_lower:
                alcance_m = 36.0
            elif "extremo" in alcance_lower:
                alcance_m = 90.0
            else:
                alcance_m = 9.0

            # Envia via OSC para a Unreal Engine
            # Endereço: /token/cast [id, ritual_nome, elemento, alcance, alcance_m, custo_pe]
            if sender.osc_client:
                try:
                    sender.osc_client.send_message(
                        "/token/cast",
                        [
                            token_id,
                            ritual_nome,
                            elemento,
                            alcance,
                            float(alcance_m),
                            custo_pe,
                        ]
                    )
                except Exception as ex:
                    logger.error(f"Erro ao enviar OSC /token/cast: {ex}")

            logger.info(f"[Bridge Cast] Token {token_id} conjurou '{ritual_nome}' [{elemento}] alcance={alcance_m}m")

            self._set_cors_headers(200)
            self.wfile.write(json.dumps({
                "success": True,
                "token_id": token_id,
                "ritual": ritual_nome,
                "alcance_m": alcance_m
            }).encode("utf-8"))

        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "Rota nao encontrada"}).encode("utf-8"))

    def log_message(self, format, *args):
        # Desativa logs verbosos automáticos do BaseHTTPRequestHandler para manter terminal limpo
        pass


def run_bridge_server(port: int = 8080, host: str = "0.0.0.0"):
    """Inicia o servidor HTTP da ponte em background ou foreground."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, BridgeRequestHandler)
    print("=" * 60)
    print("  BATTLEMAT BRIDGE SERVER (Fichas Web <-> Unreal Engine)")
    print("=" * 60)
    print(f"  [+] Escutando conexões web em: http://localhost:{port}")
    print(f"  [+] Acesso na rede local (Wi-Fi/Celular): http://<SEU_IP_LOCAL>:{port}")
    print(f"  [+] Despachando OSC para Unreal em: {config.UDP_IP}:{config.OSC_PORT}")
    print("=" * 60 + "\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Finalizado] Bridge Server encerrado.")
        httpd.server_close()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Battlemat Bridge Server para Fichas Web de Ordem Paranormal")
    parser.add_argument("--port", type=int, default=8080, help="Porta HTTP da ponte (padrao: 8080)")
    parser.add_argument("--host", default="0.0.0.0", help="Host de escuta (padrao: 0.0.0.0)")
    args = parser.parse_args()

    run_bridge_server(port=args.port, host=args.host)


if __name__ == "__main__":
    main()
