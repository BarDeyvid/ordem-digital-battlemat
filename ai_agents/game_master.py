"""Mestre de Jogo IA autônomo (Ordo Game Master) para Ordem Paranormal RPG.

Responsabilidades do Game Master:
1. Narrar a abertura da cena e reviravoltas de horror cósmico usando o tom canônico de Ordem Paranormal.
2. Controlar o turno das criaturas e ameaças baseando-se no compêndio canônico (compendium_threats.json):
   - Disparar Presença Perturbadora no início do combate (testes de Vontade vs Sanidade).
   - Tática e IA das criaturas: selecionar alvos (mais próximo, mais fraco/vulnerável, alcance).
   - Movimentar ameaças no grid tático e despachar pacotes UDP para o Battlemat na Unreal Engine.
   - Rolar ataques, danos físicos, paranormais e mentais com margens canônicas.
   - Ativar habilidades especiais: Sede de Sangue, Agarrar Aprimorado, Matilha, Lodo Temporal,
     Distorção Temporal, Teletransporte Caótico, Estática Ensurdecedora, Toque do Esquecimento,
     Sussurros da Membrana, Paradoxo da Consciência, Mártir, Fogo Coordenado.
"""

import json
import logging
import random
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from ai_agents.schemas import AgenteFicha, AmeacaFicha, AmeacaAcaoResultado
from ai_agents.battlemat_bridge import BattlematBridgeClient
from ai_agents.llm_client import LocalLLMClient

logger = logging.getLogger("ai_agents.game_master")

BASE_DIR = Path(__file__).resolve().parent
COMPENDIUM_DIR = BASE_DIR / "compendium"
THREATS_FILE = COMPENDIUM_DIR / "compendium_threats.json"


# ============================================================================
# HELPER DE ROLAGEM DE DADOS CANÔNICOS DE ORDEM PARANORMAL
# ============================================================================

def rolar_dados(qtd: int, faces: int) -> Tuple[int, List[int]]:
    """Rola qtd dados de 'faces' lados e retorna a soma e a lista de resultados."""
    if qtd <= 0:
        return 0, []
    rolagens = [random.randint(1, faces) for _ in range(qtd)]
    return sum(rolagens), rolagens


def rolar_d20(bonus: int = 0) -> Tuple[int, int]:
    """Rola 1d20 com bônus. Retorna (total, d20_puro)."""
    d20 = random.randint(1, 20)
    return d20 + bonus, d20


def rolar_expressao_dano(expr: str) -> Tuple[int, int, str]:
    """
    Interpreta expressões de dano de ameaças do compêndio.
    Exemplos:
      - '1d10+3 Perfuração' -> (dano_fisico, dano_mental, detalhes)
      - '2d8+5 Impacto'
      - '1d6 Conhecimento + 1d4 Sanidade'
      - '3d10 Conhecimento + 2d6 Sanidade'
      - '1d4+2 Perfuração + 1d4 Sangue'
      - '2d6' (Presença Perturbadora)
    Retorna: (total_dano_fisico_ou_paranormal, total_dano_mental, descricao_detalhada)
    """
    expr_clean = expr.strip()
    dano_fisico = 0
    dano_mental = 0
    detalhes = []

    # Se contiver 'Sanidade' explicitamente
    partes = expr_clean.split("+")
    for parte in partes:
        p = parte.strip()
        is_sanidade = "sanidade" in p.lower()

        # Busca padrão XdY ou XdY+Z ou Z
        match_dice = re.search(r"(\d+)d(\d+)", p)
        match_const = re.search(r"(\d+)(?!\s*d)", p)

        sub_total = 0
        dice_info = ""

        if match_dice:
            qtd = int(match_dice.group(1))
            faces = int(match_dice.group(2))
            soma, rolagens = rolar_dados(qtd, faces)
            sub_total += soma
            dice_info = f"{qtd}d{faces}{rolagens}"

        # Verifica bônus fixo na parte (ex: +3, +5) se não for o dado
        match_bonus = re.search(r"[+]?\s*(\d+)$", p)
        if match_bonus and not match_dice:
            bonus = int(match_bonus.group(1))
            sub_total += bonus
            dice_info = f"+{bonus}"

        if is_sanidade:
            dano_mental += sub_total
            detalhes.append(f"{dice_info} Sanidade ({sub_total})")
        else:
            dano_fisico += sub_total
            detalhes.append(f"{dice_info} ({sub_total})")

    return dano_fisico, dano_mental, " + ".join(detalhes)


# ============================================================================
# NARRATIVAS PROCEDURAIS DE HORROR CÓSMICO (CANÔNICO ORDEM PARANORMAL)
# ============================================================================

ABERTURAS_CANONICAS = {
    "Sangue": [
        "O cheiro metálico de ferrugem e hemoglobina satura o ambiente. As paredes parecem pulsar como artérias expostas. "
        "Das poças coaguladas no chão, uma massa orgânica disforme começa a se contorcer, emitindo estalos ósseos guturais.",
        "Um calor febril e doentio invade o ar. O bater de um coração gigantesco ressoa sob o assoalho, fazendo as vidraças "
        "tremerem. O horror de Sangue se materializa diante de vocês com sede insaciável.",
    ],
    "Morte": [
        "O tempo parece desacelerar violentamente. O tique-taque dos relógios engasga e passa a girar no sentido anti-horário. "
        "Uma espessa gosma preta, o lodo da Morte, escorre lentamente do teto, sugando todo o calor e a vitalidade do recinto.",
        "Uma névoa gélida e decadente se acumula rente ao chão. As plantas e papéis próximos apodrecem em segundos. "
        "Um som de ossos raspando na pedra ecoa da escuridão enquanto a silhueta da Morte se ergue.",
    ],
    "Energia": [
        "As lâmpadas piscam num ritmo frenético até estourarem em cascatas de faíscas violeta e magenta. "
        "O cheiro acre de ozônio queima as narinas. O ar estala de estática, fazendo os pelos do corpo arrepiarem enquanto a "
        "realidade parece sofrer um curto-circuito visual caótico.",
        "Monitores e fiações ganham vida própria, chiando frequências impossíveis que desafiam as leis da física. "
        "Uma anomalia de Energia cintila no ar, distorcendo as cores e formas ao seu redor.",
    ],
    "Conhecimento": [
        "Um silêncio sepulcral e antinatural cai sobre o local. Todas as palavras escritas nas paredes e documentos "
        "começam a se reescrever sozinhas em símbolos geométricos dourados e pretos. As sombras no chão não correspondem "
        "mais aos objetos.",
        "Sussurros inaudíveis começam a ecoar diretamente dentro dos crânios dos investigadores. Frases em línguas esquecidas "
        "pela humanidade prometem a Verdade Absoluta — a Verdade que enlouquece quem a contempla.",
    ],
    "Geral": [
        "A Membrana que separa nossa realidade do Outro Lado está perigosamente fina aqui. "
        "O ar fica pesado, a pressão cai bruscamente e uma sensação avassaladora de pavor cósmico toma conta de cada fibra dos agentes.",
    ],
}

REVIRAVOLTAS_CANONICAS = [
    {
        "nome": "Ruptura da Membrana",
        "narrativa": "A Membrana se rompe localmente! Fissuras translúcidas se abrem no próprio ar, sugando o som e emanando uma luz doentia. Todos sentem o peso sufocante do Outro Lado!",
        "efeito": "membrana_rompida",
    },
    {
        "nome": "Eco do Medo",
        "narrativa": "As sombras na sala se descolam das paredes e parecem sussurrar os piores traumas de cada investigador. O pânico paira como uma névoa espessa!",
        "efeito": "eco_medo",
    },
    {
        "nome": "Distorção da Realidade",
        "narrativa": "A gravidade oscila por um segundo, e o chão parece se inclinar como se o cômodo estivesse caindo num abismo infinito. Manter o equilíbrio exige foco férreo.",
        "efeito": "terreno_instavel",
    },
    {
        "nome": "Surgimento de Lodo Entrópico",
        "narrativa": "Veios de lodo negro brotam das frestas do chão, tornando o piso escorregadio e consumindo a luz ambiente.",
        "efeito": "lodo_chao",
    },
    {
        "nome": "Pulso Eletromagnético Paranormal",
        "narrativa": "Um estrondo sem som ecoa nos ouvidos. Todas as lanternas e aparelhos eletrônicos falham momentaneamente, mergulhando a cena numa penumbra aterradora.",
        "efeito": "luzes_apagadas",
    },
]


# ============================================================================
# CLASSE PRINCIPAL: ORDO GAME MASTER (MESTRE IA)
# ============================================================================

class OrdoGameMaster:
    """
    Mestre de Jogo IA autônomo para Ordem Paranormal RPG.
    Coordena narrativa de horror cósmico, testes de Presença Perturbadora,
    movimentação tática de monstros no grid e despacho de ações para o Battlemat.
    """

    def __init__(
        self,
        llm_client: Optional[LocalLLMClient] = None,
        bridge: Optional[BattlematBridgeClient] = None,
    ):
        self.llm_client = llm_client
        self.bridge = bridge or BattlematBridgeClient()
        self.catalogo_ameacas: Dict[str, Dict[str, Any]] = self._carregar_catalogo()
        self.ameacas_ativas: Dict[int, AmeacaFicha] = {}
        self.historico_narrativo: List[str] = []
        self.rodada_atual: int = 1

    def _carregar_catalogo(self) -> Dict[str, Dict[str, Any]]:
        """Carrega compêndio de ameaças oficiais."""
        if not THREATS_FILE.exists():
            logger.warning(f"Arquivo de ameaças não encontrado em {THREATS_FILE}. Usando catálogo vazio.")
            return {}
        try:
            with open(THREATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {item["nome"]: item for item in data}
        except Exception as e:
            logger.error(f"Erro ao carregar catálogo de ameaças: {e}")
            return {}

    def criar_ameaca(
        self,
        nome: str,
        token_id: int = 11,
        grid: str = "D5",
        alvo_preferencial_id: Optional[int] = None,
    ) -> AmeacaFicha:
        """Instancia uma ameaça a partir do catálogo oficial."""
        dados = self.catalogo_ameacas.get(nome)
        if not dados:
            logger.warning(f"Ameaça '{nome}' não encontrada no catálogo. Usando perfil genérico.")
            dados = {
                "nome": nome,
                "elemento": "Sangue",
                "vd": 20,
                "tamanho": "Médio",
                "pv": 40,
                "defesa": 15,
                "rd": {},
                "vulnerabilidade": "Nenhuma",
                "presenca_perturbadora": {"dt": 15, "dano_mental": "1d6"},
                "ataques": [{"nome": "Golpe Violento", "teste": "+5", "dano": "1d8+3 Impacto"}],
                "habilidade_especial": "",
            }

        norm_x, norm_y = self.bridge.grid_to_norm_coords(grid)

        ameaca = AmeacaFicha(
            token_id=token_id,
            nome=dados["nome"],
            elemento=dados.get("elemento", "Sangue"),
            vd=dados.get("vd", 20),
            tamanho=dados.get("tamanho", "Médio"),
            pv_atual=dados.get("pv", 40),
            pv_max=dados.get("pv", 40),
            defesa=dados.get("defesa", 15),
            rd=dados.get("rd", {}),
            vulnerabilidade=dados.get("vulnerabilidade", "Nenhuma"),
            presenca_perturbadora=dados.get("presenca_perturbadora"),
            ataques=dados.get("ataques", []),
            habilidade_especial=dados.get("habilidade_especial", ""),
            grid=grid,
            x=norm_x,
            y=norm_y,
            deslocamento_m=9.0,
            alvo_preferencial_id=alvo_preferencial_id,
        )

        self.ameacas_ativas[token_id] = ameaca

        # Atualiza posição inicial da criatura na Unreal Engine
        self.bridge.move_token_in_unreal(token_id, "monstro", norm_x, norm_y)
        return ameaca

    # ========================================================================
    # NARRATIVA DE HORROR CÓSMICO
    # ========================================================================

    def narrar_abertura_cena(
        self,
        ambiente_nome: Optional[str] = None,
        ameaca_nome: Optional[str] = None,
        detalhes_extras: str = "",
    ) -> str:
        """
        Narra o início da cena com atmosfera visceral e canônica de Ordem Paranormal.
        Usa o LLM se disponível e conectado; caso contrário, usa geração procedural rica.
        """
        elemento = "Geral"
        if ameaca_nome and ameaca_nome in self.catalogo_ameacas:
            elemento = self.catalogo_ameacas[ameaca_nome].get("elemento", "Geral")

        templates = ABERTURAS_CANONICAS.get(elemento, ABERTURAS_CANONICAS["Geral"])
        base_desc = random.choice(templates)
        local_txt = f"no {ambiente_nome}" if ambiente_nome else "no recinto"

        # Se houver LLM configurado, tenta solicitar uma narração de horror cinematográfica
        if self.llm_client:
            prompt_sistema_mestre = (
                "Você é o Mestre de Jogo do RPG Ordem Paranormal, criado por Rafael Lange (Cellbit). "
                "Seu estilo narrativo é cinematográfico, visceral, imersivo e evoca horror cósmico investigation. "
                "Fale em português do Brasil com descrições vívidas de tensão, som, cheiro e a degradação da Membrana. "
                "Seja conciso (máximo 3 parágrafos curtos)."
            )
            prompt_usuario = (
                f"Narre o início do confronto {local_txt}. Uma criatura do elemento {elemento} "
                f"({ameaca_nome or 'uma abominação'}) surge diante dos agentes da Ordo Realitas. {detalhes_extras}"
            )
            try:
                # Faz requisição direta se suportado pelo LLM client
                payload = {
                    "model": self.llm_client.model,
                    "messages": [
                        {"role": "system", "content": prompt_sistema_mestre},
                        {"role": "user", "content": prompt_usuario},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 256,
                }
                import urllib.request
                req = urllib.request.Request(
                    self.llm_client.chat_endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.llm_client.model}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    narracao = resp_data["choices"][0]["message"]["content"].strip()
                    self.historico_narrativo.append(narracao)
                    return narracao
            except Exception as e:
                logger.debug(f"LLM Mestre indisponível para narração ({e}). Usando gerador canônico.")

        # Fallback procedural
        narracao = (
            f"O ambiente se altera bruscamente {local_txt}. {base_desc} "
            f"A presença de {ameaca_nome or 'uma ameaça sombria'} estremece o campo de batalha. "
            f"{detalhes_extras}".strip()
        )
        self.historico_narrativo.append(narracao)
        return narracao

    def narrar_reviravolta(
        self,
        rodada: int,
        estado_combate: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Dispara uma reviravolta de horror cósmico durante o combate.
        Ex: Afinamento súbito da Membrana, distorção temporal, surto de luzes.
        """
        reviravolta = random.choice(REVIRAVOLTAS_CANONICAS)
        texto = f"[REVIRAVOLTA - RODADA {rodada}]: {reviravolta['narrativa']}"
        self.historico_narrativo.append(texto)
        logger.info(texto)
        return {"nome": reviravolta["nome"], "narrativa": texto, "efeito": reviravolta["efeito"]}

    # ========================================================================
    # PRESENÇA PERTURBADORA
    # ========================================================================

    def disparar_presenca_perturbadora(
        self,
        ameaca: AmeacaFicha,
        investigadores: List[AgenteFicha],
    ) -> Dict[str, Any]:
        """
        Dispara a Presença Perturbadora da criatura no início do encontro.
        Cada investigador faz um teste de Vontade (1d20 + perícia Vontade) contra a DT.
        Se falhar: sofre dano de Sanidade integral.
        Se passar: resiste (sofre metade do dano de Sanidade) e fica imune para esta cena.
        """
        if not ameaca.presenca_perturbadora:
            return {
                "ameaca": ameaca.nome,
                "disparado": False,
                "detalhes": f"{ameaca.nome} não possui Presença Perturbadora.",
                "resultados": [],
            }

        dt = ameaca.presenca_perturbadora.get("dt", 15)
        dano_mental_expr = ameaca.presenca_perturbadora.get("dano_mental", "1d6")

        resultados = []
        relato_linhas = [
            f"O impacto psíquico de contemplar {ameaca.nome} atinge os agentes em cheio! "
            f"(Presença Perturbadora - Teste de Vontade DT {dt})"
        ]

        for agente in investigadores:
            if agente.imune_presenca:
                resultados.append({
                    "agente_id": agente.token_id,
                    "agente_nome": agente.nome,
                    "resultado": "imune",
                    "rolagem": 0,
                    "dano_sanidade": 0,
                    "san_atual": agente.san_atual,
                })
                continue

            # Bônus de Vontade (se tiver Vontade em perícias, bônus +5; caso contrário +2)
            tem_vontade = any("vontade" in p.lower() for p in agente.pericias)
            bonus_vontade = 5 if tem_vontade else 2
            total_rolagem, d20_puro = rolar_d20(bonus=bonus_vontade)

            dano_fis, dano_san, detalhe = rolar_expressao_dano(dano_mental_expr)
            dano_total = dano_san if dano_san > 0 else dano_fis

            if total_rolagem >= dt:
                # Passou no teste: sofre metade do dano e ganha imunidade na cena
                dano_aplicado = max(0, dano_total // 2)
                agente.san_atual = max(0, agente.san_atual - dano_aplicado)
                agente.imune_presenca = True
                status_txt = f"{agente.nome} resistiu com firmeza mental (Rolou {total_rolagem} vs DT {dt}). Sofreu apenas {dano_aplicado} de dano de Sanidade e está imune."
                passou = True
            else:
                # Falhou no teste: sofre dano de Sanidade completo
                dano_aplicado = dano_total
                agente.san_atual = max(0, agente.san_atual - dano_aplicado)
                status_txt = f"{agente.nome} hesitou diante do terror incompreensível (Rolou {total_rolagem} vs DT {dt})! Sofreu {dano_aplicado} de dano de Sanidade ({detalhe})."
                passou = False

            # Atualiza status na Unreal HUD via Bridge
            self.bridge.update_character_status(
                token_id=agente.token_id,
                nome=agente.nome,
                classe=agente.classe,
                pv_atual=agente.pv_atual,
                pv_max=agente.pv_max,
                san_atual=agente.san_atual,
                san_max=agente.san_max,
                pe_atual=agente.pe_atual,
                pe_max=agente.pe_max,
            )

            resultados.append({
                "agente_id": agente.token_id,
                "agente_nome": agente.nome,
                "passou": passou,
                "rolagem": total_rolagem,
                "d20_puro": d20_puro,
                "dano_sanidade": dano_aplicado,
                "san_atual": agente.san_atual,
                "san_max": agente.san_max,
                "relato": status_txt,
            })
            relato_linhas.append(f"  • {status_txt}")

        relato_completo = "\n".join(relato_linhas)
        self.historico_narrativo.append(relato_completo)
        logger.info(f"[Presença Perturbadora]\n{relato_completo}")

        return {
            "ameaca": ameaca.nome,
            "disparado": True,
            "dt": dt,
            "dano_expr": dano_mental_expr,
            "relato": relato_completo,
            "resultados": resultados,
        }

    # ========================================================================
    # TÁTICA E GRID DO BATTLEMAT
    # ========================================================================

    @staticmethod
    def calcular_distancia_grid(pos1: str, pos2: str) -> int:
        """Calcula distância Chebyshev em quadrados de xadrez (ex: 'C3' até 'D5')."""
        if not pos1 or not pos2 or len(pos1) < 2 or len(pos2) < 2:
            return 99
        try:
            col1 = ord(pos1[0].upper()) - ord("A")
            row1 = int(pos1[1:]) - 1
            col2 = ord(pos2[0].upper()) - ord("A")
            row2 = int(pos2[1:]) - 1
            return max(abs(col1 - col2), abs(row1 - row2))
        except Exception:
            return 99

    @staticmethod
    def calcular_posicoes_adjacentes(grid: str, cols: int = 8, rows: int = 8) -> List[str]:
        """Retorna as coordenadas no grid adjacentes à célula dada."""
        if not grid or len(grid) < 2:
            return []
        col = ord(grid[0].upper()) - ord("A")
        row = int(grid[1:]) - 1

        adjacentes = []
        for dc in [-1, 0, 1]:
            for dr in [-1, 0, 1]:
                if dc == 0 and dr == 0:
                    continue
                nc = col + dc
                nr = row + dr
                if 0 <= nc < cols and 0 <= nr < rows:
                    letra = chr(ord("A") + nc)
                    numero = nr + 1
                    adjacentes.append(f"{letra}{numero}")
        return adjacentes

    def escolher_alvo(
        self,
        ameaca: AmeacaFicha,
        investigadores: List[AgenteFicha],
    ) -> Optional[AgenteFicha]:
        """
        IA Tática para seleção de alvo:
        - Prioriza alvo preferencial se configurado e vivo.
        - Criaturas de Sangue (Zumbi, Aberração, Cão): focam no alvo mais próximo ou com menos PV.
        - Criaturas de Conhecimento (O Existido, Estrangeiro): focam no alvo com menor Sanidade ou Ocultistas.
        - Criaturas de Energia (Anomalia, Telopsia): atacam alvos a alcance curto/médio.
        - Cultistas: atacam alvos com linha de tiro aberta ou coordenam fogo.
        """
        vivos = [a for a in investigadores if a.pv_atual > 0]
        if not vivos:
            return None

        # 1. Alvo preferencial
        if ameaca.alvo_preferencial_id:
            for a in vivos:
                if a.token_id == ameaca.alvo_preferencial_id:
                    return a

        # 2. Heurística pelo elemento
        if ameaca.elemento == "Conhecimento":
            # Foca em quem tem menor Sanidade
            return min(vivos, key=lambda a: (a.san_atual, self.calcular_distancia_grid(ameaca.grid, a.grid)))

        elif ameaca.elemento == "Sangue":
            # Foca no mais próximo; desempata pelo menor PV
            return min(vivos, key=lambda a: (self.calcular_distancia_grid(ameaca.grid, a.grid), a.pv_atual))

        elif ameaca.elemento == "Energia":
            # Prefere alvos a 2-4 quadrados de distância (curto alcance)
            def score_dist(a: AgenteFicha):
                dist = self.calcular_distancia_grid(ameaca.grid, a.grid)
                return abs(dist - 2)
            return min(vivos, key=score_dist)

        # Padrão: mais próximo
        return min(vivos, key=lambda a: self.calcular_distancia_grid(ameaca.grid, a.grid))

    def decidir_movimento(
        self,
        ameaca: AmeacaFicha,
        alvo: AgenteFicha,
        max_passos: int = 4,
    ) -> Tuple[str, float, float]:
        """
        Calcula o movimento da criatura em direção ao alvo.
        Criaturas corpo a corpo procuram parar adjacentes (distância 1).
        Criaturas de alcance procuram manter 2-3 quadrados de distância.
        Retorna (novo_grid, norm_x, norm_y).
        """
        origem = ameaca.grid
        col_orig = ord(origem[0].upper()) - ord("A")
        row_orig = int(origem[1:]) - 1

        col_alvo = ord(alvo.grid[0].upper()) - ord("A")
        row_alvo = int(alvo.grid[1:]) - 1

        dist_atual = max(abs(col_orig - col_alvo), abs(row_orig - row_alvo))

        # Se já estiver adjacente (dist == 1) e for criatura melee, não precisa andar
        eh_alcance = "alcance" in str(ameaca.ataques).lower()
        if not eh_alcance and dist_atual <= 1:
            return origem, ameaca.x, ameaca.y

        # Caminha passo a passo em direção ao alvo
        c_cur, r_cur = col_orig, row_orig
        passos_dados = 0

        dist_alvo_desejada = 2 if eh_alcance else 1

        while passos_dados < max_passos:
            dist = max(abs(c_cur - col_alvo), abs(r_cur - row_alvo))
            if dist <= dist_alvo_desejada:
                break

            step_c = 0
            step_r = 0
            if c_cur < col_alvo:
                step_c = 1
            elif c_cur > col_alvo:
                step_c = -1

            if r_cur < row_alvo:
                step_r = 1
            elif r_cur > row_alvo:
                step_r = -1

            c_cur = max(0, min(7, c_cur + step_c))
            r_cur = max(0, min(7, r_cur + step_r))
            passos_dados += 1

        novo_grid = f"{chr(ord('A') + c_cur)}{r_cur + 1}"
        norm_x, norm_y = self.bridge.grid_to_norm_coords(novo_grid)
        return novo_grid, norm_x, norm_y

    # ========================================================================
    # EXECUÇÃO DO TURNO DA AMEAÇA
    # ========================================================================

    def executar_turno_ameaca(
        self,
        token_id: int,
        agentes: Dict[int, AgenteFicha],
        outras_ameacas: Optional[List[AmeacaFicha]] = None,
    ) -> AmeacaAcaoResultado:
        """
        Executa a rodada completa de uma criatura/ameaça:
        1. Escolhe o alvo tático no battlemat.
        2. Move-se no grid e despacha comando UDP para a Unreal.
        3. Realiza o ataque canônico com bônus e rolagens de dano.
        4. Aciona habilidades especiais (Sede de Sangue, Agarrar, Lodo Temporal,
           Teletransporte Caótico, etc.).
        5. Atualiza HUDs e status na Unreal via Bridge.
        """
        ameaca = self.ameacas_ativas.get(token_id)
        if not ameaca:
            raise ValueError(f"Ameaça com token {token_id} não encontrada.")

        investigadores_vivos = [a for a in agentes.values() if a.pv_atual > 0]
        if not investigadores_vivos:
            return AmeacaAcaoResultado(
                ameaca_id=token_id,
                ameaca_nome=ameaca.nome,
                tipo_acao="passar",
                narrativa=f"{ameaca.nome} observa o cenário silencioso. Todos os investigadores estão caídos.",
            )

        # 1. Escolhe o alvo
        alvo = self.escolher_alvo(ameaca, investigadores_vivos)
        if not alvo:
            return AmeacaAcaoResultado(
                ameaca_id=token_id,
                ameaca_nome=ameaca.nome,
                tipo_acao="passar",
                narrativa=f"{ameaca.nome} rosna nas sombras sem alvos visíveis.",
            )

        # 2. Movimento
        grid_origem = ameaca.grid
        novo_grid, norm_x, norm_y = self.decidir_movimento(ameaca, alvo)
        teve_movimento = (novo_grid != grid_origem)

        if teve_movimento:
            ameaca.grid = novo_grid
            ameaca.x = norm_x
            ameaca.y = norm_y
            self.bridge.move_token_in_unreal(ameaca.token_id, "monstro", norm_x, norm_y)

        # 3. Escolhe o ataque principal
        ataques_disponiveis = ameaca.ataques or [
            {"nome": "Investida Sobrenatural", "teste": "+5", "dano": "1d8+3 Impacto"}
        ]
        ataque_info = ataques_disponiveis[0]

        # 4. Modificadores táticos
        mod_ataque = 0
        habilidades_ativadas = []

        # Habilidade: Matilha (Cão do Sangue) -> +2 no ataque para cada aliado adjacente ao mesmo alvo
        if "matilha" in ameaca.habilidade_especial.lower() and outras_ameacas:
            aliados_adjacentes = [
                m for m in outras_ameacas
                if m.token_id != ameaca.token_id and self.calcular_distancia_grid(m.grid, alvo.grid) <= 1
            ]
            if aliados_adjacentes:
                bonus_matilha = len(aliados_adjacentes) * 2
                mod_ataque += bonus_matilha
                habilidades_ativadas.append(f"Matilha (+{bonus_matilha} no ataque)")

        # Extrai bônus do teste da criatura (ex: "+5", "+10", "+14")
        teste_str = ataque_info.get("teste", "+5").replace("+", "").strip()
        bonus_base = int(teste_str) if teste_str.lstrip("-").isdigit() else 5
        bonus_total = bonus_base + mod_ataque

        # 5. Rola o teste de ataque
        rolagem_total, d20_puro = rolar_d20(bonus=bonus_total)
        acertou = (rolagem_total >= alvo.defesa) or (d20_puro == 20)

        dano_fisico = 0
        dano_mental = 0
        detalhes_dano = ""

        # 6. Processa Acerto e Habilidades Especiais
        if acertou:
            dano_expr = ataque_info.get("dano", "1d8+3")
            dano_fis, dano_men, detalhes_dano = rolar_expressao_dano(dano_expr)

            # Aplica RD do alvo se houver
            dano_fisico = max(0, dano_fis)
            dano_mental = max(0, dano_men)

            # Reduz recursos do alvo
            alvo.pv_atual = max(0, alvo.pv_atual - dano_fisico)
            if dano_mental > 0:
                alvo.san_atual = max(0, alvo.san_atual - dano_mental)

            # --- HABILIDADES ESPECIAIS AO ACERTAR ---

            # Sede de Sangue (Zumbi de Sangue): cura 5 PV se causar dano
            if "sede de sangue" in ameaca.habilidade_especial.lower() and dano_fisico > 0:
                cura = 5
                ameaca.pv_atual = min(ameaca.pv_max, ameaca.pv_atual + cura)
                habilidades_ativadas.append(f"Sede de Sangue (Curou {cura} PV)")

            # Agarrar Aprimorado (Aberração de Carne)
            if "agarrar" in ameaca.habilidade_especial.lower() or "agarrar" in ataque_info["nome"].lower():
                if "Agarrado" not in alvo.condicoes:
                    alvo.condicoes.append("Agarrado")
                    habilidades_ativadas.append(f"Agarrar Aprimorado ({alvo.nome} ficou Agarrado)")

            # Lodo Temporal (Esqueleto de Lodo)
            if "lodo temporal" in ameaca.habilidade_especial.lower() or "lento" in ataque_info.get("dano", "").lower():
                if "Lento" not in alvo.condicoes:
                    alvo.condicoes.append("Lento")
                    habilidades_ativadas.append(f"Lodo Temporal ({alvo.nome} com deslocamento reduzido pela metade)")

            # Toque do Esquecimento (O Existido)
            if "esquecimento" in ataque_info["nome"].lower() or "esquecimento" in ameaca.habilidade_especial.lower():
                habilidades_ativadas.append("Toque do Esquecimento (Memórias fragmentadas pela Membrana)")

            # Estática Ensurdecedora (Telopsia)
            if "estática ensurdecedora" in ameaca.habilidade_especial.lower():
                # Alvos a alcance curto fazem teste de Vontade DT 22
                for outro_agente in investigadores_vivos:
                    if self.calcular_distancia_grid(ameaca.grid, outro_agente.grid) <= 6:
                        v_roll, _ = rolar_d20(bonus=5 if "Vontade" in outro_agente.pericias else 2)
                        if v_roll < 22:
                            if "Atordoado" not in outro_agente.condicoes:
                                outro_agente.condicoes.append("Atordoado")
                                habilidades_ativadas.append(f"Estática Ensurdecedora ({outro_agente.nome} Atordoado)")

            # Atualiza HUD do alvo na Unreal Engine
            self.bridge.update_character_status(
                token_id=alvo.token_id,
                nome=alvo.nome,
                classe=alvo.classe,
                pv_atual=alvo.pv_atual,
                pv_max=alvo.pv_max,
                san_atual=alvo.san_atual,
                san_max=alvo.san_max,
                pe_atual=alvo.pe_atual,
                pe_max=alvo.pe_max,
            )

        # Teletransporte Caótico (Anomalia Elétrica): move-se até 9m livremente após atacar
        if "teletransporte caótico" in ameaca.habilidade_especial.lower():
            # Teleporta para um quadrado adjacente distante ou posição tática alternativa
            coords_teleporte = ["B2", "F2", "D6", "C5", "E3"]
            novo_teleporte = random.choice([c for c in coords_teleporte if c != ameaca.grid])
            ameaca.grid = novo_teleporte
            norm_tx, norm_ty = self.bridge.grid_to_norm_coords(novo_teleporte)
            ameaca.x = norm_tx
            ameaca.y = norm_ty
            self.bridge.move_token_in_unreal(ameaca.token_id, "monstro", norm_tx, norm_ty)
            habilidades_ativadas.append(f"Teletransporte Caótico (Deslocou-se instantaneamente para {novo_teleporte})")

        # 7. Gera narrativa de combate
        mov_txt = f"Avança de [{grid_origem}] para [{ameaca.grid}]. " if teve_movimento else ""
        if acertou:
            dmg_txt = f"{dano_fisico} de dano físico"
            if dano_mental > 0:
                dmg_txt += f" e {dano_mental} de dano mental"
            hab_txt = f" [{'; '.join(habilidades_ativadas)}]" if habilidades_ativadas else ""
            narrativa = (
                f"{ameaca.nome} ataca {alvo.nome}! {mov_txt}"
                f"Usa {ataque_info['nome']} (Rolagem: {rolagem_total} vs Defesa {alvo.defesa} - ACERTO!). "
                f"Causa {dmg_txt} ({detalhes_dano}).{hab_txt}"
            )
        else:
            narrativa = (
                f"{ameaca.nome} investe contra {alvo.nome}! {mov_txt}"
                f"Desfere {ataque_info['nome']} (Rolagem: {rolagem_total} vs Defesa {alvo.defesa} - ERROU!). "
                f"{alvo.nome} consegue se esquivar no último instante."
            )

        self.historico_narrativo.append(narrativa)
        logger.info(f"[Turno Ameaça] {narrativa}")

        return AmeacaAcaoResultado(
            ameaca_id=ameaca.token_id,
            ameaca_nome=ameaca.nome,
            tipo_acao="ataque",
            alvo_id=alvo.token_id,
            alvo_nome=alvo.nome,
            ataque_nome=ataque_info["nome"],
            rolagem_ataque=rolagem_total,
            d20_puro=d20_puro,
            acertou=acertou,
            dano_fisico=dano_fisico,
            dano_mental=dano_mental,
            detalhes_dano=detalhes_dano,
            habilidades_ativadas=habilidades_ativadas,
            movimento_origem=grid_origem if teve_movimento else None,
            movimento_destino=ameaca.grid if teve_movimento else None,
            narrativa=narrativa,
        )
