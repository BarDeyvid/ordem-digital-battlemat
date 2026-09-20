import sys
import time
import argparse
import logging
from pathlib import Path
import cv2 as cv

from tracker import config
from tracker.calibration import PerspectiveCalibrator
from tracker.detector import TokenDetector
from tracker.network import UdpSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("tracker")

def parse_args():
    parser = argparse.ArgumentParser(description="Battlemat Tracker - Ordem Paranormal")
    parser.add_argument("--source", type=str, default=config.CAMERA_SOURCE, 
                        help="Fonte de video (URL RTSP ou indice de camera local, ex: 0)")
    parser.add_argument("--udp-ip", type=str, default=config.UDP_IP, 
                        help="IP de destino para envio UDP (Unreal Engine)")
    parser.add_argument("--udp-port", type=int, default=config.UDP_PORT, 
                        help="Porta de destino UDP")
    parser.add_argument("--headless", action="store_true", default=config.HEADLESS, 
                        help="Executa em modo headless (sem janela GUI, ideal para Docker)")
    parser.add_argument("--calibrate", action="store_true", 
                        help="Abre diretamente a ferramenta de calibracao dos 4 cantos")
    return parser.parse_args()

def open_capture(source):
    """Abre conexão com câmera local ou RTSP com baixa latência."""
    logger.info(f"Conectando a fonte de video: {source}")
    # Se for dígito, converte para int (webcam local)
    if isinstance(source, str) and source.isdigit():
        src = int(source)
    else:
        src = source

    if isinstance(src, str) and src.startswith("rtsp://"):
        cap = cv.VideoCapture(src, cv.CAP_FFMPEG)
        cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
    else:
        cap = cv.VideoCapture(src)

    return cap

def main():
    args = parse_args()

    print("=" * 65)
    print("      ORDEM PARANORMAL - DIGITAL BATTLEMAT TRACKER (BACKEND)      ")
    print("=" * 65)
    print(f"Fonte de Video: {args.source}")
    print(f"Destino UDP:   {args.udp_ip}:{args.udp_port}")
    print(f"Modo Headless: {args.headless}")
    print("=" * 65)

    # 1. Inicializa componentes
    calibrator = PerspectiveCalibrator(
        calibration_path=config.CALIBRATION_FILE,
        output_width=config.WARP_WIDTH,
        output_height=config.WARP_HEIGHT
    )

    detector = TokenDetector(
        dict_name=config.ARUCO_DICT_NAME,
        tokens_config_path=config.TOKENS_CONFIG_FILE,
        min_pos_delta=config.MIN_POS_DELTA,
        min_rot_delta=config.MIN_ROT_DELTA,
        smoothing=config.SMOOTHING_FACTOR
    )

    udp_sender = UdpSender(ip=args.udp_ip, port=args.udp_port)

    # 2. Abre captura
    cap = open_capture(args.source)
    if not cap.isOpened():
        logger.error(f"Nao foi possivel abrir a fonte de video: {args.source}")
        if not args.headless and str(args.source) != "0":
            choice = input("Deseja tentar abrir a webcam local (0)? (s/n): ").strip().lower()
            if choice in ("s", "sim", "y", "yes"):
                args.source = 0
                cap = open_capture(args.source)
        
        if not cap.isOpened():
            logger.error("Falha fatal: Nenhuma camera disponivel. Encerrando.")
            sys.exit(1)

    def get_fresh_frame():
        ret, frm = cap.read()
        return frm if ret else None

    # Calibração inicial solicitada via CLI
    if args.calibrate and not args.headless:
        calibrator.interactive_calibrate(get_fresh_frame)

    window_name = "Battlemat Tracker - Ordem Paranormal"
    if not args.headless:
        cv.namedWindow(window_name, cv.WINDOW_NORMAL)

    # Estados de execução
    show_warped_view = True
    udp_enabled = True
    prev_time = time.time()
    fps = 0.0
    frame_count = 0
    last_log_time = time.time()

    try:
        while True:
            ret, raw_frame = cap.read()
            if not ret or raw_frame is None:
                logger.warning("Frame vazio ou sinal de video perdido. Tentando reconectar...")
                time.sleep(1)
                cap.release()
                cap = open_capture(args.source)
                continue

            frame_count += 1
            now = time.time()
            dt = now - prev_time
            if dt >= 1.0:
                fps = frame_count / dt
                frame_count = 0
                prev_time = now

            # 3. Processamento de Perspectiva (Warp)
            warped_frame = calibrator.warp(raw_frame)

            # 4. Detecção de Marcadores ArUco no tabuleiro retificado
            tokens = detector.detect(warped_frame)

            # 5. Transmissão UDP para a Unreal
            if udp_enabled and len(tokens) > 0:
                # Remove dados internos de rendering de pixels para manter o payload leve e fiel ao README
                clean_tokens = [
                    {
                        "id": t["id"],
                        "type": t["type"],
                        "x": t["x"],
                        "y": t["y"],
                        "rotation": t["rotation"]
                    }
                    for t in tokens
                ]
                udp_sender.send_tokens(clean_tokens, timestamp=now)

            # 6. Modo Headless (Docker/Servidor)
            if args.headless:
                if now - last_log_time >= 2.0:
                    last_log_time = now
                    token_summary = ", ".join([f"ID {t['id']}({t['type']}) @ ({t['x']},{t['y']})" for t in tokens]) or "nenhum"
                    logger.info(f"FPS: {fps:.1f} | Tokens ativos ({len(tokens)}): [{token_summary}] | UDP Enviados: {udp_sender.sent_packets_count}")
                continue

            # 7. Interface Gráfica / HUD (Quando não headless)
            if show_warped_view:
                display = detector.draw_tokens(warped_frame, tokens)
                view_mode_name = "TABULEIRO RETIFICADO"
            else:
                display = calibrator.draw_calibration_guides(raw_frame)
                view_mode_name = "CAMERA BRUTA"

            # Overlay HUD
            hud_h = 45
            hud = display.copy()
            cv.rectangle(hud, (0, 0), (display.shape[1], hud_h), (20, 20, 20), -1)
            cv.addWeighted(hud, 0.7, display, 0.3, 0, display)

            calib_status = "CALIBRADO" if calibrator.is_calibrated() else "SEM CALIBRACAO (pressione 'C')"
            status_line = (f"FPS: {fps:.1f} | Tokens: {len(tokens)} | Modo: {view_mode_name} | "
                           f"UDP: {'ATIVO' if udp_enabled else 'PAUSADO'} | Status: {calib_status}")
            cv.putText(display, status_line, (15, 28), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv.LINE_AA)

            cv.imshow(window_name, display)

            # Controles de Teclado
            key = cv.waitKey(1) & 0xFF
            if key in (ord('q'), 27): # 'Q' ou ESC
                logger.info("Encerramento solicitado pelo usuario.")
                break
            elif key == ord('c'):
                calibrator.interactive_calibrate(get_fresh_frame)
            elif key == ord('w'):
                show_warped_view = not show_warped_view
                logger.info(f"Modo de visualizacao alterado: {'Warped' if show_warped_view else 'Raw'}")
            elif key == ord('p'):
                udp_enabled = not udp_enabled
                logger.info(f"Transmissao UDP: {'Ativada' if udp_enabled else 'Pausada'}")
            elif key == ord('s'):
                snap_path = f"snapshot_{int(now)}.png"
                cv.imwrite(snap_path, display)
                logger.info(f"Snapshot salvo em {snap_path}")

    except KeyboardInterrupt:
        logger.info("Interrompido por sinal SIGINT (Ctrl+C).")
    finally:
        cap.release()
        if not args.headless:
            cv.destroyAllWindows()
        udp_sender.close()
        logger.info(f"Recursos liberados. Total de pacotes UDP transmitidos: {udp_sender.sent_packets_count}")

if __name__ == "__main__":
    main()
