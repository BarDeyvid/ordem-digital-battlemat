import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent

class AgentConfig(BaseModel):
    # Provedor do LLM (Unsloth Studio / llama-server local)
    llm_api_base: str = os.getenv("LLM_API_BASE", "http://127.0.0.1:33412/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "07082007")
    
    # Modelo alvo
    model_name: str = os.getenv("LLM_MODEL", "unsloth/Qwen2.5-Omni-7B-GGUF")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.4"))
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "512"))

    # Conexão com o Battlemat (Unreal Engine / Bridge)
    unreal_udp_ip: str = os.getenv("UDP_IP", "127.0.0.1")
    unreal_udp_port: int = int(os.getenv("UDP_PORT", "8888"))
    bridge_http_url: str = os.getenv("BRIDGE_HTTP_URL", "http://127.0.0.1:8080")
    
    # Armazenamento do Dataset para o Fine-Tuning LoRA (Unsloth)
    dataset_output_path: Path = BASE_DIR / "dataset" / "unsloth_training_dataset.jsonl"

    # Vozes ElevenLabs para a Mesa Viva
    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")
    elevenlabs_model_id: str = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
    audio_cache_dir: Path = BASE_DIR / "audio_cache"

config = AgentConfig()

