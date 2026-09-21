import json
import socket
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tracker.simulate import TokenSimulator

def test_simulator_payload_structure():
    sim = TokenSimulator(ip="127.0.0.1", port=9999, fps=30)
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("127.0.0.1", 9999))
    receiver.settimeout(2.0)
    
    try:
        sim.send_telemetry()
        data, addr = receiver.recvfrom(4096)
        payload = json.loads(data.decode("utf-8"))
        
        assert "timestamp" in payload
        assert "tokens" in payload
        assert len(payload["tokens"]) >= 3
        
        for token in payload["tokens"]:
            assert "id" in token
            assert "type" in token
            assert "x" in token
            assert "y" in token
            assert "rotation" in token
            assert 0.0 <= token["x"] <= 1.0
            assert 0.0 <= token["y"] <= 1.0
            assert 0.0 <= token["rotation"] <= 360.0
            
        print("[OK] test_simulator_payload_structure validado com sucesso!")
    finally:
        receiver.close()
        sim.sender.close()

if __name__ == "__main__":
    test_simulator_payload_structure()
    print("\n[SUCESSO] Teste do simulador concluído com sucesso!")
