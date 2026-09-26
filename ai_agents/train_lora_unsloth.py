"""Script de Treinamento LoRA usando Unsloth para os Agentes de Ordem Paranormal.

Executa na sua RTX 5060 Ti Blackwell (16GB VRAM) com máxima eficiência.
"""

import os
from pathlib import Path

# Certifique-se de que unsloth e trl estejam instalados no seu ambiente de treino
try:
    from unsloth import FastLanguageModel
    from datasets import load_dataset
    from trl import SFTTrainer
    from transformers import TrainingArguments
except ImportError:
    print("[Aviso] Execute no ambiente com Unsloth: pip install unsloth trl datasets")

BASE_DIR = Path(__file__).resolve().parent
DATASET_FILE = BASE_DIR / "dataset" / "unsloth_training_dataset.jsonl"
OUTPUT_DIR = BASE_DIR / "lora_ordem_agents"

# Hiperparâmetros recomendados para 7B em 16GB VRAM (Blackwell)
MAX_SEQ_LENGTH = 2048
DTYPE = None  # None para auto-detecção (BF16 na Blackwell)
LOAD_IN_4BIT = True  # QLoRA para deixar bastante VRAM livre para batch size


def run_training(model_name: str = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"):
    print("=" * 65)
    print(f"  INICIANDO TREINO LoRA DOS AGENTES - MODELO BASE: {model_name}")
    print(f"  Dataset: {DATASET_FILE}")
    print("=" * 65)

    if not DATASET_FILE.exists() or DATASET_FILE.stat().st_size == 0:
        print(f"[Erro] O dataset {DATASET_FILE} está vazio ou não existe.")
        print("Jogue algumas rodadas com demo_session.py para gerar os dados primeiro!")
        return

    # 1. Carrega o modelo base otimizado pelo Unsloth
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=DTYPE,
        load_in_4bit=LOAD_IN_4BIT,
        trust_remote_code=True,
    )

    # 2. Configura os Adaptadores LoRA
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,  # Rank 16 para estabilidade e velocidade
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_alpha=32,
        lora_dropout=0,  # 0 é otimizado pelo Unsloth
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    # 3. Carrega e prepara o Dataset
    dataset = load_dataset("json", data_files=str(DATASET_FILE), split="train")

    def format_chat_template(batch):
        texts = []
        for conv in batch["conversations"]:
            # Aplica o template de chat nativo do tokenizer
            text = tokenizer.apply_chat_template(conv, tokenize=False, add_generation_prompt=False)
            texts.append(text)
        return {"text": texts}

    dataset = dataset.map(format_chat_template, batched=True)

    # 4. Configuração do Trainer
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        dataset_num_proc=1,  # 1 para Windows compatibilidade total
        packing=False,
        args=TrainingArguments(
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=10,
            num_train_epochs=3,
            learning_rate=2e-4,
            fp16=False,
            bf16=True,  # Nativo na Blackwell RTX 5060 Ti
            logging_steps=1,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="cosine",
            seed=3407,
            output_dir=str(OUTPUT_DIR),
            report_to="none",
        ),
    )

    print("\n[Treinamento] Rodando épocas de ajuste nos pesos dos Agentes...")
    trainer_stats = trainer.train()

    print(f"\n[Sucesso] Treino concluído! Salvando adaptador LoRA em {OUTPUT_DIR}...")
    model.save_pretrained(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))
    print("Pronto para carregar os Agentes treinados no seu Battlemat!")


if __name__ == "__main__":
    import sys
    model_arg = sys.argv[1] if len(sys.argv) > 1 else "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
    run_training(model_arg)
