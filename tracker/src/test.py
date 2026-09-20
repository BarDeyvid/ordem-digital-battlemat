import cv2 as cv
import numpy as np
import socket
import json
import time

# ==========================================
# Configurações de Conexão e Streaming
# ==========================================
# URL do stream RTSP da câmera (ou troque por 0 para testar com webcam integrada)
RTSP_URL = "rtsp://admin:0708@192.168.1.6:5543/live/channel0"

# Destino UDP (Unreal Engine)
UDP_IP = "127.0.0.1"
UDP_PORT = 8888

# ==========================================
# Inicialização do Socket UDP
# ==========================================
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_udp_payload(data: dict):
    """Envia um dicionário codificado em JSON via UDP para a Unreal Engine."""
    try:
        message = json.dumps(data).encode("utf-8")
        sock.sendto(message, (UDP_IP, UDP_PORT))
        print(f"[UDP -> Unreal] Enviado para {UDP_IP}:{UDP_PORT}: {data}")
    except Exception as e:
        print(f"[UDP Erro] Falha ao enviar mensagem: {e}")

# Coordenadas do último clique para envio / debug
last_click = None

def mouse_callback(event, x, y, flags, param):
    """Detecta cliques do mouse na janela para testar envio de coordenadas para a Unreal."""
    global last_click
    if event == cv.EVENT_LBUTTONDOWN:
        last_click = (x, y)
        frame_width, frame_height = param
        
        # Coordenadas normalizadas de 0.0 a 1.0 (úteis para mapping no tabuleiro na Unreal)
        norm_x = round(x / frame_width, 4) if frame_width else 0
        norm_y = round(y / frame_height, 4) if frame_height else 0
        
        payload = {
            "type": "click_target",
            "pixel_x": x,
            "pixel_y": y,
            "norm_x": norm_x,
            "norm_y": norm_y,
            "timestamp": time.time()
        }
        send_udp_payload(payload)

def open_video_capture(source):
    """Inicializa a captura de vídeo com parâmetros de baixa latência para RTSP."""
    print(f"\n[Info] Tentando conectar à fonte de vídeo: {source}")
    
    # Dica para OpenCV usar TCP no RTSP (evita corrupção de pacotes) e buffer mínimo
    cap = cv.VideoCapture(source, cv.CAP_FFMPEG)
    
    # Reduz buffer interno para evitar atraso (latência acumulada) no RTSP
    cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
    
    return cap

def main():
    print("=" * 60)
    print("      TRACKER & RTSP TESTER - ORDEM DIGITAL BATTLEMAT       ")
    print("=" * 60)
    print(f"OpenCV version: {cv.__version__}")
    print(f"Alvo UDP Unreal: {UDP_IP}:{UDP_PORT}")
    print(f"Stream RTSP: {RTSP_URL}")
    print("\nControles:")
    print("  - Clique esquerdo: envia coordenadas do ponto clicado via UDP")
    print("  - Tecla 'u': envia ping de teste via UDP")
    print("  - Tecla 's': salva screenshot atual ('snapshot.png')")
    print("  - Tecla 'q' ou ESC: encerra o programa")
    print("=" * 60)

    # Tenta abrir o RTSP primeiro; se o usuário quiser testar webcam se falhar, pode alterar source
    source = RTSP_URL
    cap = open_video_capture(source)

    if not cap.isOpened():
        print(f"[Aviso] Não foi possível abrir o stream RTSP: {source}")
        print("[Info] Verifique se a câmera está ligada e acessível na rede.")
        use_webcam = input("Deseja tentar abrir a webcam local (0) para testes? (s/n): ").strip().lower()
        if use_webcam in ['s', 'sim', 'y', 'yes']:
            source = 0
            cap = open_video_capture(source)
            if not cap.isOpened():
                print("[Erro] Não foi possível abrir nem o RTSP nem a webcam local. Encerrando.")
                return
        else:
            print("[Info] Encerrando.")
            return

    window_name = "Battlemat Tracker - Video Stream"
    cv.namedWindow(window_name, cv.WINDOW_NORMAL)

    # Variáveis para cálculo de FPS
    prev_time = time.time()
    fps = 0.0
    frame_count = 0

    while True:
        ret, frame = cap.read()
        
        if not ret or frame is None:
            print("[Aviso] Frame vazio ou conexão perdida. Tentando reconectar...")
            time.sleep(1)
            cap.release()
            cap = open_video_capture(source)
            continue

        frame_count += 1
        current_time = time.time()
        time_diff = current_time - prev_time
        if time_diff >= 1.0:
            fps = frame_count / time_diff
            frame_count = 0
            prev_time = current_time

        h, w = frame.shape[:2]
        
        # Configura o callback do mouse passando o tamanho atual da tela
        cv.setMouseCallback(window_name, mouse_callback, (w, h))

        # Desenha marcador do último clique, se houver
        if last_click is not None:
            cv.circle(frame, last_click, 8, (0, 0, 255), -1)
            cv.circle(frame, last_click, 14, (0, 255, 255), 2)
            coord_text = f"Click: {last_click[0]}, {last_click[1]}"
            cv.putText(frame, coord_text, (last_click[0] + 10, last_click[1] - 10),
                       cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv.LINE_AA)

        # Desenha informações de HUD no topo
        hud_bg = frame.copy()
        cv.rectangle(hud_bg, (0, 0), (w, 40), (0, 0, 0), -1)
        cv.addWeighted(hud_bg, 0.6, frame, 0.4, 0, frame)

        status_text = f"FPS: {fps:.1f} | Res: {w}x{h} | UDP: {UDP_IP}:{UDP_PORT} | [Q]: Sair | [U]: Ping UDP"
        cv.putText(frame, status_text, (10, 25), cv.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv.LINE_AA)

        # Exibe o frame
        cv.imshow(window_name, frame)

        # Trata comandos de teclado
        key = cv.waitKey(1) & 0xFF
        if key in [ord('q'), 27]: # 'q' ou ESC
            print("\n[Info] Encerrando visualizador...")
            break
        elif key == ord('u'):
            payload = {
                "type": "ping",
                "message": "Hello Unreal from Tracker!",
                "timestamp": time.time()
            }
            send_udp_payload(payload)
        elif key == ord('s'):
            filename = "snapshot.png"
            cv.imwrite(filename, frame)
            print(f"[Info] Snapshot salvo como '{filename}'.")

    # Finalização limpa de recursos
    cap.release()
    cv.destroyAllWindows()
    sock.close()
    print("[Info] Recursos liberados e programa encerrado com sucesso.")

if __name__ == "__main__":
    main()
