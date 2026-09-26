"""Script demonstrativo para testar o loop de combate dos agentes LLM com o Battlemat."""

import logging
import sys
import time

from ai_agents.orchestrator import AgenteGameOrchestrator
from ai_agents.config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    print("=" * 70)
    print("   ORDEM PARANORMAL - MESA SINTÉTICA DE AGENTES LLM")
    print(f"   Modelo Configurado: {config.model_name}")
    print(f"   Endpoint LLM: {config.llm_api_base}")
    print(f"   Unreal UDP: {config.unreal_udp_ip}:{config.unreal_udp_port}")
    print("=" * 70 + "\n")

    orchestrator = AgenteGameOrchestrator()

    narrativa_inicial = (
        "As luzes do galpão piscam violentamente. Um cheiro ferroso toma o ar. "
        "Um Zumbi de Sangue emerge das sombras em D5, com as garras pingando plasma!"
    )
    orchestrator.narrar_mestre(narrativa_inicial, async_play=True)
    print()

    # Ordem da Iniciativa: 1 (Arthur), 2 (Kaiser), 3 (Dante)
    iniciativa = [1, 2, 3]

    for round_num in range(1, 2):
        print(f"--- [RODADA {round_num}] ---")
        for token_id in iniciativa:
            agente = orchestrator.agentes[token_id]
            print(f"\n>> Vez de: {agente.nome} ({agente.classe} - {agente.grid}) [SAN: {agente.san_atual}/{agente.san_max}]")

            decisao = orchestrator.executar_turno_agente(
                token_id=token_id, narrativa_mestre=narrativa_inicial
            )

            print(f"   [Pensamento Tático]: {decisao.pensamento}")
            print(f"   [Fala em Voz Alta]: \"{decisao.fala}\"")
            if decisao.movimento:
                print(f"   [Movimento]: {decisao.movimento.descricao or decisao.movimento.destino_grid}")
            print(f"   [Ação Padrão]: Tipo={decisao.acao_padrao.tipo} | Alvo={decisao.acao_padrao.alvo_nome or decisao.acao_padrao.alvo_id}")
            time.sleep(1)

    print("\n" + "=" * 70)
    print(f"   Rodada concluída! Turnos gravados para treino LoRA em:")
    print(f"   {config.dataset_output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
