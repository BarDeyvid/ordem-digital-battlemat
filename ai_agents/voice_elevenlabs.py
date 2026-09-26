"""Módulo de Voz ElevenLabs para a Mesa Viva de Ordem Paranormal.

Responsável por:
- Gerenciamento de credenciais da API ElevenLabs.
- Mapeamento sonoro dos 8 protagonistas + O Mestre da Ordem.
- Sistema de Cache em Disco com hash SHA256/MD5 para preservação de quota.
- Reprodução de áudio assíncrona não-bloqueante compatível com Windows (MCI / PowerShell).
- Fallback gracioso para modo offline ou ausência de chave de API.
"""

import ctypes
from ctypes import wintypes
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from typing import Dict, Optional, Tuple, Any

import requests

from ai_agents.config import config, BASE_DIR

logger = logging.getLogger("ai_agents.voice")

# Diretório padrão para cache local de arquivos de áudio
AUDIO_CACHE_DIR = config.audio_cache_dir if hasattr(config, "audio_cache_dir") else BASE_DIR / "audio_cache"


class VoiceProfile:
    """Perfil acústico e parâmetros de síntese de voz de um personagem."""

    def __init__(
        self,
        speaker_key: str,
        display_name: str,
        voice_id: str,
        description: str,
        stability: float = 0.5,
        similarity_boost: float = 0.8,
        style: float = 0.0,
        use_speaker_boost: bool = True,
    ):
        self.speaker_key = speaker_key.lower().strip()
        self.display_name = display_name
        self.voice_id = voice_id
        self.description = description
        self.stability = stability
        self.similarity_boost = similarity_boost
        self.style = style
        self.use_speaker_boost = use_speaker_boost

    def to_settings_dict(self) -> Dict[str, Any]:
        return {
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "style": self.style,
            "use_speaker_boost": self.use_speaker_boost,
        }

    def __repr__(self) -> str:
        return f"<VoiceProfile {self.display_name} (ID: {self.voice_id[:8]}... - {self.description})>"


# Mapeamento Canônico de Vozes dos Protagonistas + Mestre
# IDs pré-configurados utilizando as melhores vozes do catálogo ElevenLabs
# permitindo override instantâneo via variáveis de ambiente ELEVENLABS_VOICE_<NOME>
DEFAULT_VOICE_PROFILES: Dict[str, VoiceProfile] = {
    "arthur": VoiceProfile(
        speaker_key="arthur",
        display_name="Arthur Cervero",
        voice_id=os.getenv("ELEVENLABS_VOICE_ARTHUR", "pNInz6obpgDQGcFmaJgB"),  # Adam: grave, forte e determinada
        description="Voz grave, forte e determinada",
        stability=0.45,
        similarity_boost=0.85,
        style=0.15,
        use_speaker_boost=True,
    ),
    "kaiser": VoiceProfile(
        speaker_key="kaiser",
        display_name="Kaiser",
        voice_id=os.getenv("ELEVENLABS_VOICE_KAISER", "ErXwobaYiN019PkySvjV"),  # Antoni: jovem, ágil e focada
        description="Voz jovem, ágil e focada",
        stability=0.50,
        similarity_boost=0.80,
        style=0.10,
        use_speaker_boost=True,
    ),
    "dante": VoiceProfile(
        speaker_key="dante",
        display_name="Dante",
        voice_id=os.getenv("ELEVENLABS_VOICE_DANTE", "TxGEqnHWrfWFTfGW9XjX"),   # Josh: sombria, misteriosa e sussurrada
        description="Voz sombria, misteriosa e sussurrada",
        stability=0.65,
        similarity_boost=0.85,
        style=0.25,
        use_speaker_boost=True,
    ),
    "joui": VoiceProfile(
        speaker_key="joui",
        display_name="Joui Jouki",
        voice_id=os.getenv("ELEVENLABS_VOICE_JOUI", "IKne3meq5aSn9XLyUdCD"),    # Charlie: honrada, energética e respeitosa
        description="Voz honrada, energética e respeitosa",
        stability=0.40,
        similarity_boost=0.85,
        style=0.20,
        use_speaker_boost=True,
    ),
    "liz": VoiceProfile(
        speaker_key="liz",
        display_name="Liz Sena",
        voice_id=os.getenv("ELEVENLABS_VOICE_LIZ", "EXAVITQu4vr4xnSDxMaL"),     # Bella: serena, empática e científica
        description="Voz serena, empática e científica",
        stability=0.60,
        similarity_boost=0.85,
        style=0.05,
        use_speaker_boost=True,
    ),
    "thiago": VoiceProfile(
        speaker_key="thiago",
        display_name="Thiago Fritz",
        voice_id=os.getenv("ELEVENLABS_VOICE_THIAGO", "onwK4e9ZLuTAKqWW03F9"),  # Daniel: madura, firme e de liderança
        description="Voz madura, firme e de liderança",
        stability=0.55,
        similarity_boost=0.80,
        style=0.15,
        use_speaker_boost=True,
    ),
    "rubens": VoiceProfile(
        speaker_key="rubens",
        display_name="Rubens Naluti",
        voice_id=os.getenv("ELEVENLABS_VOICE_RUBENS", "CYw3kZ02Hs0563khs1Fj"),  # Dave: prática, direta e rouca
        description="Voz prática, direta e rouca",
        stability=0.50,
        similarity_boost=0.80,
        style=0.20,
        use_speaker_boost=True,
    ),
    "milo": VoiceProfile(
        speaker_key="milo",
        display_name="Milo Foster",
        voice_id=os.getenv("ELEVENLABS_VOICE_MILO", "yoZ06aMxZJJ28mfd3POQ"),    # Sam: excêntrica e intensa
        description="Voz excêntrica e intensa",
        stability=0.35,
        similarity_boost=0.80,
        style=0.30,
        use_speaker_boost=True,
    ),
    "mestre": VoiceProfile(
        speaker_key="mestre",
        display_name="O Mestre",
        voice_id=os.getenv("ELEVENLABS_VOICE_MESTRE", "JBFqnCBsd6RMkjVDRZzb"),  # George: profunda e cinematográfica de suspense
        description="Voz profunda e cinematográfica de suspense",
        stability=0.70,
        similarity_boost=0.85,
        style=0.35,
        use_speaker_boost=True,
    ),
}

# Alias adicionais para facilitar resolução flexível
SPEAKER_ALIASES = {
    "arthur cervero": "arthur",
    "artur": "arthur",
    "kaiser": "kaiser",
    "angel": "kaiser",
    "dante": "dante",
    "joui": "joui",
    "joui jouki": "joui",
    "liz": "liz",
    "liz sena": "liz",
    "thiago": "thiago",
    "thiago fritz": "thiago",
    "rubens": "rubens",
    "rubens naluti": "rubens",
    "milo": "milo",
    "milo foster": "milo",
    "mestre": "mestre",
    "o mestre": "mestre",
    "narrador": "mestre",
    "narradora": "mestre",
    "mestre da ordem": "mestre",
    "dm": "mestre",
    "gm": "mestre",
}


class WindowsAudioPlayer:
    """Reprodutor de áudio nativo para Windows (assíncrono e não-bloqueante).

    Utiliza MCI (Media Control Interface via winmm.dll) com fallback para PowerShell MediaPlayer.
    """

    def __init__(self):
        self._is_windows = os.name == "nt"
        self._active_aliases = set()
        self._lock = threading.Lock()
        self._alias_counter = 0

    def _get_short_path(self, long_path: str) -> str:
        """Converte caminho longo com espaços para 8.3 short path no Windows para segurança do MCI."""
        if not self._is_windows:
            return long_path
        try:
            buffer = ctypes.create_unicode_buffer(700)
            res = ctypes.windll.kernel32.GetShortPathNameW(long_path, buffer, 700)
            if res > 0 and buffer.value:
                return buffer.value
        except Exception as e:
            logger.debug(f"Falha ao obter short path para '{long_path}': {e}")
        return long_path

    def play(self, audio_path: Path, async_play: bool = True) -> bool:
        """Reproduz o arquivo de áudio.

        :param audio_path: Caminho para arquivo de áudio (.mp3 ou .wav).
        :param async_play: Se True, reproduz em thread em segundo plano sem travar o loop principal.
        """
        if not audio_path or not audio_path.exists():
            logger.warning(f"[AudioPlayer] Arquivo de áudio não encontrado: {audio_path}")
            return False

        if async_play:
            thread = threading.Thread(
                target=self._play_sync_internal,
                args=(audio_path,),
                daemon=True,
                name=f"VoicePlay-{audio_path.name}",
            )
            thread.start()
            return True
        else:
            return self._play_sync_internal(audio_path)

    def _play_sync_internal(self, audio_path: Path) -> bool:
        """Execução síncrona interna da reprodução."""
        if not self._is_windows:
            logger.info(f"[AudioPlayer Simulado] Tocando: {audio_path.name}")
            return True

        with self._lock:
            self._alias_counter += 1
            alias = f"mv_voice_{self._alias_counter}_{int(time.time() * 1000) % 100000}"
            self._active_aliases.add(alias)

        file_str = self._get_short_path(str(audio_path.resolve()))
        played = False

        # Tentativa 1: Windows MCI (baixa latência, nativo)
        try:
            winmm = ctypes.windll.winmm
            open_cmd = f'open "{file_str}" type mpegvideo alias {alias}'
            err = winmm.mciSendStringW(open_cmd, None, 0, None)
            if err == 0:
                play_cmd = f"play {alias} wait"
                winmm.mciSendStringW(play_cmd, None, 0, None)
                winmm.mciSendStringW(f"close {alias}", None, 0, None)
                played = True
            else:
                logger.debug(f"MCI retornou código {err}, recorrendo ao fallback de áudio.")
        except Exception as e:
            logger.debug(f"Erro ao reproduzir via MCI: {e}")

        # Tentativa 2: Fallback PowerShell MediaPlayer se MCI falhou
        if not played:
            try:
                ps_script = (
                    f"Add-Type -AssemblyName presentationCore; "
                    f"$player = New-Object System.Windows.Media.MediaPlayer; "
                    f"$player.Open([System.Uri]'{Path(file_str).as_uri()}'); "
                    f"$player.Play(); "
                    f"Start-Sleep -Seconds 1; "
                    f"while ($player.NaturalDuration.HasTimeSpan -and ($player.Position -lt $player.NaturalDuration.TimeSpan)) {{ Start-Sleep -Milliseconds 100 }}; "
                    f"$player.Close();"
                )
                subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=30,
                )
                played = True
            except Exception as e:
                logger.debug(f"Erro no fallback PowerShell: {e}")

        with self._lock:
            self._active_aliases.discard(alias)

        return played

    def stop_all(self):
        """Interrompe todas as reproduções de áudio MCI ativas."""
        if not self._is_windows:
            return
        try:
            winmm = ctypes.windll.winmm
            with self._lock:
                for alias in list(self._active_aliases):
                    winmm.mciSendStringW(f"stop {alias}", None, 0, None)
                    winmm.mciSendStringW(f"close {alias}", None, 0, None)
                self._active_aliases.clear()
        except Exception as e:
            logger.debug(f"Erro ao parar áudios MCI: {e}")


class AudioCacheManager:
    """Gerencia o armazenamento e recuperação em disco de arquivos sintetizados."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = Path(cache_dir or AUDIO_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    def compute_hash(
        self,
        text: str,
        voice_id: str,
        model_id: str,
        settings: Dict[str, Any],
    ) -> str:
        """Gera hash SHA256 exclusivo para o conteúdo da fala e parâmetros de voz."""
        norm_text = re.sub(r"\s+", " ", text.strip().lower())
        payload = {
            "text": norm_text,
            "voice_id": voice_id,
            "model_id": model_id,
            "settings": settings,
        }
        raw_json = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

    def get_cached_path(self, speaker_slug: str, hash_key: str) -> Optional[Path]:
        """Retorna o caminho do arquivo caso já exista em cache."""
        filename = f"{speaker_slug}_{hash_key[:16]}.mp3"
        file_path = self.cache_dir / filename
        if file_path.exists() and file_path.stat().st_size > 0:
            self.hits += 1
            return file_path
        self.misses += 1
        return None

    def save_to_cache(self, speaker_slug: str, hash_key: str, audio_bytes: bytes) -> Path:
        """Salva os bytes de áudio atomicamente no disco."""
        filename = f"{speaker_slug}_{hash_key[:16]}.mp3"
        final_path = self.cache_dir / filename
        temp_path = self.cache_dir / f"{filename}.tmp_{os.getpid()}_{int(time.time()*1000)}"

        try:
            with open(temp_path, "wb") as f:
                f.write(audio_bytes)
            # Substituição atômica no Windows / Unix
            os.replace(temp_path, final_path)
            logger.debug(f"[Cache] Áudio gravado com sucesso: {final_path.name} ({len(audio_bytes)} bytes)")
            return final_path
        except Exception as e:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise e

    def get_stats(self) -> Dict[str, Any]:
        """Estatísticas de uso do cache para economia de quota."""
        total = self.hits + self.misses
        hit_ratio = (self.hits / total * 100) if total > 0 else 0.0
        cached_files = list(self.cache_dir.glob("*.mp3"))
        total_bytes = sum(f.stat().st_size for f in cached_files) if cached_files else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio_percent": round(hit_ratio, 1),
            "cached_files_count": len(cached_files),
            "total_cache_size_kb": round(total_bytes / 1024, 2),
            "cache_dir": str(self.cache_dir.resolve()),
        }


class ElevenLabsVoiceManager:
    """Gerenciador central de vozes para a Mesa Viva de Ordem Paranormal."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_id: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        enabled: bool = True,
    ):
        # 1. Gerenciamento de chave de API
        self.api_key = (
            api_key
            or os.getenv("ELEVENLABS_API_KEY", "")
            or getattr(config, "elevenlabs_api_key", "")
        ).strip()

        self.model_id = (
            model_id
            or os.getenv("ELEVENLABS_MODEL_ID", "")
            or getattr(config, "elevenlabs_model_id", "eleven_multilingual_v2")
        ).strip()

        self.enabled = enabled
        self.cache = AudioCacheManager(cache_dir=cache_dir)
        self.player = WindowsAudioPlayer()
        self.profiles = dict(DEFAULT_VOICE_PROFILES)
        self.api_base_url = "https://api.elevenlabs.io/v1"

        if not self.api_key:
            logger.info(
                "[VoiceManager] ELEVENLABS_API_KEY não detectada. Modo Fallback ativado (logs textuais e áudios em cache preservados)."
            )
        else:
            logger.info(
                f"[VoiceManager] Inicializado com chave ElevenLabs ativa. Modelo: {self.model_id}"
            )

    @property
    def has_valid_api_key(self) -> bool:
        """Verifica se existe chave configurada e não vazia."""
        return bool(self.api_key and len(self.api_key) > 5)

    def resolve_voice_profile(self, speaker_name: str) -> VoiceProfile:
        """Mapeia dinamicamente o nome de qualquer protagonista ou Mestre para seu perfil sonoro."""
        raw = speaker_name.lower().strip()
        # 1. Checa correspondência exata nos perfis
        if raw in self.profiles:
            return self.profiles[raw]

        # 2. Checa tabela de sinônimos/aliases
        if raw in SPEAKER_ALIASES:
            key = SPEAKER_ALIASES[raw]
            if key in self.profiles:
                return self.profiles[key]

        # 3. Busca por substring nos nomes conhecidos
        for key, profile in self.profiles.items():
            if key in raw or profile.display_name.lower() in raw:
                return profile

        # 4. Caso não reconheça, assume "O Mestre" se tiver tom narrativo, ou "Arthur" como fallback padrão
        if any(w in raw for w in ["mestre", "dm", "narrador", "sistema", "outro lado"]):
            return self.profiles["mestre"]

        logger.debug(f"[VoiceManager] Personagem '{speaker_name}' não mapeado. Usando perfil padrão (Arthur).")
        return self.profiles["arthur"]

    def synthesize(
        self,
        text: str,
        speaker_name: str,
        force_refresh: bool = False,
    ) -> Optional[Path]:
        """Sintetiza áudio via ElevenLabs com cache em disco e fallback resiliente.

        :param text: Fala do personagem ou narração do Mestre.
        :param speaker_name: Nome do personagem (ex: "Arthur", "Kaiser", "O Mestre").
        :param force_refresh: Se True, ignora o cache e solicita nova geração na API.
        :return: Path do arquivo de áudio .mp3 gerado ou em cache, ou None caso em fallback.
        """
        if not text or not text.strip():
            return None

        clean_text = text.strip()
        profile = self.resolve_voice_profile(speaker_name)
        settings = profile.to_settings_dict()
        hash_key = self.cache.compute_hash(clean_text, profile.voice_id, self.model_id, settings)

        # 1. Consulta ao Cache em Disco
        if not force_refresh:
            cached_file = self.cache.get_cached_path(profile.speaker_key, hash_key)
            if cached_file:
                logger.info(
                    f"[Cache HIT] Voz de '{profile.display_name}' recuperada do cache: {cached_file.name}"
                )
                return cached_file

        # 2. Fallback caso não haja chave de API configurada
        if not self.has_valid_api_key:
            logger.info(
                f"[Voice Fallback] [Sem API Key] {profile.display_name} ({profile.description}): \"{clean_text}\""
            )
            return None

        # 3. Requisição HTTP direta à API da ElevenLabs
        url = f"{self.api_base_url}/text-to-speech/{profile.voice_id}?output_format=mp3_44100_128"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }
        payload = {
            "text": clean_text,
            "model_id": self.model_id,
            "voice_settings": settings,
        }

        try:
            logger.info(
                f"[ElevenLabs API] Sintetizando voz de {profile.display_name} ({len(clean_text)} caracteres)..."
            )
            response = requests.post(url, json=payload, headers=headers, timeout=18)

            if response.status_code == 200 and response.content:
                saved_path = self.cache.save_to_cache(profile.speaker_key, hash_key, response.content)
                logger.info(
                    f"[ElevenLabs Sucesso] Áudio salvo em: {saved_path.name} | Quota preservada para futuras chamadas!"
                )
                return saved_path
            elif response.status_code == 401:
                logger.warning(
                    f"[ElevenLabs 401] Chave de API inválida ou expirada. Entrando em modo fallback."
                )
                return None
            elif response.status_code == 429:
                logger.warning(
                    f"[ElevenLabs 429] Limite de quota ou taxa excedido na ElevenLabs. Prosseguindo sem áudio."
                )
                return None
            else:
                logger.warning(
                    f"[ElevenLabs HTTP {response.status_code}] Falha ao sintetizar: {response.text[:200]}"
                )
                return None

        except requests.exceptions.RequestException as exc:
            # Fallback resiliente para máquina offline ou falha de conexão
            logger.warning(
                f"[Voice Offline/Erro] Falha de conexão com ElevenLabs ({exc}). Prosseguindo com fallback textual."
            )
            return None
        except Exception as exc:
            logger.error(f"[Voice Erro Inesperado] {exc}")
            return None

    def speak(
        self,
        text: str,
        speaker_name: str,
        async_play: bool = True,
        force_refresh: bool = False,
    ) -> Optional[Path]:
        """Executa a síntese e dispara a reprodução de áudio assíncrona no Windows.

        :param text: Texto da fala ou narração.
        :param speaker_name: Nome do personagem ou Mestre.
        :param async_play: Reprodução não-bloqueante (True por padrão).
        :param force_refresh: Forçar nova requisição à ElevenLabs.
        :return: Path do áudio ou None caso fallback.
        """
        profile = self.resolve_voice_profile(speaker_name)
        
        # Emite no console o aviso roleplay
        print(f"\n[VOZ - {profile.display_name}] \"{text}\"")

        if not self.enabled:
            return None

        audio_path = self.synthesize(text, speaker_name, force_refresh=force_refresh)

        if audio_path and audio_path.exists():
            self.player.play(audio_path, async_play=async_play)

        return audio_path

    def stop_playback(self):
        """Interrompe áudios em andamento."""
        self.player.stop_all()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtém métricas do cache em disco."""
        return self.cache.get_stats()


# Instância global reutilizável
voice_manager = ElevenLabsVoiceManager()
