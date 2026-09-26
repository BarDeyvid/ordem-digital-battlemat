"""Demonstração interativa e autônoma do Mestre de Jogo IA (Ordo Game Master) de Ordem Paranormal.

Demonstra:
1. Narração cinematográfica de abertura de cena com tom de horror cósmico.
2. Disparo de Presença Perturbadora (testes de Vontade vs Sanidade).
3. Turno de Player Solo (controlado pelo usuário/script).
4. Turno tático de Agentes IA Aliados (Kaiser e Dante).
5. Turno da Criatura/Ameaça controlado pela IA do Mestre (movimentação no grid, ataque e habilidades especiais).
6. Reviravoltas de horror cósmico no meio do combate.
7. Sincronização via Battlemat Bridge e Unreal Engine UDP.
"""

import logging
import sys
import time
from pathlib import Path

# Garante codificação UTF-8 no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Garante importação do pacote ai_agents mesmo se executado diretamente
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from ai_agents.orchestrator import AgenteGameOrchestrator
from ai_agents.schemas import AcaoPadrao, MovimentoAcao
from ai_agents.config import config


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("demo_game_master")



def exibir_status_equipe(orchestrator: AgenteGameOrchestrator):
    print("\n" + "-" * 75)
    print("   STATUS DOS INVESTIGADORES NO BATTLEMAT:")
    for token_id, a in orchestrator.agentes.items():
        is_player = " [VOCÊ - PLAYER SOLO]" if token_id == orchestrator.player_token_id else " [IA ALIADO]"
        conds = f" | Condições: {', '.join(a.condicoes)}" if a.condicoes else ""
        print(
            f"   • {a.nome:<16} ({a.classe:<12} Grid: {a.grid}) "
            f"PV: {a.pv_atual:>2}/{a.pv_max:<2} | SAN: {a.san_atual:>2}/{a.san_max:<2} | PE: {a.pe_atual:>2}/{a.pe_max:<2}"
            f"{is_player}{conds}"
        )
    print("\n   AMEAÇAS EM COMBATE:")
    for m in orchestrator.game_master.ameacas_ativas.values():
        status = "VIVO" if m.pv_atual > 0 else "NEUTRALIZADO"
        print(f"   • [ID {m.token_id}] {m.nome} ({m.elemento} VD {m.vd}) em [{m.grid}] - PV: {m.pv_atual}/{m.pv_max} [{status}]")
    print("-" * 75 + "\n")


def main():
    print("\n" + "=" * 75)
    print("   ORDO REALITAS - MESTRE DE JOGO IA AUTÔNOMO (ORDO GAME MASTER)")
    print(f"   Battlemat Bridge UDP: {config.unreal_udp_ip}:{config.unreal_udp_port}")
    print(f"   Modelo IA: {config.model_name}")
    print("=" * 75 + "\n")

    # 1. Inicializa o Orquestrador configurando o Token 1 (Arthur Cervero) como Player Solo
    orchestrator = AgenteGameOrchestrator(player_token_id=1)

    # Deixamos apenas Arthur (Player), Kaiser (Especialista) e Dante (Ocultista) para dinamismo
    orchestrator.agentes = {
        1: orchestrator.agentes[1],
        2: orchestrator.agentes[2],
        3: orchestrator.agentes[3],
    }

    # 2. Inicia o Combate: O Mestre IA narra a abertura e dispara Presença Perturbadora
    print(">>> FASE 1: O MESTRE DA ORDEM ABRE A CENA <<<\n")
    ambiente = "Galpão Portuário da Leone"
    nome_ameaca = "Zumbi de Sangue"

    combate_inicio = orchestrator.iniciar_combate(
        nome_ameaca=nome_ameaca,
        grid_ameaca="D5",
        ambiente=ambiente,
        narrar_voz=False,
    )

    print(f"[MESTRE DA ORDEM]:\n\"{combate_inicio['narrativa_abertura']}\"\n")
    time.sleep(1)

    print(">>> FASE 2: IMPACTO DA PRESENÇA PERTURBADORA <<<\n")
    presenca = combate_inicio["presenca_perturbadora"]
    print(f"A presença aterradora de {nome_ameaca} (DT {presenca['dt']}) exige teste de Sanidade:")
    for r in presenca["resultados"]:
        status_sym = "[RESISTIU]" if r.get("passou") else "[FALHOU]"
        print(f"   {status_sym} {r['agente_nome']}: Rolou {r['rolagem']} | Dano Mental: {r['dano_sanidade']} SAN -> Sanidade Atual: {r['san_atual']}")

    
    exibir_status_equipe(orchestrator)
    time.sleep(1)

    # 3. Rodada 1: O Jogador Solo age, seguido pelos companheiros IA e depois a criatura
    print("=" * 75)
    print("   --- INICIANDO RODADA TÁTICA 1 ---")
    print("=" * 75)

    # Ação do Jogador Solo (Arthur): move para C4 e ataca com Espingarda
    acao_arthur = AcaoPadrao(
        tipo="ataque",
        arma="Espingarda",
        alvo_id=11,
    )
    mov_arthur = MovimentoAcao(
        destino_grid="C4",
        descricao="Avanço cautelosamente até a cobertura em C4 e miro a Espingarda.",
    )

    print("\n>> SEU TURNO (Arthur Cervero - Combatente):")
    print(f"   [Movimento Escolhido]: {mov_arthur.descricao} (Grid -> {mov_arthur.destino_grid})")
    print(f"   [Ação Escolhida]: Disparo de {acao_arthur.arma} contra {nome_ameaca}")

    relatorio_r1 = orchestrator.executar_rodada_completa(
        acao_player=acao_arthur,
        mov_player=mov_arthur,
        narrativa_mestre="O zumbi rosna furiosamente em D5, expelindo vapor fétido.",
    )

    # Exibe resultado da ação do jogador
    print(f"\n   [Resultado do seu ataque]: {relatorio_r1['player']['relato']}")

    # Exibe ações dos aliados IA
    print("\n>> TURNO DOS COMPANHEIROS IA:")
    for al in relatorio_r1["aliados"]:
        dec = al["decisao"]
        print(f"   • {al['nome']} ({dec.acao_padrao.tipo.upper()}):")
        print(f"     [Pensamento]: {dec.pensamento}")
        print(f"     [Fala]: \"{dec.fala}\"")
        if dec.movimento and dec.movimento.destino_grid:
            print(f"     [Movimento]: para {dec.movimento.destino_grid}")

    # Exibe ação da ameaça controlada pelo Game Master
    print(f"\n>> TURNO DO MESTRE IA ({nome_ameaca}):")
    for am in relatorio_r1["ameacas"]:
        print(f"   • {am.narrativa}")

    exibir_status_equipe(orchestrator)
    time.sleep(1)

    # 4. Rodada 2: O Mestre introduz uma Reviravolta de Horror Cósmico!
    print("=" * 75)
    print("   --- INICIANDO RODADA TÁTICA 2 (REVIRAVOLTA PARANORMAL) ---")
    print("=" * 75)

    # Jogador Solo desfere golpe de Machado
    acao_arthur_r2 = AcaoPadrao(
        tipo="ataque",
        arma="Machado",
        alvo_id=11,
    )
    mov_arthur_r2 = MovimentoAcao(
        destino_grid="D4",
        descricao="Fecho a distância entrando em alcance corpo a corpo!",
    )

    print("\n>> SEU TURNO (Arthur Cervero):")
    print(f"   [Movimento]: Avança para {mov_arthur_r2.destino_grid}")
    print(f"   [Ação]: Golpe brutal com {acao_arthur_r2.arma}")

    relatorio_r2 = orchestrator.executar_rodada_completa(
        acao_player=acao_arthur_r2,
        mov_player=mov_arthur_r2,
        narrativa_mestre="O chão parece pulsar como carne viva sob as botas dos agentes!",
    )

    print(f"\n   [Resultado do seu ataque]: {relatorio_r2['player']['relato']}")

    print("\n>> TURNO DOS COMPANHEIROS IA:")
    for al in relatorio_r2["aliados"]:
        dec = al["decisao"]
        print(f"   • {al['nome']} ({dec.acao_padrao.tipo.upper()}): \"{dec.fala}\"")

    print(f"\n>> TURNO DO MESTRE IA ({nome_ameaca}):")
    for am in relatorio_r2["ameacas"]:
        print(f"   • {am.narrativa}")

    # Reviravolta Cósmica da Rodada 2
    if relatorio_r2.get("reviravolta"):
        print("\n" + "!" * 75)
        print(f"   {relatorio_r2['reviravolta']['narrativa']}")
        print("!" * 75)

    exibir_status_equipe(orchestrator)

    print("=" * 75)
    print("   DEMONSTRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("   O Mestre IA controlou perfeitamente narrativa, ameaças, grid e regras canônicas.")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
