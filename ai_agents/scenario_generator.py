"""Gerador procedural canônico de cenários táticos baseado no Livro Oficial v1.3."""

import json
import random
from pathlib import Path
from typing import Dict, List, Any
from ai_agents.schemas import AgenteFicha

BASE_DIR = Path(__file__).resolve().parent
COMPENDIUM_DIR = BASE_DIR / "compendium"

# Carrega compêndios oficiais
THREATS_FILE = COMPENDIUM_DIR / "compendium_threats.json"
RITUALS_FILE = COMPENDIUM_DIR / "compendium_rituals.json"

with open(THREATS_FILE, "r", encoding="utf-8") as f:
    CRIATURAS_CATALOGO = json.load(f)

with open(RITUALS_FILE, "r", encoding="utf-8") as f:
    RITUAIS_CATALOGO = json.load(f)

AMBIENTES = [
    {
        "nome": "Galpão Portuário da Leone",
        "narrativa": "Contêineres empilhados criam um labirinto escuro. O cheiro de maresia e óleo se mistura a poças de sangue espesso.",
        "terreno": "Cobertura pesada em caixas metálicas (D4, E4). Visibilidade regular.",
    },
    {
        "nome": "Sanatório São Cristóvão (Ala Fechada)",
        "narrativa": "Paredes mofadas e macas enferrujadas bloqueiam o corredor estreito. O eco de sussurros distorcidos reverbera na Membrana.",
        "terreno": "Corredor estreito (2 quadrados). Cobertura leve em portas quebradas.",
    },
    {
        "nome": "Porão da Mansão Leone",
        "narrativa": "Velas derretidas e símbolos de Morte pintados em lodo preto no chão. O ar parece mais frio e os relógios pararam.",
        "terreno": "Lodo no chão (terreno difícil: 2x movimento). Colunas de mármore em B2 e F2.",
    },
    {
        "nome": "Laboratório Subterrâneo de Energia",
        "narrativa": "Monitores CRT explodem faíscas roxas e fios desencapados serpenteiam pelo chão encharcado de água eletrificada.",
        "terreno": "Painéis elétricos com risco de choque em C3. Iluminação estroboscópica.",
    },
    {
        "nome": "Esgoto Subterrâneo da Cidade",
        "narrativa": "Água fétida até as canelas. Tubulações gotejam lodo negro e a escuridão é quase absoluta.",
        "terreno": "Água funda (terreno difícil). Passarelas estreitas elevadas nas bordas.",
    },
    {
        "nome": "Floresta das Sombras sob Tempestade",
        "narrativa": "Chuva torrencial e neblina cinzenta. Árvores retorcidas parecem braços esqueléticos tentando agarrar quem passa.",
        "terreno": "Troncos caídos oferecem cobertura. Chuva forte reduz visibilidade à distância.",
    },
]

# Roster Completo de Protagonistas Canônicos
ROSTER_PROTAGONISTAS = [
    {
        "token_id": 1,
        "nome": "Arthur Cervero",
        "classe": "Combatente",
        "trilha": "Aniquilador",
        "nex": 25,
        "pv_base": 36,
        "san_base": 22,
        "pe_base": 12,
        "defesa": 17,
        "armas": ["Espingarda", "Machado"],
        "habilidades": ["Ataque Especial (+5 no ataque ou +1d no dano)", "A Fila Anda (Margem ameaça 19)"],
        "pericias": ["Pontaria", "Luta", "Fortitude"],
        "personalidade": "Protetor do grupo, agressivo na vanguarda, não hesita em atirar primeiro.",
        "rituais": [],
    },
    {
        "token_id": 2,
        "nome": "Kaiser",
        "classe": "Especialista",
        "trilha": "Infiltrador",
        "nex": 25,
        "pv_base": 24,
        "san_base": 26,
        "pe_base": 18,
        "defesa": 16,
        "armas": ["Submetralhadora", "Revólver"],
        "habilidades": ["Ataque Furtivo (+1d6 se alvo flanqueado)", "Perito (+1d6 em Perícias)"],
        "pericias": ["Furtividade", "Pontaria", "Crime", "Tecnologia"],
        "personalidade": "Metódico, tático, prioriza atacar à distância sob cobertura pesada.",
        "rituais": [],
    },
    {
        "token_id": 3,
        "nome": "Dante",
        "classe": "Ocultista",
        "trilha": "Graduado",
        "nex": 25,
        "pv_base": 18,
        "san_base": 28,
        "pe_base": 24,
        "defesa": 13,
        "armas": ["Faca de Ritual"],
        "habilidades": ["Escolhido pelo Outro Lado", "Saber Ampliado (DT Rituais 16)"],
        "pericias": ["Ocultismo", "Vontade", "Religião"],
        "personalidade": "Místico, calmo por fora mas sente o peso terrível da Membrana.",
        "rituais": [
            {"nome": "Decadência", "elemento": "Morte", "custo_pe": 1},
            {"nome": "Cicatrizante", "elemento": "Sangue", "custo_pe": 1},
            {"nome": "Tela de Ruído", "elemento": "Energia", "custo_pe": 3},
            {"nome": "Eletrocussão", "elemento": "Energia", "custo_pe": 1},
        ],
    },
    {
        "token_id": 4,
        "nome": "Joui Jouki",
        "classe": "Combatente",
        "trilha": "Guerreiro",
        "nex": 25,
        "pv_base": 38,
        "san_base": 24,
        "pe_base": 12,
        "defesa": 18,
        "armas": ["Katana", "Shuriken"],
        "habilidades": ["Técnica Marcial (Manobra Derrubar)", "Revidar (Contra-ataque no Bloqueio)"],
        "pericias": ["Luta", "Acrobacia", "Atletismo", "Reflexos"],
        "personalidade": "Honrado, atlético, avança velozmente para travar inimigos no combate corpo a corpo.",
        "rituais": [],
    },
    {
        "token_id": 5,
        "nome": "Elizabeth Webber",
        "classe": "Especialista",
        "trilha": "Médica de Campo",
        "nex": 25,
        "pv_base": 24,
        "san_base": 26,
        "pe_base": 18,
        "defesa": 15,
        "armas": ["Pistola", "Kit Médico"],
        "habilidades": ["Paramédico (Cura 2d10+2 PV em aliados)", "Primeiros Socorros Rápido"],
        "pericias": ["Medicina", "Investigação", "Ciências", "Vontade"],
        "personalidade": "Científica, atenta à saúde física e mental dos aliados, age sob pressão.",
        "rituais": [],
    },
    {
        "token_id": 6,
        "nome": "Thiago Fritz",
        "classe": "Combatente",
        "trilha": "Comandante de Campo",
        "nex": 25,
        "pv_base": 36,
        "san_base": 22,
        "pe_base": 14,
        "defesa": 19,
        "armas": ["Revólver", "Escudo Tático"],
        "habilidades": ["Inspirar Confiança (+2 acerto aliados)", "Estrategista (Reposicionar Aliado)"],
        "pericias": ["Tática", "Liderança", "Pontaria", "Fortitude"],
        "personalidade": "Líder nato, mantém a formação defensiva e coordena os disparos do grupo.",
        "rituais": [],
    },
    {
        "token_id": 7,
        "nome": "Rubens Naluti",
        "classe": "Especialista",
        "trilha": "Técnico",
        "nex": 25,
        "pv_base": 26,
        "san_base": 24,
        "pe_base": 16,
        "defesa": 16,
        "armas": ["Escopeta", "Granada de Fragmentação"],
        "habilidades": ["Mochila de Utilidades", "Remendar no Combate"],
        "pericias": ["Profissão (Mecânico)", "Pontaria", "Tecnologia"],
        "personalidade": "Pragmático, engenhoso, gosta de usar o ambiente e explosivos a seu favor.",
        "rituais": [],
    },
    {
        "token_id": 8,
        "nome": "Milo",
        "classe": "Ocultista",
        "trilha": "Lâmina Paranormal",
        "nex": 25,
        "pv_base": 22,
        "san_base": 24,
        "pe_base": 20,
        "defesa": 16,
        "armas": ["Rapieira", "Adaga Amaldiçoada"],
        "habilidades": ["Lâmina Amaldiçoada (Ataca com Ocultismo)", "Golpe Conjurador"],
        "pericias": ["Ocultismo", "Luta", "Reflexos"],
        "personalidade": "Intenso, dança entre os golpes físicos e rituais cortantes de Sangue.",
        "rituais": [
            {"nome": "Amaldiçoar Arma", "elemento": "Conhecimento", "custo_pe": 1},
            {"nome": "Armadura de Sangue", "elemento": "Sangue", "custo_pe": 1},
            {"nome": "Decadência", "elemento": "Morte", "custo_pe": 1},
        ],
    },
]

GRID_COORDS = ["A1", "A2", "A3", "B1", "B2", "B3", "C2", "C3", "C4", "D3", "D4", "D5", "E3", "E4", "E5", "F4", "F5"]


def gerar_cenario_aleatorio() -> Dict[str, Any]:
    """Gera um encontro tático canônico com 3 a 4 protagonistas sorteados do roster."""
    ambiente = random.choice(AMBIENTES)
    criatura_dados = random.choice(CRIATURAS_CATALOGO)

    pos_criatura = random.choice(["D5", "E5", "C6", "F4", "D4", "E6"])

    # Seleciona 3 protagonistas diferentes para a sessão
    protagonistas_selecionados = random.sample(ROSTER_PROTAGONISTAS, 3)

    # Sorteia o perfil de desgaste da rodada
    perfil_status = random.choice([
        "saudavel", "desgastado", "critico_sanidade", "critico_pv", "sem_pe", "aliado_morrendo"
    ])

    agentes: Dict[int, AgenteFicha] = {}
    grid_disponiveis = ["A1", "A2", "B1", "B2", "B3", "C2", "C3"]

    for idx, proto in enumerate(protagonistas_selecionados):
        token_id = proto["token_id"]
        pos_grid = random.choice(grid_disponiveis)
        grid_disponiveis.remove(pos_grid)

        # Ajusta vitais conforme perfil de status
        if perfil_status == "saudavel":
            pv = proto["pv_base"]
            san = proto["san_base"]
            pe = proto["pe_base"]
        elif perfil_status == "desgastado":
            pv = max(8, int(proto["pv_base"] * 0.65))
            san = max(6, int(proto["san_base"] * 0.60))
            pe = max(3, int(proto["pe_base"] * 0.40))
        elif perfil_status == "critico_sanidade":
            pv = int(proto["pv_base"] * 0.8)
            san = 3 if idx == 0 else int(proto["san_base"] * 0.4)  # Um agente em delírio extremo
            pe = proto["pe_base"]
        elif perfil_status == "critico_pv":
            pv = 5 if idx == 0 else int(proto["pv_base"] * 0.5)  # Um agente quase caindo
            san = int(proto["san_base"] * 0.7)
            pe = max(1, int(proto["pe_base"] * 0.3))
        elif perfil_status == "aliado_morrendo":
            pv = 1 if idx == 0 else proto["pv_base"]  # Primeiro aliado caído (morrendo!)
            san = int(proto["san_base"] * 0.8)
            pe = proto["pe_base"]
        else:  # sem_pe
            pv = int(proto["pv_base"] * 0.8)
            san = int(proto["san_base"] * 0.8)
            pe = 0  # Sem PE nenhum

        agentes[token_id] = AgenteFicha(
            token_id=token_id,
            nome=proto["nome"],
            classe=proto["classe"],
            trilha=proto["trilha"],
            nex=proto["nex"],
            pv_atual=pv,
            pv_max=proto["pv_base"],
            san_atual=san,
            san_max=proto["san_base"],
            pe_atual=pe,
            pe_max=proto["pe_base"],
            defesa=proto["defesa"],
            grid=pos_grid,
            personalidade=proto["personalidade"],
            armas=proto["armas"],
            habilidades=proto["habilidades"],
            pericias=proto["pericias"],
            rituais=proto["rituais"],
        )

    # Detalhes da Ameaça
    presenca_txt = ""
    if criatura_dados.get("presenca_perturbadora"):
        p_dt = criatura_dados["presenca_perturbadora"]["dt"]
        p_dano = criatura_dados["presenca_perturbadora"]["dano_mental"]
        presenca_txt = f"Presença Perturbadora: Vontade DT {p_dt} ou sofre {p_dano} de dano mental."

    ameaca = {
        "id": 11,
        "name": criatura_dados["nome"],
        "tipo": f"{criatura_dados['elemento']} (VD {criatura_dados['vd']})",
        "elemento": criatura_dados["elemento"],
        "grid": pos_criatura,
        "distancia": f"{random.randint(1, 4)} quadrados (Curto/Adjacente)",
        "vulnerabilidade": criatura_dados.get("vulnerabilidade", "Nenhuma"),
        "presenca": presenca_txt,
    }

    narrativa_completa = (
        f"{ambiente['narrativa']} Em [{pos_criatura}], surge {criatura_dados['nome']}! "
        f"{presenca_txt} {ambiente['terreno']}"
    )

    return {
        "ambiente": ambiente["nome"],
        "narrativa": narrativa_completa,
        "agentes": agentes,
        "ameacas": [ameaca],
        "perfil_status": perfil_status,
    }
