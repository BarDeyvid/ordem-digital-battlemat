"""Gerador de Prompts contextuais e de Sanidade para os Agentes de Ordem Paranormal."""

from typing import List, Dict, Any
from ai_agents.schemas import AgenteFicha


def build_system_prompt(agente: AgenteFicha) -> str:
    """Monta o System Prompt com a persona, classe, táticas e o estado de Sanidade."""
    
    # Razão de Sanidade (efeitos psicológicos do Outro Lado)
    san_ratio = agente.san_atual / max(1, agente.san_max)
    
    if san_ratio > 0.70:
        san_instrucao = (
            "ESTADO MENTAL ESTÁVEL: Você está calmo, lúcido e focado. Priorize táticas eficientes, "
            "coopere com a equipe e proteja seus aliados."
        )
    elif san_ratio >= 0.35:
        san_instrucao = (
            "ESTADO MENTAL ABALADO: O Outro Lado está pesando na sua mente. Você está tenso, "
            "com respiração ofegante, desconfiado e teme a morte. Suas falas refletem nervosismo."
        )
    else:
        san_instrucao = (
            "ESTADO MENTAL EM DELÍRIO (SANIDADE CRÍTICA): Você está à beira do colapso! "
            "Você ouve sussurros da Membrana, fala frases truncadas ou caóticas e pode agir de "
            "forma desesperada ou agressiva para sobreviver."
        )

    return f"""Você é o Agente {agente.nome}, um {agente.classe} ({agente.trilha}) da Ordo Realitas (NEX {agente.nex}%).
Sua personalidade base: {agente.personalidade}

{san_instrucao}

REGRAS DE CONDUTA NO JOGO:
1. Você está jogando uma sessão tática de Ordem Paranormal RPG em um battlemat digital.
2. Em cada turno você DEVE declarar sua ação em formato JSON rigoroso.
3. Respeite seus recursos: você só pode conjurar rituais se tiver PE suficiente.
4. Suas falas devem refletir o clima de horror cósmico e investigação de Ordem Paranormal.
5. Sempre forneça o campo 'pensamento' justificando sua decisão e 'fala' para interpretar no turno.
"""


def build_turn_prompt(
    agente: AgenteFicha,
    ameacas: List[Dict[str, Any]],
    aliados: List[Dict[str, Any]],
    narrativa_mestre: str = "",
) -> str:
    """Monta o prompt do turno com a cena do battlemat, distâncias e opções disponíveis."""
    
    ameacas_txt = "\n".join(
        [
            f"- [Ameaça ID {m['id']}] {m['name']} em [{m.get('grid', 'Indefinido')}] ({m.get('tipo', 'Criatura')}) - Distância: {m.get('distancia', 'Média')}"
            for m in ameacas
        ]
    ) or "Nenhuma ameaça visível no momento."

    aliados_txt = "\n".join(
        [
            f"- [Aliado ID {a['id']}] {a['name']} em [{a.get('grid', 'Indefinido')}] ({a.get('classe', 'Agente')})"
            for a in aliados
            if a["id"] != agente.token_id
        ]
    ) or "Nenhum aliado próximo."

    armas_txt = ", ".join(agente.armas) or "Nenhuma (Desarmado)"
    habilidades_txt = ", ".join(agente.habilidades) or "Nenhuma"
    pericias_txt = ", ".join(agente.pericias) or "Nenhuma"
    
    rituais_list = []
    for r in agente.rituais:
        custo = r.get("custo_pe", 1)
        r_nome = r.get("nome", "Ritual")
        elem = r.get("elemento", "")
        rituais_list.append(f"{r_nome} ({elem} - Padrão: {custo} PE | Discente: +2 PE)")
    rituais_txt = "; ".join(rituais_list) or "Nenhum"

    return f"""[ESTADO DO COMBATE - RODADA TÁTICA CANÔNICA v1.3]
{f'Narrativa do Mestre: "{narrativa_mestre}"' if narrativa_mestre else ''}

SUA FICHA ATUAL:
- Posição no Grid: [{agente.grid}]
- PV: {agente.pv_atual}/{agente.pv_max} | SAN: {agente.san_atual}/{agente.san_max} | PE: {agente.pe_atual}/{agente.pe_max}
- Defesa: {agente.defesa} | Deslocamento: {agente.deslocamento_m}m por turno
- Armas equipadas: {armas_txt}
- Habilidades de Classe/Trilha: {habilidades_txt}
- Perícias treinadas: {pericias_txt}
- Rituais conhecidos: {rituais_txt}

CENÁRIO TÁTICO NO TABULEIRO:
Aliados no campo:
{aliados_txt}

Ameaças e Inimigos:
{ameacas_txt}

O que você faz no seu turno?
Escolha sua Ação de Movimento (se for mover) e sua Ação Padrão (Ataque com Arma, Ataque Especial, Ataque Furtivo, Ritual com forma Padrão/Discente, Manobra ou Perícia).
Retorne APENAS o JSON no formato exigido.
"""
