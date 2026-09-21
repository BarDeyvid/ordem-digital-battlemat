"""Simulador de telemetria de tokens para desenvolvimento e testes do Digital Battlemat.

Permite simular o envio de tokens via UDP para o Unreal Engine sem precisar
de câmera física ou miniaturas impressas na mesa.
"""

import argparse
import json
import math
import socket
import sys
import time
from typing import Dict, Any

import cv2 as cv
import numpy as np

from tracker.network import UdpSender
from tracker import config

DEFAULT_UDP_IP = config.UDP_IP
DEFAULT_UDP_PORT = config.UDP_PORT
DEFAULT_OSC_PORT = config.OSC_PORT

TOKEN_PRESETS = {
    1: {"name": "Investigador 1", "type": "investigador", "color": (255, 200, 50)},
    2: {"name": "Investigador 2", "type": "investigador", "color": (255, 180, 0)},
    3: {"name": "Investigador 3", "type": "investigador", "color": (200, 255, 0)},
    4: {"name": "Investigador 4", "type": "investigador", "color": (150, 220, 50)},
    5: {"name": "Investigador 5", "type": "investigador", "color": (220, 220, 100)},
    11: {"name": "Zumbi de Sangue", "type": "criatura_sangue", "color": (30, 30, 230)},
    12: {"name": "Esqueleto de Lodo", "type": "criatura_morte", "color": (80, 80, 80)},
    13: {"name": "Anomalia Eletrica", "type": "criatura_energia", "color": (230, 100, 200)},
    14: {"name": "Existido", "type": "criatura_conhecimento", "color": (0, 215, 255)},
    20: {"name": "Aliado Civil", "type": "npc", "color": (180, 230, 180)},
}


class TokenSimulator:
    def __init__(self, ip: str = DEFAULT_UDP_IP, port: int = DEFAULT_UDP_PORT, osc_port: int = DEFAULT_OSC_PORT, fps: int = 30):
        self.ip = ip
        self.port = port
        self.osc_port = osc_port
        self.fps = fps
        self.interval = 1.0 / fps
        self.sender = UdpSender(ip=self.ip, port=self.port, osc_port=self.osc_port, enable_osc=config.ENABLE_OSC)

        self.tokens: Dict[int, Dict[str, Any]] = {
            1: {"id": 1, "type": "investigador", "x": 0.35, "y": 0.50, "rotation": 90.0, "active": True},
            2: {"id": 2, "type": "investigador", "x": 0.40, "y": 0.60, "rotation": 45.0, "active": True},
            11: {"id": 11, "type": "criatura_sangue", "x": 0.70, "y": 0.50, "rotation": 270.0, "active": True},
        }

        self.selected_token_id = 1
        self.dragging = False
        self.canvas_w = 960
        self.canvas_h = 540

    def send_telemetry(self):
        active_tokens = [
            {
                "id": t["id"],
                "type": t["type"],
                "x": round(t["x"], 4),
                "y": round(t["y"], 4),
                "rotation": round(t["rotation"] % 360.0, 1),
            }
            for t in self.tokens.values()
            if t.get("active", True)
        ]

        self.sender.send_tokens(active_tokens)

    def run_circle_mode(self):
        print(f"\n[Modo Circulo/Patrulha] Enviando telemetria para {self.ip}:{self.port} a {self.fps} FPS.")
        print("Pressione Ctrl+C para encerrar.\n")

        t0 = time.time()
        try:
            while True:
                elapsed = time.time() - t0

                self.tokens[1]["x"] = 0.5 + 0.25 * math.cos(elapsed * 0.8)
                self.tokens[1]["y"] = 0.5 + 0.25 * math.sin(elapsed * 0.8)
                self.tokens[1]["rotation"] = (math.degrees(elapsed * 0.8) + 90.0) % 360.0

                self.tokens[2]["x"] = 0.5 + 0.35 * math.cos(-elapsed * 0.5 + 1.5)
                self.tokens[2]["y"] = 0.5 + 0.15 * math.sin(-elapsed * 0.5 + 1.5)
                self.tokens[2]["rotation"] = (math.degrees(-elapsed * 0.5 + 1.5) + 90.0) % 360.0

                self.tokens[11]["x"] = 0.5 + 0.15 * math.sin(elapsed * 0.3)
                self.tokens[11]["y"] = 0.5 + 0.30 * math.cos(elapsed * 0.3)
                self.tokens[11]["rotation"] = (math.degrees(elapsed * 0.3)) % 360.0

                self.send_telemetry()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("\n[Finalizado] Simulador encerrado.")

    def run_combat_mode(self):
        print(f"\n[Modo Combate Tático] Enviando telemetria para {self.ip}:{self.port} a {self.fps} FPS.")
        print("Pressione Ctrl+C para encerrar.\n")

        self.tokens[13] = {"id": 13, "type": "criatura_energia", "x": 0.8, "y": 0.3, "rotation": 180.0, "active": True}
        self.tokens[3] = {"id": 3, "type": "investigador", "x": 0.2, "y": 0.7, "rotation": 0.0, "active": True}

        t0 = time.time()
        try:
            while True:
                elapsed = time.time() - t0

                target_x = 0.3 + 0.1 * math.sin(elapsed * 0.5)
                target_y = 0.4 + 0.1 * math.cos(elapsed * 0.6)
                self.tokens[1]["x"] = target_x
                self.tokens[1]["y"] = target_y
                dx = self.tokens[11]["x"] - target_x
                dy = self.tokens[11]["y"] - target_y
                self.tokens[1]["rotation"] = math.degrees(math.atan2(dy, dx)) % 360.0

                aggro_step = math.sin(elapsed * 1.2)
                self.tokens[11]["x"] = 0.55 + (0.15 if aggro_step > 0 else 0.05) * aggro_step
                self.tokens[11]["y"] = 0.45 + 0.1 * math.cos(elapsed * 0.7)
                self.tokens[11]["rotation"] = math.degrees(math.atan2(-dy, -dx)) % 360.0

                if int(elapsed * 2) % 6 == 0:
                    self.tokens[13]["rotation"] = (self.tokens[13]["rotation"] + 45) % 360.0
                self.tokens[13]["x"] = 0.75 + 0.08 * math.sin(elapsed * 2.5)
                self.tokens[13]["y"] = 0.30 + 0.08 * math.cos(elapsed * 2.5)

                self.send_telemetry()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("\n[Finalizado] Simulador encerrado.")

    def _mouse_event(self, event, x, y, flags, param):
        norm_x = max(0.0, min(1.0, x / self.canvas_w))
        norm_y = max(0.0, min(1.0, y / self.canvas_h))

        if event == cv.EVENT_LBUTTONDOWN:
            clicked_id = None
            min_dist = 0.05
            for tid, t in self.tokens.items():
                if not t.get("active", True):
                    continue
                d = math.hypot(t["x"] - norm_x, t["y"] - norm_y)
                if d < min_dist:
                    clicked_id = tid
                    min_dist = d

            if clicked_id is not None:
                self.selected_token_id = clicked_id
                self.dragging = True
            else:
                if self.selected_token_id in self.tokens:
                    self.tokens[self.selected_token_id]["x"] = norm_x
                    self.tokens[self.selected_token_id]["y"] = norm_y
                    self.dragging = True

        elif event == cv.EVENT_MOUSEMOVE and self.dragging:
            if self.selected_token_id in self.tokens:
                self.tokens[self.selected_token_id]["x"] = norm_x
                self.tokens[self.selected_token_id]["y"] = norm_y

        elif event == cv.EVENT_LBUTTONUP:
            self.dragging = False

        elif event == cv.EVENT_MOUSEWHEEL:
            delta = 15.0 if flags > 0 else -15.0
            if self.selected_token_id in self.tokens:
                curr_rot = self.tokens[self.selected_token_id]["rotation"]
                self.tokens[self.selected_token_id]["rotation"] = (curr_rot + delta) % 360.0

    def run_interactive_gui(self):
        win_name = "Battlemat Token Simulator (Dev Mode)"
        cv.namedWindow(win_name, cv.WINDOW_AUTOSIZE)
        cv.setMouseCallback(win_name, self._mouse_event)

        print("\n" + "=" * 60)
        print("  BATTLEMAT TOKEN SIMULATOR - MODO INTERATIVO")
        print("=" * 60)
        print("Controles na janela gráfica:")
        print("  - Clique e Arraste com o Mouse : Move o token selecionado")
        print("  - Roda do Mouse (Scroll)       : Gira o token selecionado")
        print("  - Teclas 1 a 5                 : Seleciona Investigador 1 a 5")
        print("  - Tecla S                      : Seleciona Criatura de Sangue (ID 11)")
        print("  - Tecla M                      : Seleciona Criatura de Morte (ID 12)")
        print("  - Tecla E                      : Seleciona Criatura de Energia (ID 13)")
        print("  - Tecla C                      : Seleciona Criatura de Conhecimento (ID 14)")
        print("  - Tecla N                      : Seleciona NPC Aliado (ID 20)")
        print("  - Espaço                       : Ativa / Desativa token selecionado")
        print("  - Teclas A / D                 : Gira token +- 10 graus")
        print("  - Tecla Q ou ESC               : Sair")
        print(f"Transmitindo UDP -> {self.ip}:{self.port} a {self.fps} FPS")
        print("=" * 60 + "\n")

        last_packet_time = time.time()

        while True:
            canvas = np.full((self.canvas_h, self.canvas_w, 3), 20, dtype=np.uint8)

            grid_size = 60
            for gx in range(0, self.canvas_w, grid_size):
                cv.line(canvas, (gx, 0), (gx, self.canvas_h), (35, 35, 35), 1)
            for gy in range(0, self.canvas_h, grid_size):
                cv.line(canvas, (0, gy), (self.canvas_w, gy), (35, 35, 35), 1)

            for tid, t in self.tokens.items():
                if not t.get("active", True):
                    continue

                preset = TOKEN_PRESETS.get(tid, {"name": f"Token {tid}", "color": (200, 200, 200)})
                color = preset["color"]
                px = int(t["x"] * self.canvas_w)
                py = int(t["y"] * self.canvas_h)
                rot_rad = math.radians(t["rotation"])

                is_selected = (tid == self.selected_token_id)
                radius = 24 if is_selected else 20

                if is_selected:
                    cv.circle(canvas, (px, py), radius + 6, (0, 255, 255), 2, cv.LINE_AA)

                cv.circle(canvas, (px, py), radius, color, -1, cv.LINE_AA)
                cv.circle(canvas, (px, py), radius, (255, 255, 255), 2, cv.LINE_AA)

                dir_len = radius + 12
                dir_x = int(px + dir_len * math.cos(rot_rad))
                dir_y = int(py + dir_len * math.sin(rot_rad))
                cv.arrowedLine(canvas, (px, py), (dir_x, dir_y), (0, 255, 255) if is_selected else (255, 255, 255), 2, cv.LINE_AA, tipLength=0.3)

                label = f"ID {tid}: {preset['name']}"
                cv.putText(canvas, label, (px - 40, py - radius - 8), cv.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1, cv.LINE_AA)

            selected_preset = TOKEN_PRESETS.get(self.selected_token_id, {"name": f"Token {self.selected_token_id}"})
            sel_token = self.tokens.get(self.selected_token_id, {"x": 0, "y": 0, "rotation": 0, "active": False})
            status_text = (
                f"Selecionado: ID {self.selected_token_id} ({selected_preset['name']}) | "
                f"Pos: ({sel_token['x']:.3f}, {sel_token['y']:.3f}) | "
                f"Rot: {sel_token['rotation']:.1f} deg | "
                f"Ativo: {sel_token.get('active', True)}"
            )
            cv.rectangle(canvas, (0, 0), (self.canvas_w, 36), (10, 10, 10), -1)
            cv.putText(canvas, status_text, (16, 24), cv.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1, cv.LINE_AA)

            now = time.time()
            if now - last_packet_time >= self.interval:
                self.send_telemetry()
                last_packet_time = now

            cv.imshow(win_name, canvas)
            key = cv.waitKey(15) & 0xFF

            if key in (ord('q'), 27):
                break
            elif ord('1') <= key <= ord('5'):
                tid = key - ord('0')
                self._select_or_create_token(tid)
            elif key in (ord('s'), ord('S')):
                self._select_or_create_token(11)
            elif key in (ord('m'), ord('M')):
                self._select_or_create_token(12)
            elif key in (ord('e'), ord('E')):
                self._select_or_create_token(13)
            elif key in (ord('c'), ord('C')):
                self._select_or_create_token(14)
            elif key in (ord('n'), ord('N')):
                self._select_or_create_token(20)
            elif key == ord(' '):
                if self.selected_token_id in self.tokens:
                    curr = self.tokens[self.selected_token_id].get("active", True)
                    self.tokens[self.selected_token_id]["active"] = not curr
            elif key in (ord('a'), ord('A')):
                if self.selected_token_id in self.tokens:
                    self.tokens[self.selected_token_id]["rotation"] = (self.tokens[self.selected_token_id]["rotation"] - 10.0) % 360.0
            elif key in (ord('d'), ord('D')):
                if self.selected_token_id in self.tokens:
                    self.tokens[self.selected_token_id]["rotation"] = (self.tokens[self.selected_token_id]["rotation"] + 10.0) % 360.0

        cv.destroyAllWindows()
        print("[Finalizado] Simulador encerrado.")

    def _select_or_create_token(self, tid: int):
        self.selected_token_id = tid
        if tid not in self.tokens:
            preset = TOKEN_PRESETS.get(tid, {"type": "token"})
            self.tokens[tid] = {
                "id": tid,
                "type": preset["type"],
                "x": 0.5,
                "y": 0.5,
                "rotation": 0.0,
                "active": True
            }
        else:
            self.tokens[tid]["active"] = True


def main():
    parser = argparse.ArgumentParser(description="Simulador de Telemetria de Tokens para Digital Battlemat")
    parser.add_argument("--mode", choices=["interactive", "circle", "combat"], default="interactive", help="Modo do simulador")
    parser.add_argument("--ip", default=DEFAULT_UDP_IP, help=f"IP de destino UDP (padrao: {DEFAULT_UDP_IP})")
    parser.add_argument("--port", type=int, default=DEFAULT_UDP_PORT, help=f"Porta UDP (padrao: {DEFAULT_UDP_PORT})")
    parser.add_argument("--fps", type=int, default=30, help="Taxa de envio de pacotes por segundo (padrao: 30)")

    args = parser.parse_args()
    sim = TokenSimulator(ip=args.ip, port=args.port, fps=args.fps)

    if args.mode == "circle":
        sim.run_circle_mode()
    elif args.mode == "combat":
        sim.run_combat_mode()
    else:
        sim.run_interactive_gui()


if __name__ == "__main__":
    main()
