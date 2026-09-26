"""Gerador em lote de dados de treino para o LoRA (Unsloth).

Executa dezenas de rodadas em cenários temáticos de Ordem Paranormal com o Qwen.
"""

import argparse
import logging
import sys
import time
from typing import Dict, Any

from ai_agents.config import config
from ai_agents.llm_client import LocalLLMClient
from ai_agents.prompt_builder import build_system_prompt, build_turn_prompt
from ai_agents.session_logger import SessionDatasetRecorder
from ai_agents.scenario_generator import gerar_cenario_aleatorio

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("batch_generator")


def run_batch_generation(total_turns: int = 100):
    print("=" * 75)
    print("   ORDEM PARANORMAL - GERADOR DE DATASET EM LOTE PARA LoRA")
    print(f"   Meta: {total_turns} turnos táticos de combate")
    print(f"   Modelo: {config.model_name}")
    print(f"   Destino: {config.dataset_output_path}")
    print("=" * 75 + "\n")

    llm_client = LocalLLMClient()
    recorder = SessionDatasetRecorder()

    turns_completed = 0
    t_start = time.time()

    encounter_id = 0

    while turns_completed < total_turns:
        encounter_id += 1
        cenario = gerar_cenario_aleatorio()
        agentes = cenario["agentes"]
        ameacas = cenario["ameacas"]
        narrativa = cenario["narrativa"]
        ambiente = cenario["ambiente"]
        perfil = cenario["perfil_status"]

        print(f"\n[{encounter_id}] Cenário: {ambiente} (Condição: {perfil.upper()})")
        print(f"     Ameaça: {ameacas[0]['name']} [{ameacas[0]['elemento']}] em {ameacas[0]['grid']}")

        # Executa o turno de cada um dos protagonistas sorteados
        for token_id, agente in list(agentes.items()):
            if turns_completed >= total_turns:
                break
            system_prompt = build_system_prompt(agente)
            aliados_list = [
                {"id": a.token_id, "name": a.nome, "classe": a.classe, "grid": a.grid}
                for a in agentes.values()
            ]
            user_prompt = build_turn_prompt(
                agente=agente,
                ameacas=ameacas,
                aliados=aliados_list,
                narrativa_mestre=narrativa,
            )

            try:
                t0 = time.time()
                decisao = llm_client.request_turn_decision(system_prompt, user_prompt)
                dt = round(time.time() - t0, 2)

                # Grava no dataset Unsloth
                recorder.record_turn(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    assistant_decision=decisao.model_dump(),
                    metadata={
                        "token_id": token_id,
                        "agente": agente.nome,
                        "classe": agente.classe,
                        "ambiente": ambiente,
                        "elemento_ameaca": ameacas[0]["elemento"],
                        "perfil_status": perfil,
                    },
                )

                turns_completed += 1
                acao_txt = f"{decisao.acao_padrao.tipo} ({decisao.acao_padrao.arma or decisao.acao_padrao.ritual or 'ação'})"
                print(
                    f"     -> Turno [{turns_completed:03d}/{total_turns}]: {agente.nome} ({agente.classe}) "
                    f"fez '{acao_txt}' [{dt}s]"
                )

            except Exception as e:
                logger.error(f"Erro no turno de {agente.nome}: {e}")
                time.sleep(1)

    total_time = round(time.time() - t_start, 1)
    print("\n" + "=" * 75)
    print(f"   [SUCESSO] {turns_completed} turnos gerados e registrados em {total_time}s!")
    print(f"   Dataset pronto para treino LoRA em: {config.dataset_output_path}")
    print("=" * 75)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerador de Dataset em Lote")
    parser.add_argument("--turns", type=int, default=100, help="Quantidade total de turnos a gerar (padrao: 100)")
    args = parser.parse_args()

    run_batch_generation(args.turns)
