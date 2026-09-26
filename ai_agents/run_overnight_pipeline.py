"""Pipeline Noturno Automatizado de Ordem Paranormal:

1. Inicia o servidor local de inferência (se necessário).
2. Gera centenas de turnos táticos canônicos com 8 protagonistas variados e criaturas da v1.3.
3. Encerra o servidor de inferência e limpa a VRAM da GPU.
4. Executa o treinamento LoRA completo com Unsloth em BF16 / Blackwell.
5. Salva os novos adaptadores e valida a inferência.
"""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("overnight_pipeline")

LLAMA_SERVER_EXE = Path(r"C:\Users\Deyvi\.unsloth\llama.cpp\build\bin\Release\llama-server.exe")
MODEL_GGUF = Path(
    r"C:\Users\Deyvi\.cache\huggingface\hub\models--unsloth--Qwen2.5-Omni-7B-GGUF\snapshots\de13a229d14d23c7149d6550e99ed3fe7778b733\Qwen2.5-Omni-7B-Q8_0.gguf"
)
SERVER_PORT = 33412
API_KEY = "07082007"


def is_server_alive() -> bool:
    import urllib.request
    try:
        url = f"http://127.0.0.1:{SERVER_PORT}/v1/models"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {API_KEY}"})
        with urllib.request.urlopen(req, timeout=3) as res:
            return res.status == 200
    except Exception:
        return False


def start_llama_server():
    if is_server_alive():
        logger.info("[Servidor LLM] Já está rodando e pronto para receber requisições.")
        return None

    logger.info(f"[Servidor LLM] Iniciando llama-server na porta {SERVER_PORT}...")
    cmd = [
        str(LLAMA_SERVER_EXE),
        "-m", str(MODEL_GGUF),
        "--port", str(SERVER_PORT),
        "--api-key", API_KEY,
        "--flash-attn", "on",
        "--no-context-shift",
        "-c", "4096",
        "--alias", "unsloth/Qwen2.5-Omni-7B-GGUF",
        "-ngl", "-1",
        "--fit", "off",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Aguarda o servidor subir
    for _ in range(30):
        time.sleep(2)
        if is_server_alive():
            logger.info("[Servidor LLM] Servidor online! Aquecendo modelo na VRAM...")
            try:
                import urllib.request, json
                warmup_payload = {
                    "model": "unsloth/Qwen2.5-Omni-7B-GGUF",
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 5
                }
                w_req = urllib.request.Request(
                    f"http://127.0.0.1:{SERVER_PORT}/v1/chat/completions",
                    data=json.dumps(warmup_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
                )
                with urllib.request.urlopen(w_req, timeout=90) as _:
                    pass
                logger.info("[Servidor LLM] Modelo 100% aquecido e pronto na VRAM!")
            except Exception as e:
                logger.warning(f"[Servidor LLM] Aquecimento concluiu com aviso: {e}")
            return proc
    logger.warning("[Servidor LLM] Tempo de espera excedido, mas continuando...")
    return proc


def stop_llama_server(proc=None):
    logger.info("[Servidor LLM] Encerrando servidor de inferência para liberar VRAM...")
    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            pass
    # Força encerramento se ainda houver processo
    os.system("taskkill /F /IM llama-server.exe >nul 2>&1")
    time.sleep(3)
    logger.info("[VRAM] Memória de vídeo liberada para o treinamento!")


def main():
    print("=" * 75)
    print("  ORDEM PARANORMAL RPG - PIPELINE NOTURNO AUTOMATIZADO")
    print("  1. Geração Canônica v1.3 com 8 Protagonistas")
    print("  2. Treinamento do Adaptador LoRA no Unsloth")
    print("=" * 75 + "\n")

    # 1. Inicia o servidor de inferência
    server_proc = start_llama_server()

    # 2. Executa a geração de turnos canônicos
    logger.info("[Fase 1/3] Iniciando geração de 250 turnos canônicos adicionais...")
    from ai_agents.batch_dataset_generator import run_batch_generation
    run_batch_generation(total_turns=250)

    # 3. Para o servidor e libera VRAM
    stop_llama_server(server_proc)

    # 4. Executa o treinamento LoRA com o Unsloth
    logger.info("[Fase 2/3] Iniciando treinamento LoRA com Unsloth...")
    from ai_agents.train_lora_unsloth import run_training
    run_training(model_name="unsloth/Qwen2.5-7B-Instruct-bnb-4bit")

    # 5. Validação final
    logger.info("[Fase 3/3] Treinamento finalizado com sucesso! Executando teste de inferência...")
    from ai_agents.test_trained_agent import test_inference
    test_inference()

    print("\n" + "=" * 75)
    print("  [CONCLUÍDO COM SUCESSO]")
    print("  O modelo foi treinado com o novo compêndio e está pronto para jogar!")
    print("=" * 75)


if __name__ == "__main__":
    main()
