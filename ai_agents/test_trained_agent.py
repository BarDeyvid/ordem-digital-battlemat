"""Script para testar o modelo com o Adaptador LoRA treinado de Ordem Paranormal."""

import os
from pathlib import Path
from unsloth import FastLanguageModel
from ai_agents.prompt_builder import build_system_prompt, build_turn_prompt
from ai_agents.schemas import AgenteFicha

BASE_DIR = Path(__file__).resolve().parent
LORA_DIR = BASE_DIR / "lora_ordem_agents"

def test_inference():
    print("=" * 65)
    print("  CARREGANDO MODELO COM ADAPTADOR LoRA TREINADO")
    print(f"  Diretório: {LORA_DIR}")
    print("=" * 65)

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(LORA_DIR),
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)

    # Cria uma situação de teste: Dante com Sanidade Baixa enfrentando uma Anomalia Elétrica
    dante = AgenteFicha(
        token_id=3,
        nome="Dante",
        classe="Ocultista",
        trilha="Graduado",
        nex=20,
        pv_atual=12,
        pv_max=16,
        san_atual=4,  # Sanidade crítica
        san_max=22,
        pe_atual=8,
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
    )

    ameacas = [{
        "id": 13,
        "name": "Anomalia Elétrica",
        "tipo": "Criatura de Energia (VD 20)",
        "grid": "D3",
        "distancia": "Curta (2 quadrados)",
    }]

    aliados = [
        {"id": 1, "name": "Arthur Cervero", "classe": "Combatente", "grid": "C3"},
        {"id": 2, "name": "Kaiser", "classe": "Especialista", "grid": "A2"},
    ]

    system_prompt = build_system_prompt(dante)
    user_prompt = build_turn_prompt(
        agente=dante,
        ameacas=ameacas,
        aliados=aliados,
        narrativa_mestre="O chão vibra e relâmpagos roxos rompem o teto do laboratório!",
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
    ).to("cuda")

    print("\n[Gerando Ação com o Modelo Treinado...]\n")
    outputs = model.generate(input_ids=inputs, max_new_tokens=256, temperature=0.3)
    response_text = tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)

    print("=" * 65)
    print("RESPOSTA DO AGENTE TREINADO:")
    print("=" * 65)
    print(response_text)
    print("=" * 65)


if __name__ == "__main__":
    test_inference()
