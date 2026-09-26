"""Esquemas de dados para as decisões e estado dos Agentes de Ordem Paranormal."""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class MovimentoAcao(BaseModel):
    destino_grid: Optional[str] = Field(None, description="Coordenada no grid de xadrez (ex: 'C4', 'D2')")
    x: Optional[float] = Field(None, description="Coordenada normalizada X (0.0 a 1.0)")
    y: Optional[float] = Field(None, description="Coordenada normalizada Y (0.0 a 1.0)")
    descricao: Optional[str] = Field(None, description="Como o personagem se move (ex: 'Avanço buscando cobertura na mureta')")


class AcaoPadrao(BaseModel):
    tipo: str = Field(
        "ataque", description="Tipo de ação padrão realizada no turno (ataque, ritual, pericia, manobra, esquiva, ajuda)"
    )
    alvo_id: Optional[int] = Field(None, description="ID do token do alvo (ex: 11 para Zumbi de Sangue)")
    alvo_nome: Optional[str] = Field(None, description="Nome do alvo visado")

    # Detalhes de Ataque e Habilidade
    arma: Optional[str] = Field(None, description="Nome da arma empunhada (ex: 'Espingarda', 'Katana', 'Revólver')")
    habilidade_classe: Optional[str] = Field(None, description="Habilidade usada (ex: 'Ataque Especial', 'Ataque Furtivo', 'Paramédico')")
    manobra: Optional[str] = Field(None, description="Manobra de combate (ex: 'derrubar', 'desarmar', 'agarrar')")

    # Detalhes de Ritual Canônico v1.3
    ritual: Optional[str] = Field(None, description="Nome do ritual (ex: 'Decadência', 'Cicatrizante', 'Eletrocussão')")
    forma_ritual: Optional[str] = Field("padrao", description="Forma de conjuração: 'padrao', 'discente' (+2 PE), 'verdadeiro' (+5 PE)")
    elemento: Optional[Literal["Sangue", "Morte", "Energia", "Conhecimento", "Medo"]] = Field(
        None, description="Elemento paranormal do ritual"
    )
    custo_pe: Optional[int] = Field(0, description="Custo total de Pontos de Esforço")

    # Detalhes de Perícia
    pericia: Optional[str] = Field(None, description="Perícia utilizada (ex: 'Pontaria', 'Ocultismo', 'Medicina', 'Luta')")
    reacao_preparada: Optional[str] = Field(None, description="Reação tática preparada (ex: 'esquiva', 'bloqueio', 'contra-ataque')")

    @classmethod
    def from_dict_flexible(cls, data: Any):
        if not isinstance(data, dict):
            return cls(tipo="passar")
        tipo = data.get("tipo") or data.get("acao") or "ataque"
        alvo_nome = data.get("alvo_nome") or data.get("alvo")
        alvo_id = data.get("alvo_id")
        return cls(
            tipo=str(tipo).lower(),
            alvo_id=alvo_id,
            alvo_nome=str(alvo_nome) if alvo_nome else None,
            arma=data.get("arma"),
            habilidade_classe=data.get("habilidade_classe") or data.get("habilidade"),
            manobra=data.get("manobra"),
            ritual=data.get("ritual"),
            forma_ritual=data.get("forma_ritual") or "padrao",
            elemento=data.get("elemento"),
            custo_pe=int(data.get("custo_pe", 0) or 0),
            pericia=data.get("pericia"),
            reacao_preparada=data.get("reacao_preparada") or data.get("reacao"),
        )


class TurnoDecisao(BaseModel):
    """Schema estrito de saída que o LLM DEVE produzir a cada turno."""
    pensamento: str = Field(
        ..., description="Monólogo interno tático do agente ou delírio de sanidade baixa."
    )
    fala: str = Field(
        ..., description="Fala em voz alta na cena para os aliados ou monstros (Roleplay)."
    )
    movimento: Optional[MovimentoAcao] = Field(
        None, description="Ação de Movimento no grid do battlemat."
    )
    acao_padrao: AcaoPadrao = Field(
        ..., description="Ação Padrão mecânica executada na rodada."
    )
    acao_livre: Optional[str] = Field(
        None, description="Ação livre adicional (ex: largar lanterna, recarregar rápido)."
    )

    @classmethod
    def from_dict_flexible(cls, data: Dict[str, Any]):
        if not isinstance(data, dict):
            return cls(pensamento="Agindo...", fala="Cuidado!", acao_padrao=AcaoPadrao(tipo="passar"))

        # Normaliza movimento se for string simples
        mov = data.get("movimento")
        if isinstance(mov, str):
            mov = {"destino_grid": mov}

        # Normaliza acao_padrao
        ap = data.get("acao_padrao") or {}
        if isinstance(ap, dict):
            ap_obj = AcaoPadrao.from_dict_flexible(ap)
        else:
            ap_obj = AcaoPadrao(tipo="passar")

        return cls(
            pensamento=str(data.get("pensamento", "Analisando a situação...")),
            fala=str(data.get("fala", "Vamos em frente!")),
            movimento=mov,
            acao_padrao=ap_obj,
            acao_livre=data.get("acao_livre"),
        )


class AgenteFicha(BaseModel):
    """Estado em memória do personagem conectado ao battlemat."""
    token_id: int
    nome: str
    classe: Literal["Combatente", "Especialista", "Ocultista"]
    trilha: str
    nex: int = 10
    
    # Recursos Vitais
    pv_atual: int
    pv_max: int
    san_atual: int
    san_max: int
    pe_atual: int
    pe_max: int
    
    # Defesa e Deslocamento
    defesa: int = 15
    deslocamento_m: float = 9.0  # metros por turno (1 quadrado = 1.5m)
    
    # Posição atual no Battlemat
    x: float = 0.5
    y: float = 0.5
    grid: str = "D4"
    
    # Personalidade e Armamento
    personalidade: str = "Tático e cauteloso."
    armas: List[str] = ["Revólver", "Faca"]
    habilidades: List[str] = []
    pericias: List[str] = []
    rituais: List[Dict[str, Any]] = []
    condicoes: List[str] = Field(default_factory=list)
    imune_presenca: bool = False


class AmeacaFicha(BaseModel):
    """Estado em memória da criatura ou monstro paranormal no Battlemat."""
    token_id: int
    nome: str
    elemento: str
    vd: int
    tamanho: str = "Médio"
    pv_atual: int
    pv_max: int
    defesa: int
    rd: Dict[str, int] = Field(default_factory=dict)
    vulnerabilidade: str = "Nenhuma"
    presenca_perturbadora: Optional[Dict[str, Any]] = None
    ataques: List[Dict[str, Any]] = Field(default_factory=list)
    habilidade_especial: str = ""
    grid: str = "D5"
    x: float = 0.5
    y: float = 0.5
    deslocamento_m: float = 9.0
    condicoes: List[str] = Field(default_factory=list)
    alvo_preferencial_id: Optional[int] = None


class AmeacaAcaoResultado(BaseModel):
    """Resultado detalhado do turno de uma criatura/ameaça executado pelo Mestre IA."""
    ameaca_id: int
    ameaca_nome: str
    tipo_acao: str = "ataque"
    alvo_id: Optional[int] = None
    alvo_nome: Optional[str] = None
    ataque_nome: Optional[str] = None
    rolagem_ataque: int = 0
    d20_puro: int = 0
    acertou: bool = False
    dano_fisico: int = 0
    dano_mental: int = 0
    detalhes_dano: str = ""
    habilidades_ativadas: List[str] = Field(default_factory=list)
    movimento_origem: Optional[str] = None
    movimento_destino: Optional[str] = None
    narrativa: str = ""

