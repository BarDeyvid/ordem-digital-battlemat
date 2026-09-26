"""Testes automatizados para o Mestre de Jogo IA (OrdoGameMaster) e integração com o Orquestrador."""

import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from ai_agents.schemas import AgenteFicha, AcaoPadrao, MovimentoAcao, AmeacaFicha
from ai_agents.game_master import (
    OrdoGameMaster,
    rolar_dados,
    rolar_d20,
    rolar_expressao_dano,
)
from ai_agents.orchestrator import AgenteGameOrchestrator



@pytest.fixture
def mock_bridge():
    """Mock da ponte com a Unreal Engine para evitar sockets reais durante testes."""
    bridge = MagicMock()
    bridge.grid_to_norm_coords.return_value = (0.5, 0.5)
    return bridge


@pytest.fixture
def game_master(mock_bridge):
    """Instância do Game Master com mock do bridge."""
    return OrdoGameMaster(bridge=mock_bridge)


@pytest.fixture
def agentes_teste():
    """Trio de investigadores canônicos para testes."""
    return {
        1: AgenteFicha(
            token_id=1,
            nome="Arthur Cervero",
            classe="Combatente",
            trilha="Aniquilador",
            nex=20,
            pv_atual=28,
            pv_max=32,
            san_atual=14,
            san_max=20,
            pe_atual=6,
            pe_max=10,
            defesa=17,
            grid="C3",
            pericias=["Pontaria", "Luta", "Fortitude"],
            armas=["Espingarda", "Machado"],
        ),
        2: AgenteFicha(
            token_id=2,
            nome="Kaiser",
            classe="Especialista",
            trilha="Infiltrador",
            nex=20,
            pv_atual=20,
            pv_max=22,
            san_atual=18,
            san_max=24,
            pe_atual=12,
            pe_max=16,
            defesa=15,
            grid="A2",
            pericias=["Furtividade", "Pontaria", "Crime"],
            armas=["Revólver", "Submetralhadora"],
        ),
        3: AgenteFicha(
            token_id=3,
            nome="Dante",
            classe="Ocultista",
            trilha="Graduado",
            nex=20,
            pv_atual=14,
            pv_max=16,
            san_atual=9,
            san_max=22,
            pe_atual=15,
            pe_max=20,
            defesa=13,
            grid="B1",
            pericias=["Ocultismo", "Vontade"],
            armas=["Faca de Ritual"],
            rituais=[
                {"nome": "Decadência", "elemento": "Morte", "custo_pe": 1},
                {"nome": "Cicatrizante", "elemento": "Sangue", "custo_pe": 1},
            ],
        ),
    }


# ============================================================================
# 1. TESTES DE ROLAGEM DE DADOS E EXPRESSÕES CANÔNICAS
# ============================================================================

def test_rolagem_dados():
    total, rolagens = rolar_dados(3, 6)
    assert 3 <= total <= 18
    assert len(rolagens) == 3
    assert all(1 <= r <= 6 for r in rolagens)


def test_rolagem_d20():
    total, d20_puro = rolar_d20(bonus=5)
    assert 1 <= d20_puro <= 20
    assert total == d20_puro + 5


def test_rolagem_expressao_dano_fisico():
    fis, mental, detalhe = rolar_expressao_dano("1d10+3 Perfuração")
    assert 4 <= fis <= 13
    assert mental == 0
    assert "1d10" in detalhe


def test_rolagem_expressao_dano_misto():
    fis, mental, detalhe = rolar_expressao_dano("1d6 Conhecimento + 1d4 Sanidade")
    assert 1 <= fis <= 6
    assert 1 <= mental <= 4
    assert "Sanidade" in detalhe


def test_rolagem_expressao_multi_dados():
    fis, mental, detalhe = rolar_expressao_dano("2d8+5 Impacto")
    assert 7 <= fis <= 21
    assert mental == 0


# ============================================================================
# 2. TESTES DE PRESENÇA PERTURBADORA
# ============================================================================

def test_presenca_perturbadora_disparo(game_master, agentes_teste):
    ameaca = game_master.criar_ameaca("Zumbi de Sangue", token_id=11, grid="D5")
    investigadores = list(agentes_teste.values())

    san_antes = {ag.token_id: ag.san_atual for ag in investigadores}
    resultado = game_master.disparar_presenca_perturbadora(ameaca, investigadores)

    assert resultado["disparado"] is True
    assert resultado["dt"] == 15
    assert len(resultado["resultados"]) == 3

    # Todos que passaram ou falharam devem ter sofrido dano ou ficado imunes
    for r in resultado["resultados"]:
        ag_id = r["agente_id"]
        ag = agentes_teste[ag_id]
        if r["passou"]:
            assert ag.imune_presenca is True
        assert ag.san_atual <= san_antes[ag_id]


def test_presenca_perturbadora_imunidade_subsequente(game_master, agentes_teste):
    ameaca = game_master.criar_ameaca("Zumbi de Sangue", token_id=11, grid="D5")
    investigadores = list(agentes_teste.values())
    investigadores[0].imune_presenca = True
    san_esperada = investigadores[0].san_atual

    res = game_master.disparar_presenca_perturbadora(ameaca, [investigadores[0]])
    assert res["resultados"][0]["resultado"] == "imune"
    assert investigadores[0].san_atual == san_esperada


# ============================================================================
# 3. TESTES DE TÁTICA E MOVIMENTAÇÃO NO GRID
# ============================================================================

def test_calculo_distancia_grid():
    assert OrdoGameMaster.calcular_distancia_grid("C3", "C3") == 0
    assert OrdoGameMaster.calcular_distancia_grid("C3", "D4") == 1  # diagonal adjacente
    assert OrdoGameMaster.calcular_distancia_grid("A1", "A3") == 2
    assert OrdoGameMaster.calcular_distancia_grid("A1", "D4") == 3


def test_posicoes_adjacentes():
    adj = OrdoGameMaster.calcular_posicoes_adjacentes("B2")
    assert "A1" in adj
    assert "B1" in adj
    assert "C1" in adj
    assert "A2" in adj
    assert "C2" in adj
    assert "A3" in adj
    assert "B3" in adj
    assert "C3" in adj
    assert len(adj) == 8


def test_escolha_alvo_sangue(game_master, agentes_teste):
    # Criatura de Sangue foca no mais próximo ou menos PV
    zumbi = game_master.criar_ameaca("Zumbi de Sangue", token_id=11, grid="C4")
    # Arthur está em C3 (dist 1), Dante em B1 (dist 3), Kaiser em A2 (dist 2)
    alvo = game_master.escolher_alvo(zumbi, list(agentes_teste.values()))
    assert alvo.token_id == 1  # Arthur é o mais próximo


def test_escolha_alvo_conhecimento(game_master, agentes_teste):
    # Criatura de Conhecimento foca no alvo com menor Sanidade
    existido = game_master.criar_ameaca("O Existido", token_id=12, grid="E5")
    # Dante tem menor Sanidade (9)
    alvo = game_master.escolher_alvo(existido, list(agentes_teste.values()))
    assert alvo.token_id == 3
    assert alvo.nome == "Dante"


def test_decidir_movimento_aproximacao(game_master, agentes_teste):
    zumbi = game_master.criar_ameaca("Zumbi de Sangue", token_id=11, grid="F6")
    arthur = agentes_teste[1]  # em C3
    novo_grid, nx, ny = game_master.decidir_movimento(zumbi, arthur, max_passos=3)
    # Zumbi deve ter se aproximado de C3
    dist_antes = game_master.calcular_distancia_grid("F6", "C3")
    dist_depois = game_master.calcular_distancia_grid(novo_grid, "C3")
    assert dist_depois < dist_antes


# ============================================================================
# 4. TESTES DE HABILIDADES ESPECIAIS CANÔNICAS
# ============================================================================

def test_habilidade_sede_de_sangue(game_master, agentes_teste):
    zumbi = game_master.criar_ameaca("Zumbi de Sangue", token_id=11, grid="C4")
    zumbi.pv_atual = 20  # Danificado
    # Alvo com defesa baixa para forçar acerto
    agentes_teste[1].defesa = 0

    res = game_master.executar_turno_ameaca(11, agentes_teste)
    assert res.acertou is True
    assert zumbi.pv_atual == 25  # Curou 5 PV via Sede de Sangue
    assert any("Sede de Sangue" in h for h in res.habilidades_ativadas)


def test_habilidade_agarrar_aberracao(game_master, agentes_teste):
    aberracao = game_master.criar_ameaca("Aberração de Carne", token_id=12, grid="C4")
    agentes_teste[1].defesa = 0  # Garante acerto

    res = game_master.executar_turno_ameaca(12, agentes_teste)
    assert res.acertou is True
    assert "Agarrado" in agentes_teste[1].condicoes
    assert any("Agarrar Aprimorado" in h for h in res.habilidades_ativadas)


def test_habilidade_lodo_temporal(game_master, agentes_teste):
    esqueleto = game_master.criar_ameaca("Esqueleto de Lodo", token_id=13, grid="C4")
    agentes_teste[1].defesa = 0

    res = game_master.executar_turno_ameaca(13, agentes_teste)
    assert res.acertou is True
    assert "Lento" in agentes_teste[1].condicoes
    assert any("Lodo Temporal" in h for h in res.habilidades_ativadas)


def test_habilidade_teletransporte_caotico(game_master, agentes_teste):
    anomalia = game_master.criar_ameaca("Anomalia Elétrica", token_id=14, grid="D4")
    grid_inicial = anomalia.grid

    res = game_master.executar_turno_ameaca(14, agentes_teste)
    # A anomalia deve ter ativado teletransporte caótico e trocado de grid
    assert any("Teletransporte Caótico" in h for h in res.habilidades_ativadas)
    assert anomalia.grid != grid_inicial


def test_habilidade_matilha_cao_do_sangue(game_master, agentes_teste):
    cao1 = game_master.criar_ameaca("Cão do Sangue", token_id=15, grid="C4")
    cao2 = game_master.criar_ameaca("Cão do Sangue", token_id=16, grid="C2")
    # Arthur está em C3, ambos os cães estão adjacentes a Arthur
    res = game_master.executar_turno_ameaca(15, agentes_teste, outras_ameacas=[cao1, cao2])
    assert any("Matilha" in h for h in res.habilidades_ativadas)


def test_habilidade_toque_do_esquecimento(game_master, agentes_teste):
    existido = game_master.criar_ameaca("O Existido", token_id=17, grid="B2")
    dante = agentes_teste[3]
    dante.defesa = 0  # Força acerto
    san_antes = dante.san_atual

    res = game_master.executar_turno_ameaca(17, agentes_teste)
    assert res.acertou is True
    assert res.dano_mental > 0
    assert dante.san_atual < san_antes
    assert any("Toque do Esquecimento" in h for h in res.habilidades_ativadas)


# ============================================================================
# 5. TESTES DE NARRATIVA DE HORROR E REVIRAVOLTAS
# ============================================================================

def test_narrar_abertura_cena(game_master):
    narracao = game_master.narrar_abertura_cena("Galpão Portuário", "Zumbi de Sangue")
    assert "Zumbi de Sangue" in narracao
    assert len(narracao) > 30


def test_narrar_reviravolta(game_master):
    rev = game_master.narrar_reviravolta(rodada=2)
    assert "nome" in rev
    assert "narrativa" in rev
    assert "[REVIRAVOLTA - RODADA 2]" in rev["narrativa"]


# ============================================================================
# 6. TESTES DE INTEGRAÇÃO COM O ORQUESTRADOR
# ============================================================================

def test_orchestrator_iniciar_combate(mock_bridge):
    orchestrator = AgenteGameOrchestrator(player_token_id=1)
    orchestrator.bridge = mock_bridge
    orchestrator.game_master.bridge = mock_bridge

    resultado = orchestrator.iniciar_combate(
        nome_ameaca="Zumbi de Sangue",
        grid_ameaca="D5",
        ambiente="Mansão Leone",
        narrar_voz=False,
    )

    assert "narrativa_abertura" in resultado
    assert "presenca_perturbadora" in resultado
    assert resultado["presenca_perturbadora"]["disparado"] is True
    assert len(orchestrator.game_master.ameacas_ativas) >= 1


def test_orchestrator_turno_player_ataque(mock_bridge):
    orchestrator = AgenteGameOrchestrator(player_token_id=1)
    orchestrator.bridge = mock_bridge
    orchestrator.game_master.bridge = mock_bridge

    # Configura zumbi com defesa baixa para garantir acerto
    ameaca = orchestrator.game_master.criar_ameaca("Zumbi de Sangue", token_id=11, grid="C4")
    ameaca.defesa = 0
    pv_inicial = ameaca.pv_atual

    acao = AcaoPadrao(tipo="ataque", arma="Espingarda", alvo_id=11)
    mov = MovimentoAcao(destino_grid="C3")

    res = orchestrator.executar_turno_player(token_id=1, acao=acao, movimento=mov)

    assert res["movimento"]["destino"] == "C3"
    assert res["acao"]["acertou"] is True
    assert ameaca.pv_atual < pv_inicial


def test_orchestrator_turno_player_ritual(mock_bridge):
    orchestrator = AgenteGameOrchestrator(player_token_id=3)  # Dante
    orchestrator.bridge = mock_bridge
    orchestrator.game_master.bridge = mock_bridge

    dante = orchestrator.agentes[3]
    pe_inicial = dante.pe_atual

    acao = AcaoPadrao(tipo="ritual", ritual="Decadência", elemento="Morte", custo_pe=1)
    res = orchestrator.executar_turno_player(token_id=3, acao=acao)

    assert res["acao"]["tipo"] == "ritual"
    assert dante.pe_atual == pe_inicial - 1


def test_orchestrator_rodada_completa(mock_bridge):
    orchestrator = AgenteGameOrchestrator(player_token_id=1)
    orchestrator.bridge = mock_bridge
    orchestrator.game_master.bridge = mock_bridge

    # Limita o número de agentes no teste para execução rápida
    orchestrator.agentes = {
        1: orchestrator.agentes[1],
        2: orchestrator.agentes[2],
    }

    acao_player = AcaoPadrao(tipo="ataque", arma="Espingarda")
    mov_player = MovimentoAcao(destino_grid="C3")

    relatorio = orchestrator.executar_rodada_completa(
        acao_player=acao_player,
        mov_player=mov_player,
        narrativa_mestre="O combate começa!",
    )

    assert relatorio["rodada"] == 1
    assert relatorio["player"] is not None
    assert len(relatorio["aliados"]) == 1  # Kaiser
    assert len(relatorio["ameacas"]) >= 1  # Zumbi
