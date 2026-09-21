"""Testes automatizados para validação do backend do tracker."""

import json
import socket
import numpy as np
import cv2 as cv

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tracker.detector import TokenDetector
from tracker.calibration import PerspectiveCalibrator
from tracker.network import UdpSender
from tracker import config

def test_detector_synthetic():
    """Gera uma imagem com um marcador ArUco sintético e valida detecção, X, Y e ângulo."""
    detector = TokenDetector(dict_name="DICT_4X4_50")
    
    # Cria imagem branca de 800x600
    img = np.ones((600, 800, 3), dtype=np.uint8) * 255
    
    # Gera marcador ID 4 (investigador) de 100x100
    marker = cv.aruco.generateImageMarker(detector.aruco_dict, 4, 100)
    marker_bgr = cv.cvtColor(marker, cv.COLOR_GRAY2BGR)
    
    # Cola o marcador no centro (x=350..450, y=250..350)
    img[250:350, 350:450] = marker_bgr
    
    tokens = detector.detect(img)
    assert len(tokens) == 1, f"Deveria detectar 1 token, detectou {len(tokens)}"
    
    tok = tokens[0]
    assert tok["id"] == 4, f"ID esperado 4, obteve {tok['id']}"
    assert 0.45 <= tok["x"] <= 0.55, f"Coordenada X normalizada esperada ~0.5, obteve {tok['x']}"
    assert 0.45 <= tok["y"] <= 0.55, f"Coordenada Y normalizada esperada ~0.5, obteve {tok['y']}"
    print("[OK] test_detector_synthetic passou!")

def test_calibrator_warp(tmp_path):
    """Testa transformação de perspectiva com 4 pontos."""
    calib_file = tmp_path / "test_calib.json"
    calibrator = PerspectiveCalibrator(calib_file, output_width=400, output_height=300)
    
    # 4 cantos de teste
    test_corners = [[50, 50], [750, 60], [740, 550], [60, 540]]
    calibrator.set_corners(test_corners)
    
    assert calibrator.is_calibrated()
    assert calib_file.exists()
    
    # Recarrega do arquivo
    new_calibrator = PerspectiveCalibrator(calib_file, output_width=400, output_height=300)
    assert new_calibrator.is_calibrated()
    
    dummy_frame = np.zeros((600, 800, 3), dtype=np.uint8)
    warped = new_calibrator.warp(dummy_frame)
    assert warped.shape == (300, 400, 3)
    print("[OK] test_calibrator_warp passou!")

def test_udp_payload():
    """Testa envio de pacote UDP e valida estrutura do JSON recebido."""
    test_port = 18888
    # Configura receptor de teste
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("127.0.0.1", test_port))
    receiver.settimeout(2.0)
    
    sender = UdpSender(ip="127.0.0.1", port=test_port)
    test_tokens = [{
        "id": 4,
        "type": "investigador",
        "x": 0.452,
        "y": 0.781,
        "rotation": 92.4
    }]
    
    success = sender.send_tokens(test_tokens, timestamp=1726859900.12)
    assert success
    
    data, addr = receiver.recvfrom(4096)
    payload = json.loads(data.decode("utf-8"))
    
    assert payload["timestamp"] == 1726859900.12
    assert len(payload["tokens"]) == 1
    assert payload["tokens"][0]["id"] == 4
    assert payload["tokens"][0]["type"] == "investigador"
    assert payload["tokens"][0]["x"] == 0.452
    assert payload["tokens"][0]["y"] == 0.781
    assert payload["tokens"][0]["rotation"] == 92.4
    
    receiver.close()
    sender.close()
    print("[OK] test_udp_payload passou com formato 100% compativel com o README!")

if __name__ == "__main__":
    from pathlib import Path
    import tempfile
    test_detector_synthetic()
    with tempfile.TemporaryDirectory() as td:
        test_calibrator_warp(Path(td))
    test_udp_payload()
    print("\n[SUCESSO] Todos os testes passaram perfeitamente!")
