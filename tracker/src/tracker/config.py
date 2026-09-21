import os
from pathlib import Path

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR

# Configurações de Câmera / Stream
# Pode ser sobrescrito por variável de ambiente: RTSP_URL="rtsp://..." ou RTSP_URL="0" para webcam
RTSP_URL = os.getenv("RTSP_URL", "rtsp://admin:0708@192.168.1.6:5543/live/channel0")
CAMERA_SOURCE = 0 if RTSP_URL == "0" else RTSP_URL

# Configurações de Rede UDP (Destino Unreal Engine)
UDP_IP = os.getenv("UDP_IP", "127.0.0.1")
UDP_PORT = int(os.getenv("UDP_PORT", "8888"))
OSC_PORT = int(os.getenv("OSC_PORT", "8000"))
ENABLE_OSC = os.getenv("ENABLE_OSC", "true").lower() in ("true", "1", "yes")

# Modo Headless (ideal para Docker / servidores sem tela)
HEADLESS = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")

# Caminhos dos arquivos de configuração
CALIBRATION_FILE = Path(os.getenv("CALIBRATION_FILE", str(CONFIG_DIR / "calibration.json")))
TOKENS_CONFIG_FILE = Path(os.getenv("TOKENS_CONFIG_FILE", str(CONFIG_DIR / "tokens_config.json")))

# Configurações de Resolução Retificada do Tabuleiro (Warp Output)
WARP_WIDTH = int(os.getenv("WARP_WIDTH", "1920"))
WARP_HEIGHT = int(os.getenv("WARP_HEIGHT", "1080"))

# Configuração ArUco
# Dicionário padrão usado nas bases: DICT_4X4_50
ARUCO_DICT_NAME = os.getenv("ARUCO_DICT", "DICT_4X4_50")

# Anti-Jitter / Filtros
# Limiar mínimo de movimento normalizado (evita tremedeira em tokens parados)
MIN_POS_DELTA = float(os.getenv("MIN_POS_DELTA", "0.002"))  # ~0.2% da tela
MIN_ROT_DELTA = float(os.getenv("MIN_ROT_DELTA", "1.5"))    # 1.5 graus
SMOOTHING_FACTOR = float(os.getenv("SMOOTHING_FACTOR", "0.6")) # 0.0 (sem filtro) a 0.9 (muito suave)
