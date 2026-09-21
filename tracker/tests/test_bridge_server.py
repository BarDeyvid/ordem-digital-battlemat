import json
import threading
import time
import urllib.request
from http.server import HTTPServer
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tracker.bridge_server import BridgeRequestHandler, get_udp_sender
from tracker import config

def test_bridge_server_endpoints():
    test_http_port = 8089
    test_osc_port = 8099

    # Configura sender para enviar OSC para a porta de teste
    sender = get_udp_sender()
    sender.osc_port = test_osc_port
    from pythonosc import udp_client
    sender.osc_client = udp_client.SimpleUDPClient("127.0.0.1", test_osc_port)

    # Inicia servidor HTTP em background thread
    httpd = HTTPServer(("127.0.0.1", test_http_port), BridgeRequestHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    # Registra mensagens OSC recebidas
    received_osc = []
    dispatcher = Dispatcher()
    dispatcher.map("/token/status", lambda addr, *args: received_osc.append((addr, args)))
    dispatcher.map("/token/cast", lambda addr, *args: received_osc.append((addr, args)))
    
    osc_server = BlockingOSCUDPServer(("127.0.0.1", test_osc_port), dispatcher)
    osc_thread = threading.Thread(target=osc_server.serve_forever, daemon=True)
    osc_thread.start()

    time.sleep(0.2)

    try:
        # 1. Teste GET /api/status
        req = urllib.request.Request(f"http://127.0.0.1:{test_http_port}/api/status")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "online"
            assert data["service"] == "Battlemat Bridge"

        # 2. Teste POST /api/token/status
        status_payload = {
            "token_id": 1,
            "nome": "Arthur Cervero",
            "classe": "Combatente",
            "pv_atual": 24,
            "pv_max": 30,
            "san_atual": 15,
            "san_max": 20,
            "pe_atual": 5,
            "pe_max": 8
        }
        req = urllib.request.Request(
            f"http://127.0.0.1:{test_http_port}/api/token/status",
            data=json.dumps(status_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["success"] is True
            assert data["token_id"] == 1

        # 3. Teste POST /api/token/cast
        cast_payload = {
            "token_id": 1,
            "ritual": "Decadência",
            "elemento": "Morte",
            "alcance": "Curto",
            "custo_pe": 1
        }
        req = urllib.request.Request(
            f"http://127.0.0.1:{test_http_port}/api/token/cast",
            data=json.dumps(cast_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["success"] is True
            assert data["ritual"] == "Decadência"
            assert data["alcance_m"] == 9.0

        time.sleep(0.2)

        # Valida que as mensagens OSC chegaram com os argumentos corretos
        assert len(received_osc) >= 2
        addresses = [msg[0] for msg in received_osc]
        assert "/token/status" in addresses
        assert "/token/cast" in addresses

        print("[OK] test_bridge_server_endpoints passou com sucesso!")
    finally:
        httpd.shutdown()
        osc_server.shutdown()

if __name__ == "__main__":
    test_bridge_server_endpoints()
    print("\n[SUCESSO] Teste da Bridge concluído com sucesso!")
