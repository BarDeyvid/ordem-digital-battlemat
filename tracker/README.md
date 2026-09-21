# Battlemat Tracker & Simulator

Módulo em Python para rastreamento de miniaturas físicas (via câmera 2K RTSP / Webcam) e simulador de telemetria para desenvolvimento contínuo sem câmera física.

---

## 🚀 Como Rodar

### 1. Simulador de Miniaturas (Dev Mode sem Câmera)

Ideal para desenvolver lógica, auras e efeitos no Unreal Engine sem precisar de câmera ligada ou miniaturas físicas na mesa:

```bash
# Modo Interativo com Janela Gráfica (arraste tokens com o mouse, gire com o scroll)
uv run simulate

# Modo Trajetória Circular Automática (ideal para testar fluidez e interpolação)
uv run simulate --mode circle

# Modo Combate Tático (investigadores vs criaturas de Sangue/Energia)
uv run simulate --mode combat
```

**Controles do Modo Interativo:**
* **Clique & Arraste:** Move o token selecionado pela tela.
* **Scroll do Mouse ou teclas A / D:** Gira o token.
* **Teclas `1` a `5`:** Seleciona Investigador 1 a 5.
* **Tecla `S`:** Seleciona Criatura de Sangue (ID 11).
* **Tecla `M`:** Seleciona Criatura de Morte (ID 12).
* **Tecla `E`:** Seleciona Criatura de Energia (ID 13).
* **Tecla `C`:** Seleciona Criatura de Conhecimento (ID 14).
* **Tecla `N`:** Seleciona Aliado Civil / NPC (ID 20).
* **Espaço:** Liga / Desliga o token selecionado na mesa.
* **`Q` ou `ESC`:** Encerra o simulador.

---

### 2. Tracker Real com Câmera (OpenCV / ArUco)

Quando a câmera física e a iluminação estiverem montadas na mesa:

```bash
# Executa o tracking oficial com envio UDP para 127.0.0.1:8888
uv run tracker
```

---

### 3. Geração de Marcadores para Impressão

```bash
uv run python generate_markers.py
```
Gera os marcadores em alta resolução prontos para imprimir na pasta `markers/` com identificação e borda branca de segurança (*quiet zone*).
