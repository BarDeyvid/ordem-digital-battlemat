"""Gravador automático de sessões de jogo formatado para Unsloth / LoRA Fine-Tuning."""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from ai_agents.config import config

logger = logging.getLogger("ai_agents.session_logger")


class SessionDatasetRecorder:
    """Registra interações de turnos diretamente no formato Instruction/Chat do Unsloth."""

    def __init__(self, output_path: Path = None):
        self.output_path = output_path or config.dataset_output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def record_turn(
        self,
        system_prompt: str,
        user_prompt: str,
        assistant_decision: Dict[str, Any],
        metadata: Dict[str, Any] = None,
    ):
        """Salva um exemplo no dataset JSONL."""
        sample = {
            "conversations": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": json.dumps(assistant_decision, ensure_ascii=False)},
            ],
            "metadata": metadata or {},
        }

        try:
            with open(self.output_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
            logger.info(f"[Dataset LoRA] Turno registrado com sucesso em {self.output_path.name}")
        except Exception as e:
            logger.error(f"[Dataset LoRA Erro] Falha ao salvar turno para fine-tuning: {e}")
