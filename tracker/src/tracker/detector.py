import math
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np
import cv2 as cv

logger = logging.getLogger("tracker.detector")

# Dicionários ArUco suportados no OpenCV
ARUCO_DICTS = {
    "DICT_4X4_50": cv.aruco.DICT_4X4_50,
    "DICT_4X4_100": cv.aruco.DICT_4X4_100,
    "DICT_5X5_50": cv.aruco.DICT_5X5_50,
    "DICT_6X6_50": cv.aruco.DICT_6X6_50,
}

class TokenDetector:
    """Detecta marcadores ArUco, extrai pose normalizada (X, Y, Rotacao) e filtra jitter."""

    def __init__(
        self,
        dict_name: str = "DICT_4X4_50",
        tokens_config_path: Optional[Path] = None,
        min_pos_delta: float = 0.002,
        min_rot_delta: float = 1.5,
        smoothing: float = 0.6
    ):
        self.dict_id = ARUCO_DICTS.get(dict_name, cv.aruco.DICT_4X4_50)
        self.aruco_dict = cv.aruco.getPredefinedDictionary(self.dict_id)
        
        # Parâmetros otimizados para precisão de cantos e estabilidade
        self.params = cv.aruco.DetectorParameters()
        self.params.cornerRefinementMethod = cv.aruco.CORNER_REFINE_SUBPIX
        self.detector = cv.aruco.ArucoDetector(self.aruco_dict, self.params)

        self.min_pos_delta = min_pos_delta
        self.min_rot_delta = min_rot_delta
        self.smoothing = max(0.0, min(0.95, smoothing))

        # Histórico para filtro temporal {token_id: {"x": float, "y": float, "rotation": float}}
        self.history: Dict[int, Dict[str, float]] = {}

        # Mapeamento de tipos
        self.token_types = {}
        self.default_type = "token"
        if tokens_config_path and Path(tokens_config_path).exists():
            self.load_tokens_config(tokens_config_path)

    def load_tokens_config(self, path: Path):
        """Carrega mapeamento de IDs de tokens para seus tipos e nomes tematicos."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.token_types = data.get("mappings", {})
            self.default_type = data.get("default_type", "token")
            logger.info(f"Mapeamento de {len(self.token_types)} tokens carregado de {path}")
        except Exception as e:
            logger.error(f"Falha ao carregar tokens_config: {e}")

    def detect(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Detecta marcadores na imagem (ja retificada) e retorna lista estruturada de tokens."""
        h, w = image.shape[:2]
        gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        corners, ids, _ = self.detector.detectMarkers(gray)

        tokens = []
        if ids is None or len(ids) == 0:
            return tokens

        ids = ids.flatten()

        for marker_corners, marker_id in zip(corners, ids):
            pts = marker_corners.reshape((4, 2))
            
            # Centro do marcador (média dos 4 vértices)
            cx = float(np.mean(pts[:, 0]))
            cy = float(np.mean(pts[:, 1]))

            # Ponto médio da aresta superior (vértice 0 -> vértice 1) para direção da frente
            top_mid_x = float((pts[0, 0] + pts[1, 0]) / 2.0)
            top_mid_y = float((pts[0, 1] + pts[1, 1]) / 2.0)

            # Vetor direção apontando para a "frente" da miniatura
            dx = top_mid_x - cx
            dy = top_mid_y - cy

            # Ângulo em graus no sentido horário de 0 a 360 (0 graus = eixo X positivo)
            angle_rad = math.atan2(dy, dx)
            angle_deg = math.degrees(angle_rad)
            rotation = round((angle_deg + 360.0) % 360.0, 1)

            # Normalização X, Y no intervalo [0.0, 1.0]
            norm_x = round(cx / w, 4)
            norm_y = round(cy / h, 4)

            # Aplicação de filtro anti-jitter / Deadband
            filtered_x, filtered_y, filtered_rot = self._apply_filter(int(marker_id), norm_x, norm_y, rotation)

            # Identificação do tipo
            meta = self.token_types.get(str(marker_id), {})
            token_type = meta.get("type", self.default_type)
            token_name = meta.get("name", f"Token {marker_id}")

            tokens.append({
                "id": int(marker_id),
                "type": token_type,
                "name": token_name,
                "x": filtered_x,
                "y": filtered_y,
                "rotation": filtered_rot,
                # Coordenadas em pixels na tela retificada para rendering/debug
                "pixel_center": (int(cx), int(cy)),
                "pixel_corners": pts.astype(np.int32)
            })

        return tokens

    def _apply_filter(self, token_id: int, x: float, y: float, rot: float):
        """Suaviza pequenos ruídos de sensor da câmera quando a peça está parada."""
        if token_id not in self.history:
            self.history[token_id] = {"x": x, "y": y, "rotation": rot}
            return x, y, rot

        last = self.history[token_id]

        # Distância de deslocamento
        dist = math.hypot(x - last["x"], y - last["y"])
        # Diferença angular menor caminho
        rot_diff = abs((rot - last["rotation"] + 180) % 360 - 180)

        # Se a variação for menor que o deadband, mantemos a posição anterior (estática)
        if dist < self.min_pos_delta:
            new_x = last["x"]
            new_y = last["y"]
        else:
            new_x = round(last["x"] * self.smoothing + x * (1.0 - self.smoothing), 4)
            new_y = round(last["y"] * self.smoothing + y * (1.0 - self.smoothing), 4)

        if rot_diff < self.min_rot_delta:
            new_rot = last["rotation"]
        else:
            # Interpolação angular circular
            new_rot = round((last["rotation"] * self.smoothing + rot * (1.0 - self.smoothing)) % 360.0, 1)

        self.history[token_id] = {"x": new_x, "y": new_y, "rotation": new_rot}
        return new_x, new_y, new_rot

    def draw_tokens(self, image: np.ndarray, tokens: List[Dict[str, Any]]) -> np.ndarray:
        """Desenha caixas delimitadoras, seta de orientacao e informacoes do token."""
        debug_img = image.copy()

        # Cores por elemento / tipo
        color_palette = {
            "investigador": (255, 200, 0),        # Ciano/Amarelo
            "criatura_sangue": (0, 0, 255),       # Vermelho
            "criatura_morte": (50, 50, 50),       # Preto/Cinza
            "criatura_energia": (0, 165, 255),     # Laranja eletrico
            "criatura_conhecimento": (255, 255, 0),# Amarelo/Ouro
            "npc": (0, 255, 0),                   # Verde
            "token": (200, 200, 200)
        }

        for token in tokens:
            pts = token["pixel_corners"]
            cx, cy = token["pixel_center"]
            rot = token["rotation"]
            token_type = token["type"]
            color = color_palette.get(token_type, (0, 255, 0))

            # Contorno do marcador
            cv.polylines(debug_img, [pts], isClosed=True, color=color, thickness=3)

            # Ponto central
            cv.circle(debug_img, (cx, cy), 6, color, -1)

            # Seta apontando na direção da frente da miniatura
            arrow_len = 45
            rad = math.radians(rot)
            end_x = int(cx + arrow_len * math.cos(rad))
            end_y = int(cy + arrow_len * math.sin(rad))
            cv.arrowedLine(debug_img, (cx, cy), (end_x, end_y), (0, 255, 255), 3, tipLength=0.35)

            # Label de identificação
            label = f"ID:{token['id']} [{token['type']}] {rot:.0f}°"
            cv.rectangle(debug_img, (cx - 10, cy - 35), (cx + 200, cy - 10), (0, 0, 0), -1)
            cv.putText(debug_img, label, (cx - 5, cy - 18), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv.LINE_AA)

        return debug_img
