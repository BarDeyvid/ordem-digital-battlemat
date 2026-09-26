"""Orquestrador do Loop de Jogo: gerencia turnos dos agentes LLM, regras e despacho para o Battlemat."""

import logging
import random
from typing import List, Dict, Any, Optional

from ai_agents.schemas import AgenteFicha, TurnoDecisao, AcaoPadrao, MovimentoAcao, AmeacaFicha, AmeacaAcaoResultado
from ai_agents.llm_client import LocalLLMClient
from ai_agents.prompt_builder import build_system_prompt, build_turn_prompt
from ai_agents.battlemat_bridge import BattlematBridgeClient
from ai_agents.session_logger import SessionDatasetRecorder
from ai_agents.voice_elevenlabs import ElevenLabsVoiceManager, voice_manager as default_voice_manager
from ai_agents.game_master import OrdoGameMaster, rolar_d20, rolar_expressao_dano

logger = logging.getLogger("ai_agents.orchestrator")

# Tabela canônica de dano de armas da Ordem Paranormal
WEAPON_DAMAGE_MAP: Dict[str, str] = {
    "Espingarda": "4d6 Balístico",
    "Revólver": "2d6 Balístico",
    "Submetralhadora": "2d6 Balístico",
    "Machado": "1d8+3 Corte",
    "Katana": "1d10+3 Corte",
    "Faca de Ritual": "1d4+2 Perfuração",
    "Pistola": "1d12 Balístico",
    "Revólver Magnum": "2d8 Balístico",
    "Escopeta": "3d6 Balístico",
    "Adaga": "1d4+1 Perfuração",
    "Faca": "1d4 Perfuração",
    "Shuriken": "1d4+1 Perfuração",
    "Rapieira": "1d8+2 Perfuração",
    "Granada de Fragmentação": "4d6 Impacto",
}




class AgenteGameOrchestrator:
    """Gerencia a iniciativa, requisições aos agentes e atualização do Battlemat."""

    def __init__(
        self,
        llm_client: LocalLLMClient = None,
        voice_manager: ElevenLabsVoiceManager = None,
        game_master: OrdoGameMaster = None,
        player_token_id: Optional[int] = None,
    ):
        self.llm_client = llm_client or LocalLLMClient()
        self.bridge = BattlematBridgeClient()
        self.dataset_recorder = SessionDatasetRecorder()
        self.voice_manager = voice_manager or default_voice_manager
        self.game_master = game_master or OrdoGameMaster(llm_client=self.llm_client, bridge=self.bridge)
        self.player_token_id = player_token_id

        # Personagens Padrão da Equipe da Ordem (8 Protagonistas)
        self.agentes: Dict[int, AgenteFicha] = {
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
                personalidade="Protetor da equipe, direto, prefere resolver na força bruta.",
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
                personalidade="Metódico, técnico, prefere atacar à distância sob cobertura.",
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
                personalidade="Místico, calmo por fora mas atormentado pelo Outro Lado.",
                armas=["Faca de Ritual"],
                rituais=[
                    {"nome": "Decadência", "elemento": "Morte", "custo_pe": 1, "alcance": "Curto"},
                    {"nome": "Cicatrizante", "elemento": "Sangue", "custo_pe": 1, "alcance": "Toque"},
                    {"nome": "Eletrocussão", "elemento": "Energia", "custo_pe": 1, "alcance": "Curto"},
                ],
            ),
            4: AgenteFicha(
                token_id=4,
                nome="Joui Jouki",
                classe="Combatente",
                trilha="Guerreiro",
                nex=20,
                pv_atual=26,
                pv_max=30,
                san_atual=16,
                san_max=20,
                pe_atual=8,
                pe_max=12,
                defesa=16,
                grid="C2",
                personalidade="Honrado, leal aos amigos, focado no combate corpo a corpo justo.",
                armas=["Katana"],
            ),
            5: AgenteFicha(
                token_id=5,
                nome="Liz Sena",
                classe="Especialista",
                trilha="Médica de Campo",
                nex=20,
                pv_atual=18,
                pv_max=20,
                san_atual=20,
                san_max=26,
                pe_atual=14,
                pe_max=18,
                defesa=14,
                grid="B2",
                personalidade="Científica, empática, busca salvar vidas e compreender o paranormal racionalmente.",
                armas=["Pistola", "Kit Médico"],
            ),
            6: AgenteFicha(
                token_id=6,
                nome="Thiago Fritz",
                classe="Combatente",
                trilha="Comandante de Campo",
                nex=20,
                pv_atual=24,
                pv_max=28,
                san_atual=15,
                san_max=22,
                pe_atual=10,
                pe_max=14,
                defesa=16,
                grid="C1",
                personalidade="Líder experiente, firme, estrategista que prioriza a sobrevivência de todos.",
                armas=["Revólver Magnum"],
            ),
            7: AgenteFicha(
                token_id=7,
                nome="Rubens Naluti",
                classe="Especialista",
                trilha="Técnico",
                nex=20,
                pv_atual=22,
                pv_max=24,
                san_atual=14,
                san_max=22,
                pe_atual=11,
                pe_max=15,
                defesa=15,
                grid="A3",
                personalidade="Prático, pragmático, direto ao ponto e focado na eficácia mecânica.",
                armas=["Espingarda Curta"],
            ),
            8: AgenteFicha(
                token_id=8,
                nome="Milo Foster",
                classe="Ocultista",
                trilha="Intuitivo",
                nex=20,
                pv_atual=15,
                pv_max=18,
                san_atual=11,
                san_max=24,
                pe_atual=16,
                pe_max=20,
                defesa=13,
                grid="A1",
                personalidade="Excêntrico, impulsivo, fascinado pelos mistérios do Outro Lado.",
                armas=["Adaga"],
                rituais=[
                    {"nome": "Terceiro Olho", "elemento": "Conhecimento", "custo_pe": 1, "alcance": "Pessoal"},
                ],
            ),
        }

        # Inicializa a ameaça padrão no Game Master se não houver nenhuma
        if not self.game_master.ameacas_ativas:
            self.game_master.criar_ameaca("Zumbi de Sangue", token_id=11, grid="D5")
        self.ameacas: List[Dict[str, Any]] = []
        self._sincronizar_ameacas_legado()

    def _sincronizar_ameacas_legado(self):
        """Mantém a lista `self.ameacas` sincronizada com `self.game_master.ameacas_ativas` para o prompt builder."""
        self.ameacas = []
        for m in self.game_master.ameacas_ativas.values():
            dist = self.game_master.calcular_distancia_grid(m.grid, "C3")
            self.ameacas.append({
                "id": m.token_id,
                "name": m.nome,
                "tipo": f"{m.elemento} (VD {m.vd})",
                "grid": m.grid,
                "distancia": f"{dist} quadrados ({'Curta' if dist <= 2 else 'Média'})",
                "pv": m.pv_atual,
            })


    def rolar_d20(self, bonus: int = 5) -> int:
        """Simula a rolagem de dados físicas do sistema d20 de Ordem."""
        dado = random.randint(1, 20)
        return dado + bonus

    def narrar_mestre(self, texto: str, async_play: bool = True):
        """Sintetiza e reproduz a narração de suspense d'O Mestre da Ordem."""
        return self.voice_manager.speak(
            text=texto,
            speaker_name="O Mestre",
            async_play=async_play,
        )

    def executar_turno_agente(
        self,
        token_id: int,
        narrativa_mestre: str = "",
        narrar_mestre_agora: bool = False,
    ) -> TurnoDecisao:
        """Executa a rodada completa de um agente individual."""
        agente = self.agentes.get(token_id)
        if not agente:
            raise ValueError(f"Agente com Token ID {token_id} não encontrado.")

        # 0. Narração do Mestre da Ordem (se solicitada)
        if narrativa_mestre and narrar_mestre_agora:
            self.narrar_mestre(narrativa_mestre, async_play=True)

        # 1. Monta os prompts
        system_prompt = build_system_prompt(agente)
        aliados_list = [
            {"id": a.token_id, "name": a.nome, "classe": a.classe, "grid": a.grid}
            for a in self.agentes.values()
        ]
        user_prompt = build_turn_prompt(
            agente=agente,
            ameacas=self.ameacas,
            aliados=aliados_list,
            narrativa_mestre=narrativa_mestre,
        )

        # 2. Requisita a decisão do LLM
        decisao = self.llm_client.request_turn_decision(system_prompt, user_prompt)

        # 3. Processa Movimento no Battlemat (Unreal Engine)
        if decisao.movimento and decisao.movimento.destino_grid:
            novo_grid = decisao.movimento.destino_grid
            norm_x, norm_y = self.bridge.grid_to_norm_coords(novo_grid)
            agente.grid = novo_grid
            agente.x = norm_x
            agente.y = norm_y
            self.bridge.move_token_in_unreal(agente.token_id, "investigador", norm_x, norm_y)

        # 4. Processa Ação Padrão (Ataque, Ritual, etc.)
        acao = decisao.acao_padrao
        if acao.tipo == "ritual" and acao.ritual:
            custo = acao.custo_pe or 1
            if agente.pe_atual >= custo:
                agente.pe_atual -= custo
                elemento = acao.elemento or "Morte"
                self.bridge.cast_ritual_vfx(
                    token_id=agente.token_id,
                    ritual=acao.ritual,
                    elemento=elemento,
                    custo_pe=custo,
                )
            else:
                logger.warning(f"{agente.nome} tentou conjurar sem PE suficiente!")

        elif acao.tipo == "ataque":
            resultado_ataque = self.rolar_d20(bonus=5)
            logger.info(f"[Combate] {agente.nome} atacou com {acao.arma}: Tirou {resultado_ataque} no teste!")

        # 5. Atualiza HUD / Barras no Battlemat
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

        # 6. Grava automaticamente no Dataset de Fine-Tuning do Unsloth
        self.dataset_recorder.record_turn(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            assistant_decision=decisao.model_dump(),
            metadata={"token_id": token_id, "agente": agente.nome, "classe": agente.classe},
        )

        # 7. Dispara a voz do agente via ElevenLabs com cache em disco e áudio assíncrono
        if decisao.fala:
            self.voice_manager.speak(
                text=decisao.fala,
                speaker_name=agente.nome,
                async_play=True,
            )

        return decisao

    def iniciar_combate(
        self,
        nome_ameaca: str = "Zumbi de Sangue",
        grid_ameaca: str = "D5",
        ambiente: Optional[str] = None,
        narrar_voz: bool = True,
    ) -> Dict[str, Any]:
        """Inicia um confronto tático: cria a ameaça, narra a abertura e dispara Presença Perturbadora."""
        ameaca = self.game_master.criar_ameaca(nome=nome_ameaca, token_id=11, grid=grid_ameaca)
        self._sincronizar_ameacas_legado()

        abertura = self.game_master.narrar_abertura_cena(ambiente_nome=ambiente, ameaca_nome=nome_ameaca)
        if narrar_voz:
            self.narrar_mestre(abertura, async_play=True)

        presenca = self.game_master.disparar_presenca_perturbadora(ameaca, list(self.agentes.values()))

        return {
            "narrativa_abertura": abertura,
            "presenca_perturbadora": presenca,
            "ameaca": ameaca,
        }

    def executar_turno_player(
        self,
        token_id: int,
        acao: AcaoPadrao,
        movimento: Optional[MovimentoAcao] = None,
    ) -> Dict[str, Any]:
        """
        Executa a ação de um Jogador Humano solo na mesa.
        Permite que o usuário se mova no grid, ataque criaturas ou conjure rituais.
        """
        player = self.agentes.get(token_id)
        if not player:
            raise ValueError(f"Personagem do jogador com Token ID {token_id} não encontrado.")

        resultado: Dict[str, Any] = {
            "token_id": token_id,
            "nome": player.nome,
            "movimento": None,
            "acao": None,
            "relato": "",
        }

        # 1. Movimento do Jogador no Battlemat
        if movimento and movimento.destino_grid:
            novo_grid = movimento.destino_grid
            norm_x, norm_y = self.bridge.grid_to_norm_coords(novo_grid)
            grid_antigo = player.grid
            player.grid = novo_grid
            player.x = norm_x
            player.y = norm_y
            self.bridge.move_token_in_unreal(player.token_id, "investigador", norm_x, norm_y)
            resultado["movimento"] = {"origem": grid_antigo, "destino": novo_grid}
            logger.info(f"[Player Move] {player.nome} moveu-se de {grid_antigo} para {novo_grid}")

        # 2. Ação Padrão (Ataque, Ritual, Perícia, etc.)
        if acao.tipo == "ataque":
            tem_treinamento = any(p.lower() in ["pontaria", "luta", "pontaria."] for p in player.pericias)
            bonus_ataque = 5 if tem_treinamento else 2
            roll_total, d20_puro = rolar_d20(bonus=bonus_ataque)

            # Localiza a criatura visada
            alvo_ameaca = None
            if acao.alvo_id and acao.alvo_id in self.game_master.ameacas_ativas:
                alvo_ameaca = self.game_master.ameacas_ativas[acao.alvo_id]
            elif self.game_master.ameacas_ativas:
                alvo_ameaca = list(self.game_master.ameacas_ativas.values())[0]

            if not alvo_ameaca:
                resultado["acao"] = {"tipo": "ataque", "sucesso": False, "mensagem": "Nenhum alvo na mira."}
                return resultado

            acertou = (roll_total >= alvo_ameaca.defesa) or (d20_puro == 20)

            if acertou:
                arma = acao.arma or (player.armas[0] if player.armas else "Revólver")
                dano_fisico, dano_mental, detalhe = rolar_expressao_dano(
                    WEAPON_DAMAGE_MAP.get(arma, "2d6 Balístico")
                )

                # Aplica RD do monstro se houver
                tipo_arma = "Balístico" if any(w in arma.lower() for w in ["esp", "rev", "pist", "sub"]) else "Corte"
                rd_val = alvo_ameaca.rd.get(tipo_arma, 0)
                dano_final = max(1, dano_fisico - rd_val)
                alvo_ameaca.pv_atual = max(0, alvo_ameaca.pv_atual - dano_final)

                relato_ataque = (
                    f"{player.nome} atacou {alvo_ameaca.nome} com {arma}! "
                    f"Rolagem: {roll_total} vs Defesa {alvo_ameaca.defesa} (Acertou!). "
                    f"Causou {dano_final} de dano ({detalhe})! "
                    f"{alvo_ameaca.nome} agora está com {alvo_ameaca.pv_atual}/{alvo_ameaca.pv_max} PV."
                )

                # Verifica morte e habilidades reativas do monstro (ex: Mártir do Fanático)
                if alvo_ameaca.pv_atual == 0:
                    relato_ataque += f" **{alvo_ameaca.nome} foi neutralizado!**"
                    if "mártir" in alvo_ameaca.habilidade_especial.lower():
                        d_exp, _, _ = rolar_expressao_dano("2d6")
                        relato_ataque += f" [Mártir ativado: o corpo explode em lodo causando {d_exp} de dano aos adjacentes!]"
                        for ag in self.agentes.values():
                            if self.game_master.calcular_distancia_grid(alvo_ameaca.grid, ag.grid) <= 1:
                                ag.pv_atual = max(0, ag.pv_atual - d_exp)

                resultado["acao"] = {
                    "tipo": "ataque",
                    "acertou": True,
                    "arma": arma,
                    "rolagem": roll_total,
                    "dano": dano_final,
                    "alvo": alvo_ameaca.nome,
                    "alvo_pv": alvo_ameaca.pv_atual,
                }
            else:
                relato_ataque = (
                    f"{player.nome} atacou {alvo_ameaca.nome} com {acao.arma or 'Arma'}, "
                    f"mas errou o golpe (Tirou {roll_total} vs Defesa {alvo_ameaca.defesa})."
                )
                if "sussurros da membrana" in alvo_ameaca.habilidade_especial.lower():
                    player.san_atual = max(0, player.san_atual - 1)
                    relato_ataque += f" [Sussurros da Membrana: Ao errar o ataque contra {alvo_ameaca.nome}, {player.nome} perdeu 1 de Sanidade!]"

                resultado["acao"] = {
                    "tipo": "ataque",
                    "acertou": False,
                    "rolagem": roll_total,
                    "alvo": alvo_ameaca.nome,
                }

            resultado["relato"] = relato_ataque
            logger.info(f"[Player Ação] {relato_ataque}")

        elif acao.tipo == "ritual" and acao.ritual:
            custo = acao.custo_pe or 1
            if player.pe_atual >= custo:
                player.pe_atual -= custo
                elem = acao.elemento or "Morte"
                self.bridge.cast_ritual_vfx(player.token_id, acao.ritual, elem, custo_pe=custo)

                if "cicatrizante" in acao.ritual.lower():
                    cura, _, _ = rolar_expressao_dano("2d8+2")
                    player.pv_atual = min(player.pv_max, player.pv_atual + cura)
                    relato = f"{player.nome} conjurou Cicatrizante ({elem}) e curou {cura} PV! (PV: {player.pv_atual}/{player.pv_max})"
                else:
                    dano, _, _ = rolar_expressao_dano("2d8+2")
                    if self.game_master.ameacas_ativas:
                        alvo_m = list(self.game_master.ameacas_ativas.values())[0]
                        alvo_m.pv_atual = max(0, alvo_m.pv_atual - dano)
                        relato = f"{player.nome} conjurou {acao.ritual} ({elem}) contra {alvo_m.nome}, causando {dano} de dano! (PV Alvo: {alvo_m.pv_atual}/{alvo_m.pv_max})"
                    else:
                        relato = f"{player.nome} conjurou {acao.ritual} ({elem}) no ar."

                resultado["acao"] = {"tipo": "ritual", "ritual": acao.ritual, "pe_gasto": custo}
                resultado["relato"] = relato
            else:
                resultado["acao"] = {"tipo": "ritual", "sucesso": False, "mensagem": "PE insuficiente."}
                resultado["relato"] = f"{player.nome} tentou conjurar {acao.ritual}, mas não tinha PE suficiente!"

        else:
            resultado["acao"] = {"tipo": acao.tipo}
            resultado["relato"] = f"{player.nome} realizou a ação: {acao.tipo}."

        # Sincroniza status do Player no Battlemat
        self.bridge.update_character_status(
            token_id=player.token_id,
            nome=player.nome,
            classe=player.classe,
            pv_atual=player.pv_atual,
            pv_max=player.pv_max,
            san_atual=player.san_atual,
            san_max=player.san_max,
            pe_atual=player.pe_atual,
            pe_max=player.pe_max,
        )

        self._sincronizar_ameacas_legado()
        return resultado

    def executar_turno_ameaca(self, token_id: int = 11) -> AmeacaAcaoResultado:
        """Executa a vez de uma criatura através do Mestre de Jogo IA."""
        resultado = self.game_master.executar_turno_ameaca(
            token_id=token_id,
            agentes=self.agentes,
            outras_ameacas=list(self.game_master.ameacas_ativas.values()),
        )
        self._sincronizar_ameacas_legado()
        return resultado

    def executar_rodada_completa(
        self,
        acao_player: Optional[AcaoPadrao] = None,
        mov_player: Optional[MovimentoAcao] = None,
        narrativa_mestre: str = "",
    ) -> Dict[str, Any]:
        """
        Executa uma rodada tática completa:
        1. Turno do Player (se houver player_token_id e ação fornecida)
        2. Turno dos Agentes IA aliados (companheiros controlados por LLM)
        3. Turno das Ameaças (controladas pelo OrdoGameMaster)
        4. Checagem de reviravolta de horror cósmico ao fim da rodada
        """
        rodada_atual = self.game_master.rodada_atual
        relatorio_rodada: Dict[str, Any] = {
            "rodada": rodada_atual,
            "player": None,
            "aliados": [],
            "ameacas": [],
            "reviravolta": None,
        }

        # 1. Turno do Jogador Solo
        if self.player_token_id and self.player_token_id in self.agentes:
            player = self.agentes[self.player_token_id]
            if player.pv_atual > 0 and acao_player:
                res_player = self.executar_turno_player(self.player_token_id, acao_player, mov_player)
                relatorio_rodada["player"] = res_player

        # 2. Turno dos Aliados IA (Companion Agents)
        for token_id, agente in self.agentes.items():
            if self.player_token_id and token_id == self.player_token_id:
                continue  # Pula o jogador humano
            if agente.pv_atual <= 0:
                continue  # Inconsciente ou morto

            decisao_ia = self.executar_turno_agente(
                token_id=token_id,
                narrativa_mestre=narrativa_mestre,
            )
            relatorio_rodada["aliados"].append({
                "token_id": token_id,
                "nome": agente.nome,
                "decisao": decisao_ia,
            })

        # 3. Turno das Ameaças
        for ameaca_id, ameaca in list(self.game_master.ameacas_ativas.items()):
            if ameaca.pv_atual > 0:
                res_ameaca = self.executar_turno_ameaca(ameaca_id)
                relatorio_rodada["ameacas"].append(res_ameaca)

        # 4. Reviravolta de Horror Cósmico (a partir da rodada 2 ou por afinamento da Membrana)
        if rodada_atual >= 2 or any(a.san_atual <= 5 for a in self.agentes.values()):
            reviravolta = self.game_master.narrar_reviravolta(rodada_atual)
            relatorio_rodada["reviravolta"] = reviravolta
            self.narrar_mestre(reviravolta["narrativa"], async_play=True)

        self.game_master.rodada_atual += 1
        return relatorio_rodada

