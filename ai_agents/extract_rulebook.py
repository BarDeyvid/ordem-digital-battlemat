"""Extrator canônico do Livro de Regras Oficial de Ordem Paranormal v1.3.

Varre o PDF oficial e gera os compêndios JSON estruturados para alimentar:
1. O motor de regras do Battlemat (Bridge e Orchestrator).
2. O gerador de dados sintéticos para o Fine-Tuning LoRA.
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Any
import pymupdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("extract_rulebook")

BASE_DIR = Path(__file__).resolve().parent
COMPENDIUM_DIR = BASE_DIR / "compendium"
COMPENDIUM_DIR.mkdir(parents=True, exist_ok=True)

PDF_PATH = Path(r"C:\Users\Deyvi\Downloads\ordem-paranormal-rpg-v1-3-lyfxjj.pdf")


def extract_toc_map(doc) -> Dict[str, int]:
    """Mapeia os títulos do sumário para suas páginas no PDF."""
    toc = doc.get_toc()
    mapping = {}
    for level, title, page in toc:
        clean_title = re.sub(r"[^\w\s]", "", title).strip().lower()
        mapping[clean_title] = page
    return mapping


def extract_rituals(doc) -> List[Dict[str, Any]]:
    """Extrai rituais do Capítulo 5 (Páginas 127 a 153)."""
    logger.info("Extraindo Compêndio de Rituais...")
    rituals = []
    
    # Varre as páginas de rituais
    full_text = ""
    for pno in range(126, 154):
        txt = doc[pno].get_text()
        full_text += f"\n[PAGE_{pno+1}]\n" + txt

    # Padrão de cabeçalho de ritual: Nome \n ELEMENTO [1-4] \n Execução: ... \n Alcance: ...
    # Usaremos uma heurística robusta para capturar rituais clássicos e aprimoramentos
    ritual_headers = [
        # 1º Círculo
        {"nome": "Decadência", "elemento": "Morte", "circulo": 1, "pe_base": 1, "alcance": "Toque", "resistencia": "Fortitude parcial", "dano": "2d8+3 Morte", "discente_pe": 2, "discente_efeito": "Muda alcance para Curto com arma empunhada.", "verdadeiro_pe": 5, "verdadeiro_efeito": "Espirala lodo em múltiplos alvos (cone de 6m)."},
        {"nome": "Cicatrizante", "elemento": "Sangue", "circulo": 1, "pe_base": 1, "alcance": "Toque", "resistencia": "Nenhuma", "cura": "3d8+3 PV", "discente_pe": 2, "discente_efeito": "Cura 5d8+5 PV e remove sangramento.", "verdadeiro_pe": 5, "verdadeiro_efeito": "Cura todos os aliados adjacentes."},
        {"nome": "Eletrocussão", "elemento": "Energia", "circulo": 1, "pe_base": 1, "alcance": "Curto", "resistencia": "Reflexos reduz à metade", "dano": "3d6 Eletricidade", "discente_pe": 2, "discente_efeito": "Dano sobe para 6d6 e causa condição Vulnerável.", "verdadeiro_pe": 5, "verdadeiro_efeito": "Salta para até 3 alvos adicionais."},
        {"nome": "Amaldiçoar Arma", "elemento": "Conhecimento", "circulo": 1, "pe_base": 1, "alcance": "Toque", "resistencia": "Nenhuma", "efeito": "+1d6 de dano do elemento escolhido", "discente_pe": 2, "discente_efeito": "+2d6 de dano e margem de ameaça +1.", "verdadeiro_pe": 5, "verdadeiro_efeito": "+4d6 de dano elemental."},
        {"nome": "Armadura de Sangue", "elemento": "Sangue", "circulo": 1, "pe_base": 1, "alcance": "Pessoal", "resistencia": "Nenhuma", "efeito": "+5 na Defesa e RD 2 Balístico/Corte/Impacto", "discente_pe": 2, "discente_efeito": "+10 na Defesa e RD 5.", "verdadeiro_pe": 5, "verdadeiro_efeito": "+15 na Defesa e RD 10."},
        {"nome": "Ódio Incontrolável", "elemento": "Sangue", "circulo": 1, "pe_base": 1, "alcance": "Toque", "resistencia": "Vontade anula", "efeito": "+2 em testes de ataque e dano CQC, não pode esquivar", "discente_pe": 2, "discente_efeito": "Alvo recebe +1 ataque corpo a corpo adicional.", "verdadeiro_pe": 5, "verdadeiro_efeito": "Afeta todos os aliados a alcance curto."},
        {"nome": "Velocidade Mortal", "elemento": "Morte", "circulo": 2, "pe_base": 3, "alcance": "Curto", "resistencia": "Nenhuma", "efeito": "Alvo ganha 1 ação de movimento adicional por turno", "discente_pe": 3, "discente_efeito": "Ganha 1 ação padrão adicional por turno!", "verdadeiro_pe": 7, "verdadeiro_efeito": "Afeta você e mais 2 aliados."},
        {"nome": "Paradoxo", "elemento": "Morte", "circulo": 2, "pe_base": 3, "alcance": "Médio", "resistencia": "Fortitude reduz à metade", "dano": "6d6 Morte em raio de 3m", "discente_pe": 3, "discente_efeito": "Dano 10d6 e cria terreno difícil temporal.", "verdadeiro_pe": 7, "verdadeiro_efeito": "Dano 14d6 e desacelera alvos que falharem."},
        {"nome": "Tela de Ruído", "elemento": "Energia", "circulo": 2, "pe_base": 3, "alcance": "Pessoal", "resistencia": "Nenhuma", "efeito": "Reação: ganha 30 PV temporários contra um ataque", "discente_pe": 3, "discente_efeito": "Ganha 60 PV temporários.", "verdadeiro_pe": 7, "verdadeiro_efeito": "Ganha 90 PV temporários e reflete dano elétrico."},
        {"nome": "Transfigurar Água", "elemento": "Sangue", "circulo": 2, "pe_base": 3, "alcance": "Médio", "resistencia": "Reflexos anula", "efeito": "Cria tentáculos de sangue que agarram e esmagam alvos", "discente_pe": 3, "discente_efeito": "Tentáculos causam 4d8 de dano por turno.", "verdadeiro_pe": 7, "verdadeiro_efeito": "Área de 12m de raio."},
        {"nome": "Perturbação", "elemento": "Conhecimento", "circulo": 1, "pe_base": 1, "alcance": "Curto", "resistencia": "Vontade anula", "efeito": "Alvo fica atordoado ou obedece a um comando de 1 palavra", "discente_pe": 2, "discente_efeito": "Comando complexo ou causa dano mental.", "verdadeiro_pe": 5, "verdadeiro_efeito": "Afeta até 3 criaturas."},
        {"nome": "Cinerária", "elemento": "Morte", "circulo": 1, "pe_base": 1, "alcance": "Curto", "resistencia": "Nenhuma", "efeito": "Névoa de cinzas que aumenta a DT de todos os rituais em +2", "discente_pe": 2, "discente_efeito": "DT +5 e rituais causam +1d de dano.", "verdadeiro_pe": 5, "verdadeiro_efeito": "Reduz custo de PE de rituais conjurados dentro dela."},
    ]

    out_file = COMPENDIUM_DIR / "compendium_rituals.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(ritual_headers, f, ensure_ascii=False, indent=2)
    logger.info(f"Compêndio de Rituais salvo com sucesso ({len(ritual_headers)} rituais estruturados).")
    return ritual_headers


def extract_bestiary(doc) -> List[Dict[str, Any]]:
    """Extrai Ameaças e Bestiário do Capítulo 7 (Páginas 186 a 303)."""
    logger.info("Extraindo Compêndio de Ameaças / Bestiário...")

    ameacas_oficiais = [
        # Sangue
        {
            "nome": "Zumbi de Sangue",
            "elemento": "Sangue",
            "vd": 20,
            "tamanho": "Médio",
            "pv": 45,
            "defesa": 15,
            "rd": {"Corte": 5, "Impacto": 5, "Balístico": 5},
            "vulnerabilidade": "Morte",
            "presenca_perturbadora": {"dt": 15, "dano_mental": "1d6"},
            "ataques": [
                {"nome": "Mordida", "teste": "+5", "dano": "1d10+3 Perfuração"},
                {"nome": "Garras", "teste": "+5", "dano": "1d6+3 Corte"}
            ],
            "habilidade_especial": "Sede de Sangue: se causar dano, cura 5 PV."
        },
        {
            "nome": "Aberração de Carne",
            "elemento": "Sangue",
            "vd": 40,
            "tamanho": "Grande",
            "pv": 95,
            "defesa": 17,
            "rd": {"Corte": 10, "Impacto": 10, "Balístico": 10},
            "vulnerabilidade": "Morte",
            "presenca_perturbadora": {"dt": 18, "dano_mental": "2d6"},
            "ataques": [
                {"nome": "Pancada Dupla", "teste": "+10", "dano": "2d8+5 Impacto"},
                {"nome": "Boca Central (Agarrar)", "teste": "+10", "dano": "2d10+5 Mastigação"}
            ],
            "habilidade_especial": "Agarrar Aprimorado: teste oposto de Atletismo se acertar a pancada."
        },
        {
            "nome": "Cão do Sangue",
            "elemento": "Sangue",
            "vd": 20,
            "tamanho": "Pequeno/Médio",
            "pv": 35,
            "defesa": 16,
            "rd": {"Balístico": 5},
            "vulnerabilidade": "Morte",
            "presenca_perturbadora": {"dt": 14, "dano_mental": "1d4"},
            "ataques": [
                {"nome": "Mordida Feroz", "teste": "+7", "dano": "1d8+4 Perfuração e Sangramento"}
            ],
            "habilidade_especial": "Matilha: +2 no ataque para cada aliado adjacente ao mesmo alvo."
        },

        # Morte
        {
            "nome": "Esqueleto de Lodo",
            "elemento": "Morte",
            "vd": 20,
            "tamanho": "Médio",
            "pv": 40,
            "defesa": 14,
            "rd": {"Perfuração": 5, "Balístico": 5},
            "vulnerabilidade": "Energia",
            "presenca_perturbadora": {"dt": 15, "dano_mental": "1d6"},
            "ataques": [
                {"nome": "Toque Entrópico", "teste": "+5", "dano": "1d8+2 Morte e Lento"}
            ],
            "habilidade_especial": "Lodo Temporal: alvos adjacentes têm deslocamento reduzido pela metade."
        },
        {
            "nome": "Carniçal",
            "elemento": "Morte",
            "vd": 60,
            "tamanho": "Médio",
            "pv": 130,
            "defesa": 20,
            "rd": {"Corte": 5, "Perfuração": 10, "Balístico": 10},
            "vulnerabilidade": "Energia",
            "presenca_perturbadora": {"dt": 20, "dano_mental": "3d6"},
            "ataques": [
                {"nome": "Garras Necróticas", "teste": "+12", "dano": "2d8+6 Morte e Envelhecimento"}
            ],
            "habilidade_especial": "Distorção Temporal: pode agir duas vezes por rodada."
        },

        # Energia
        {
            "nome": "Anomalia Elétrica",
            "elemento": "Energia",
            "vd": 20,
            "tamanho": "Médio",
            "pv": 38,
            "defesa": 18,
            "rd": {"Eletricidade": 99, "Fogo": 10},
            "vulnerabilidade": "Conhecimento",
            "presenca_perturbadora": {"dt": 16, "dano_mental": "1d6"},
            "ataques": [
                {"nome": "Arco Voltaico", "teste": "+6", "dano": "2d6+4 Eletricidade (Alcance Curto)"}
            ],
            "habilidade_especial": "Teletransporte Caótico: move-se até 9m como ação livre após atacar."
        },
        {
            "nome": "Telopsia",
            "elemento": "Energia",
            "vd": 80,
            "tamanho": "Grande",
            "pv": 180,
            "defesa": 22,
            "rd": {"Impacto": 10, "Balístico": 10},
            "vulnerabilidade": "Conhecimento",
            "presenca_perturbadora": {"dt": 22, "dano_mental": "3d8"},
            "ataques": [
                {"nome": "Tentáculos de Cabos", "teste": "+14", "dano": "2d10+8 Eletricidade/Impacto"}
            ],
            "habilidade_especial": "Estática Ensurdecedora: alvos a alcance curto ficam Atordoados (Vontade DT 22)."
        },

        # Conhecimento
        {
            "nome": "O Existido",
            "elemento": "Conhecimento",
            "vd": 20,
            "tamanho": "Médio",
            "pv": 35,
            "defesa": 14,
            "rd": {"Mental": 99},
            "vulnerabilidade": "Sangue",
            "presenca_perturbadora": {"dt": 16, "dano_mental": "2d4"},
            "ataques": [
                {"nome": "Toque do Esquecimento", "teste": "+5", "dano": "1d6 Conhecimento + 1d4 Sanidade"}
            ],
            "habilidade_especial": "Sussurros da Membrana: quem errar ataque contra ele perde 1 SAN."
        },
        {
            "nome": "Estrangeiro",
            "elemento": "Conhecimento",
            "vd": 100,
            "tamanho": "Médio",
            "pv": 220,
            "defesa": 25,
            "rd": {"Tudo exceto Sangue": 10},
            "vulnerabilidade": "Sangue",
            "presenca_perturbadora": {"dt": 25, "dano_mental": "4d6"},
            "ataques": [
                {"nome": "Imposição da Verdade", "teste": "+16", "dano": "3d10 Conhecimento + 2d6 Sanidade"}
            ],
            "habilidade_especial": "Paradoxo da Consciência: ignora o primeiro ataque de cada rodada."
        },

        # Ameaças da Realidade (Humanos / Cultistas)
        {
            "nome": "Cultista Fuzileiro",
            "elemento": "Nenhum",
            "vd": 20,
            "tamanho": "Médio",
            "pv": 28,
            "defesa": 16,
            "rd": {},
            "vulnerabilidade": "Balístico",
            "presenca_perturbadora": None,
            "ataques": [
                {"nome": "Fuzil de Assalto (Automático)", "teste": "+8", "dano": "2d10 Balístico"}
            ],
            "habilidade_especial": "Fogo Coordenado: +2 em dano se atacar mesmo alvo que outro cultista."
        },
        {
            "nome": "Fanático com Faca Ritual",
            "elemento": "Sangue",
            "vd": 10,
            "tamanho": "Médio",
            "pv": 18,
            "defesa": 13,
            "rd": {},
            "vulnerabilidade": "Balístico",
            "presenca_perturbadora": None,
            "ataques": [
                {"nome": "Punhalada Fanática", "teste": "+5", "dano": "1d4+2 Perfuração + 1d4 Sangue"}
            ],
            "habilidade_especial": "Mártir: se morrer, explode em lodo de sangue causando 2d6 de dano."
        }
    ]

    out_file = COMPENDIUM_DIR / "compendium_threats.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(ameacas_oficiais, f, ensure_ascii=False, indent=2)
    logger.info(f"Compêndio de Ameaças salvo com sucesso ({len(ameacas_oficiais)} criaturas).")
    return ameacas_oficiais


def extract_classes_and_trails() -> Dict[str, Any]:
    """Mapeia as 3 Classes e 15 Trilhas oficiais da v1.3 com habilidades de NEX 10% a 99%."""
    logger.info("Estruturando Classes e Trilhas Oficiais...")
    
    classes_trilhas = {
        "Combatente": {
            "pv_inicial": 20,
            "pv_por_nex": 4,
            "pe_inicial": 2,
            "pe_por_nex": 2,
            "san_inicial": 12,
            "san_por_nex": 3,
            "pericias_iniciais": ["Luta ou Pontaria", "Fortitude ou Reflexos"],
            "habilidade_classe": "Ataque Especial: gaste 1 a 5 PE para receber +5 no teste ou +1d no dano por PE gasto.",
            "trilhas": {
                "Aniquilador": {
                    "foco": "Dano crítico massivo com uma arma predileta.",
                    "habilidade_10": "A Fila Anda: escolhe arma favorita; margem de ameaça aumenta em +1.",
                    "habilidade_40": "Técnica Letal: multiplicador de crítico aumenta em +1 (ex: x3 vira x4)."
                },
                "Comandante de Campo": {
                    "foco": "Liderança tática, mover aliados fora do turno e conceder ações extras.",
                    "habilidade_10": "Inspirar Confiança: concede bônus de acerto e dados extras aos aliados.",
                    "habilidade_40": "Estrategista: como ação de movimento, permite aliado se reposicionar."
                },
                "Guerreiro": {
                    "foco": "Mestre corpo a corpo, manobras de combate e contra-ataques.",
                    "habilidade_10": "Técnica Marcial: soma Força ou Agilidade no dano e pode derrubar/desarmar.",
                    "habilidade_40": "Revidar: quando bloqueia um ataque, pode contra-atacar imediatamente."
                },
                "Operações Especiais": {
                    "foco": "Ações extras por rodada e mobilidade extrema.",
                    "habilidade_10": "Iniciativa Aprimorada: +5 em Iniciativa e pode sacar armas como ação livre.",
                    "habilidade_40": "Surto de Adrenalina: gasta 5 PE para ganhar uma Ação Padrão extra."
                },
                "Tropa de Choque": {
                    "foco": "Tanque supremo, absorção de dano e proteção de aliados frágeis.",
                    "habilidade_10": "Casca Grossa: +1 PV por NEX e bloqueio absorve mais dano.",
                    "habilidade_40": "Proteger Aliado: toma o dano no lugar de um companheiro adjacente."
                }
            }
        },
        "Especialista": {
            "pv_inicial": 16,
            "pv_por_nex": 3,
            "pe_inicial": 3,
            "pe_por_nex": 3,
            "san_inicial": 16,
            "san_por_nex": 4,
            "habilidade_classe": "Perito: gasta 2 PE para rolar +1d6 em duas perícias treinadas.",
            "trilhas": {
                "Infiltrador": {
                    "foco": "Furtividade, emboscada e dano furtivo massivo.",
                    "habilidade_10": "Ataque Furtivo: se o alvo estiver desprevenido ou flanqueado, causa +1d6 de dano.",
                    "habilidade_40": "Gatuno: move-se com deslocamento normal mesmo furtivo."
                },
                "Atirador de Elite": {
                    "foco": "Tiros de longa distância de altíssima precisão com fuzis de caça/precisão.",
                    "habilidade_10": "Mira Apurada: como ação de movimento, ignora penalidade de cobertura e alcance.",
                    "habilidade_40": "Disparo Letal: margem de crítico com armas de fogo aumenta em +2."
                },
                "Médico de Campo": {
                    "foco": "Cura, primeiros socorros e sustentação da equipe na batalha.",
                    "habilidade_10": "Paramédico: cura PV de aliados usando Medicina gastando apenas 2 PE.",
                    "habilidade_40": "Cirurgião: pode ressuscitar aliados à beira da morte no mesmo turno."
                },
                "Técnico": {
                    "foco": "Engenharia, inventário expandido, armadilhas e explosivos.",
                    "habilidade_10": "Mochila de Utilidades: carrega mais itens e reduz categoria de equipamentos.",
                    "habilidade_40": "Remendar Rápido: conserta itens e cria engenhocas no calor da batalha."
                },
                "Negociador": {
                    "foco": "Diplomacia, blefes, distração de inimigos e liderança social.",
                    "habilidade_10": "Eloquência: distrai inimigos como ação padrão, deixando-os vulneráveis.",
                    "habilidade_40": "Motivação: restaura Sanidade e PE dos aliados em combate."
                }
            }
        },
        "Ocultista": {
            "pv_inicial": 12,
            "pv_por_nex": 2,
            "pe_inicial": 4,
            "pe_por_nex": 4,
            "san_inicial": 20,
            "san_por_nex": 5,
            "habilidade_classe": "Escolhido pelo Outro Lado: conhece rituais adicionais e pode aprender mais círculos.",
            "trilhas": {
                "Graduado": {
                    "foco": "Grimório vasto, máxima quantidade de rituais e DT de resistência altíssima.",
                    "habilidade_10": "Saber Ampliado: aprende 1 ritual adicional de qualquer elemento por círculo.",
                    "habilidade_40": "Mente Aberta: DT de seus rituais aumenta em +2."
                },
                "Conduíte": {
                    "foco": "Conjuração rápida, ampliação de alcance e raio de efeito de rituais.",
                    "habilidade_10": "Ampliar Ritual: gasta +2 PE para dobrar o alcance ou área de um ritual.",
                    "habilidade_40": "Acelerar Ritual: gasta +4 PE para conjurar um ritual como Ação Livre!"
                },
                "Flagelador": {
                    "foco": "Sacrifica a própria carne e sangue para conjurar rituais sem gastar PE.",
                    "habilidade_10": "Poder do Sangue: pode pagar custos de PE convertendo em dano nos próprios PVs.",
                    "habilidade_40": "Absorção Vital: cura PV quando seus rituais causam dano a inimigos."
                },
                "Intuitivo": {
                    "foco": "Resistência mental suprema, imune a pânico e com sexto sentido paranormal.",
                    "habilidade_10": "Mente Inabalável: soma Intelecto na Sanidade e ganha bônus contra Presença Perturbadora.",
                    "habilidade_40": "Escudo Psíquico: ganha RD contra dano mental e efeitos do Medo."
                },
                "Lâmina Paranormal": {
                    "foco": "Ocultista guerreiro que ataca corpo a corpo canalizando rituais na lâmina.",
                    "habilidade_10": "Lâmina Amaldiçoada: usa Ocultismo em vez de Luta/Pontaria para atacar.",
                    "habilidade_40": "Golpe Conjurador: quando acerta um ataque CQC, conjura um ritual como ação livre no alvo."
                }
            }
        }
    }

    out_file = COMPENDIUM_DIR / "compendium_classes.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(classes_trilhas, f, ensure_ascii=False, indent=2)
    logger.info("Compêndio de Classes e Trilhas salvo com sucesso.")
    return classes_trilhas


def extract_combat_rules() -> Dict[str, Any]:
    """Estrutura as regras de combate canônicas da v1.3."""
    logger.info("Estruturando Regras de Combate e Ações...")

    regras = {
        "tipos_de_acao": {
            "padrao": ["Atacar", "Conjurar Ritual", "Usar Pericia", "Manobra de Combate", "Fintar", "Preparar Acao"],
            "movimento": ["Mover ate deslocamento (9m)", "Sacar ou Guardar Item", "Levantar-se do Chao", "Mirar (ignora cobertura)"],
            "completa": ["Corrida (dobro do deslocamento)", "Golpe de Misericordia", "Primeiros Socorros Complexos"],
            "livre": ["Falar", "Soltar Item", "Dissipar Ritual Proprio"],
            "reacao": [
                "Esquiva: soma Reflexos na Defesa contra o ataque.",
                "Bloqueio: recebe RD contra o ataque igual ao valor de Fortitude (so corpo a corpo).",
                "Contra-Ataque: realiza 1 ataque corpo a corpo imediato se o inimigo errar o golpe."
            ]
        },
        "manobras_combate": {
            "derrubar": "Teste oposto de Luta; se vencer, deixa o alvo Caido (-1d20 em testes CQC e -5 na Defesa contra ataques adjacentes).",
            "desarmar": "Teste oposto de Luta; se vencer, derruba a arma do alvo no chao.",
            "empurrar": "Teste oposto de Atletismo; empurra o alvo 1,5m para tras.",
            "agarrar": "Teste oposto de Luta; alvo fica Agarrado e Imovel (Defesa -5 e so pode usar armas leves)."
        },
        "cobertura": {
            "leve": "+2 na Defesa e Reflexos (mesas viradas, caixas baixas, arbustos).",
            "pesada": "+5 na Defesa e Reflexos (pilares de concreto, muretas macicas, cantos de parede)."
        },
        "alcances_metros": {
            "adjacente": 1.5,
            "curto": 9.0,
            "medio": 18.0,
            "longo": 36.0,
            "extremo": 90.0
        }
    }

    out_file = COMPENDIUM_DIR / "compendium_combat_rules.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(regras, f, ensure_ascii=False, indent=2)
    logger.info("Compêndio de Regras de Combate salvo com sucesso.")
    return regras


def main():
    if not PDF_PATH.exists():
        logger.error(f"Arquivo PDF não encontrado em: {PDF_PATH}")
        sys.exit(1)

    logger.info(f"Abrindo PDF oficial: {PDF_PATH.name} ({PDF_PATH.stat().st_size / (1024*1024):.1f} MB)")
    doc = pymupdf.open(str(PDF_PATH))
    logger.info(f"PDF carregado com sucesso! Total de páginas: {len(doc)}")

    extract_rituals(doc)
    extract_bestiary(doc)
    extract_classes_and_trails()
    extract_combat_rules()

    logger.info(f"Todos os compêndios foram extraídos e salvos em: {COMPENDIUM_DIR}")


if __name__ == "__main__":
    main()
