import json
import logging
from pathlib import Path
import numpy as np
import cv2 as cv

logger = logging.getLogger("tracker.calibration")

class PerspectiveCalibrator:
    """Gerencia a calibração de perspectiva dos 4 cantos do monitor/tabuleiro."""

    CORNER_NAMES = ["Top-Left (Canto Superior Esquerdo)", 
                    "Top-Right (Canto Superior Direito)", 
                    "Bottom-Right (Canto Inferior Direito)", 
                    "Bottom-Left (Canto Inferior Esquerdo)"]

    def __init__(self, calibration_path: Path, output_width: int = 1920, output_height: int = 1080):
        self.calibration_path = Path(calibration_path)
        self.output_width = output_width
        self.output_height = output_height
        self.corners = []  # Lista de [ [x, y], ... ] 4 pontos
        self.transform_matrix = None
        self.dst_points = np.array([
            [0, 0],
            [self.output_width - 1, 0],
            [self.output_width - 1, self.output_height - 1],
            [0, self.output_height - 1]
        ], dtype=np.float32)

        self.load()

    def load(self) -> bool:
        """Carrega os 4 cantos do arquivo calibration.json se existir."""
        if not self.calibration_path.exists():
            logger.info(f"Nenhum arquivo de calibracao encontrado em: {self.calibration_path}")
            return False

        try:
            with open(self.calibration_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            corners = data.get("corners", [])
            if len(corners) == 4:
                self.corners = corners
                self._update_matrix()
                logger.info(f"Calibracao carregada com sucesso de {self.calibration_path}")
                return True
            else:
                logger.warning("Arquivo de calibracao contem quantidade invalida de cantos.")
                return False
        except Exception as e:
            logger.error(f"Erro ao ler calibracao: {e}")
            return False

    def save(self):
        """Salva os cantos atuais no calibration.json."""
        try:
            self.calibration_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "output_width": self.output_width,
                "output_height": self.output_height,
                "corners": self.corners
            }
            with open(self.calibration_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Calibracao salva em {self.calibration_path}")
        except Exception as e:
            logger.error(f"Erro ao salvar calibracao: {e}")

    def set_corners(self, corners):
        """Define os 4 cantos e recalcula a matriz de perspectiva."""
        if len(corners) != 4:
            raise ValueError("Sao necessarios exatamente 4 pontos de cantos.")
        self.corners = [list(pt) for pt in corners]
        self._update_matrix()
        self.save()

    def _update_matrix(self):
        if len(self.corners) == 4:
            src = np.array(self.corners, dtype=np.float32)
            self.transform_matrix = cv.getPerspectiveTransform(src, self.dst_points)

    def is_calibrated(self) -> bool:
        return self.transform_matrix is not None and len(self.corners) == 4

    def warp(self, frame: np.ndarray) -> np.ndarray:
        """Aplica o corte e transformacao de perspectiva no frame da camera."""
        if not self.is_calibrated():
            # Se nao calibrado, redimensiona diretamente para o tamanho de saida
            return cv.resize(frame, (self.output_width, self.output_height))
        
        return cv.warpPerspective(frame, self.transform_matrix, (self.output_width, self.output_height))

    def draw_calibration_guides(self, frame: np.ndarray) -> np.ndarray:
        """Desenha o poligono dos 4 cantos na imagem bruta para depuracao visual."""
        debug_frame = frame.copy()
        if len(self.corners) > 0:
            pts = np.array(self.corners, dtype=np.int32)
            for i, pt in enumerate(self.corners):
                cv.circle(debug_frame, (int(pt[0]), int(pt[1])), 8, (0, 255, 0), -1)
                cv.putText(debug_frame, f"P{i+1}", (int(pt[0]) + 10, int(pt[1]) - 10),
                           cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if len(self.corners) == 4:
                cv.polylines(debug_frame, [pts], isClosed=True, color=(0, 255, 255), thickness=2)
        return debug_frame

    def interactive_calibrate(self, get_frame_func, window_name="Calibracao de Tabuleiro"):
        """Modo interativo com cliques do mouse para calibrar os 4 cantos."""
        temp_corners = []

        def on_click(event, x, y, flags, param):
            if event == cv.EVENT_LBUTTONDOWN and len(temp_corners) < 4:
                temp_corners.append([x, y])
                print(f"[Calibracao] Ponto {len(temp_corners)} ({PerspectiveCalibrator.CORNER_NAMES[len(temp_corners)-1]}): x={x}, y={y}")

        cv.namedWindow(window_name, cv.WINDOW_NORMAL)
        cv.setMouseCallback(window_name, on_click)

        print("\n--- MODO DE CALIBRACAO INTERATIVO ---")
        print("Clique sucessivamente nos 4 cantos da mesa/monitor na imagem:")
        print("  1: Superior Esquerdo (Top-Left)")
        print("  2: Superior Direito (Top-Right)")
        print("  3: Inferior Direito (Bottom-Right)")
        print("  4: Inferior Esquerdo (Bottom-Left)")
        print("Teclas: 'r' = resetar pontos clicados | 'c' ou Enter = confirmar quando tiver 4 pontos | 'ESC' = cancelar\n")

        while True:
            frame = get_frame_func()
            if frame is None:
                continue

            display_frame = frame.copy()
            # Desenha pontos atuais
            for i, pt in enumerate(temp_corners):
                cv.circle(display_frame, (pt[0], pt[1]), 8, (0, 0, 255), -1)
                cv.putText(display_frame, f"P{i+1}", (pt[0] + 10, pt[1] - 10),
                           cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            if len(temp_corners) > 1:
                pts = np.array(temp_corners, dtype=np.int32)
                cv.polylines(display_frame, [pts], isClosed=(len(temp_corners) == 4), color=(0, 255, 0), thickness=2)

            next_idx = len(temp_corners)
            instruction = (f"Clique no canto: {PerspectiveCalibrator.CORNER_NAMES[next_idx]}" 
                           if next_idx < 4 else "4 pontos marcados! Pressione 'C' ou Enter para confirmar.")
            
            # HUD Superior
            cv.rectangle(display_frame, (0, 0), (display_frame.shape[1], 45), (0, 0, 0), -1)
            cv.putText(display_frame, instruction, (20, 30), cv.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

            cv.imshow(window_name, display_frame)
            key = cv.waitKey(20) & 0xFF

            if key == 27: # ESC
                print("[Calibracao] Cancelada.")
                break
            elif key == ord('r'):
                print("[Calibracao] Pontos resetados.")
                temp_corners.clear()
            elif key in (ord('c'), 13): # 'c' ou Enter
                if len(temp_corners) == 4:
                    self.set_corners(temp_corners)
                    print("[Calibracao] Calibracao aplicada e salva!")
                    break
                else:
                    print(f"[Calibracao] Marque os 4 pontos primeiro (atual: {len(temp_corners)}).")

        cv.destroyWindow(window_name)
