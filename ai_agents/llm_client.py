"""Cliente de conexão com o LLM local (Ollama, vLLM, llama.cpp, LM Studio, K2-Horizon local)."""

import json
import logging
import re
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

from ai_agents.config import config
from ai_agents.schemas import TurnoDecisao

logger = logging.getLogger("ai_agents.llm_client")


class LocalLLMClient:
    """Cliente universal OpenAI-compatible para inferência local com Structured Output."""

    def __init__(self, api_base: Optional[str] = None, model: Optional[str] = None):
        self.api_base = (api_base or config.llm_api_base).rstrip("/")
        self.model = model or config.model_name
        self.chat_endpoint = f"{self.api_base}/chat/completions"

    def _extract_json_block(self, text: str) -> Dict[str, Any]:
        """Extrai bloco JSON limpo mesmo se o modelo cuspir tags markdown ```json."""
        text = text.strip()
        # Se contiver bloco de código markdown
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))

        # Se for JSON puro iniciando com {
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start : end + 1])

        return json.loads(text)

    def request_turn_decision(
        self, system_prompt: str, user_prompt: str
    ) -> TurnoDecisao:
        """Envia o estado da rodada para o LLM e recebe a decisão validada no schema Pydantic."""
        
        # Schema JSON estrito para o modelo seguir
        json_schema = TurnoDecisao.model_json_schema()

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "response_format": {"type": "json_object"},
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.chat_endpoint,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.llm_api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                resp_json = json.loads(response.read().decode("utf-8"))
                raw_content = resp_json["choices"][0]["message"]["content"]
                parsed_json = self._extract_json_block(raw_content)
                return TurnoDecisao.from_dict_flexible(parsed_json)

        except urllib.error.URLError as e:
            logger.warning(
                f"[LLM Conexao] Nao foi possivel conectar ao servidor LLM em {self.chat_endpoint}: {e}."
                f" Usando decisao de fallback (Modo Simulacao)."
            )
            # Retorna uma decisão de fallback simulada caso o LLM ainda não esteja ligado
            return TurnoDecisao(
                pensamento="[Fallback Offline] Preciso agir rápido para proteger o time.",
                fala="Cobram cobertura, vou atacar essa criatura!",
                movimento={"destino_grid": "C3", "descricao": "Recuo para C3"},
                acao_padrao={
                    "tipo": "ataque",
                    "arma": "Revólver",
                    "alvo_id": 11,
                    "alvo_nome": "Zumbi de Sangue",
                },
            )
        except Exception as e:
            logger.error(f"[LLM Erro] Falha ao processar resposta do modelo: {e}")
            raise
