# Ordem Paranormal - Digital Battlemat

> **Mesa tática híbrida e interativa para RPG de Ordem Paranormal, combinando rastreamento de miniaturas físicas via visão computacional (OpenCV/ArUco), renderização dinâmica de névoa de guerra e efeitos de Membrana na Unreal Engine.**

---

### Descrição Curta (GitHub `About`)
> *Interactive top-down digital battlemat for Ordem Paranormal RPG using Unreal Engine 5, OpenCV fiducial tracking, and 3D printed smart bases.*

---

## 📐 Visão Geral da Arquitetura

O sistema integra hardware físico com um loop de baixa latência:

```
[ Câmera 2K Top-Down ]
        │  (Captura a 30/60 fps)
        ▼
[ tracker.py (OpenCV / ArUco) ]
        │  (Transformação de perspectiva + Normalização X, Y, Ângulo)
        ▼  UDP Socket (127.0.0.1:8888)
[ Unreal Engine 5 (Battlemat Project) ]
        │  (Recepção de pacotes + Spawning/Atualização de Atores)
        ▼
[ Monitor 24" Deitado na Mesa ]  <───────  [ Miniaturas 3D (Bases ArUco) ]
 (Grid, Fog of War, VFX de Membrana)
```

1. **Bases Físicas (3D Print):** Miniaturas com bases contendo marcadores ArUco (`DICT_4X4_50`).
2. **Tracker (Python):** Localiza os 4 cantos da tela, faz o *warp perspective* e extrai $(X, Y, \text{yaw})$ de cada token.
3. **Engine (Unreal Engine):** Projeta o mapa tático em visão ortográfica direta no monitor deitado, revelando névoa (*Dynamic Render Target*) e emitindo efeitos de elementos (Sangue, Morte, Energia, Conhecimento) sob as peças.

---

## 🚀 Como Inicializar o Projeto

### 1. Pré-requisitos
* **Git** e **Git LFS** instalados no sistema:
  ```bash
  git lfs install
  ```
* **Python 3.10+**
* **Unreal Engine 5.x**

### 2. Configurando o Repositório
```bash
# Clone o repositório
git clone https://github.com/SEU_USUARIO/ordem-digital-battlemat.git
cd ordem-digital-battlemat

# Certifique-se de que o LFS puxou os binários
git lfs pull
```

### 3. Configurando o Tracker Python
```bash
cd tracker/
python -m venv venv

# No Windows:
venv\Scripts\activate
# No Linux/macOS:
source venv/bin/activate

pip install opencv-python numpy
```

---

## 📂 Estrutura de Diretórios

```plaintext
ordem-digital-battlemat/
├── .gitattributes          # Configurações do Git LFS (.uasset, .umap, etc.)
├── .gitignore              # Filtros de build e cache da Unreal/Python
├── README.md               # Documentação principal
├── tracker/                # Módulo de Visão Computacional (Python)
│   ├── tracker.py          # Script de detecção ArUco e envio UDP
│   ├── calibration.json    # Calibração dos 4 cantos da tela
│   └── requirements.txt
├── 3d_models/              # Peças para impressão (STL / Step)
│   ├── base_25mm_aruco.stl
│   ├── base_32mm_aruco.stl
│   └── monitor_corners.stl # Cantoneiras para apoio do monitor
└── unreal_project/         # Projeto Unreal Engine
    ├── Config/
    ├── Content/
    └── Battlemat.uproject
```

---

## ⚙️ Protocolo de Comunicação UDP

O tracker envia payloads JSON leves para a porta `8888` via UDP a cada frame detectado:

```json
{
  "timestamp": 1726859900.12,
  "tokens": [
    {
      "id": 4,
      "type": "investigador",
      "x": 0.452,
      "y": 0.781,
      "rotation": 92.4
    },
    {
      "id": 12,
      "type": "criatura_morte",
      "x": 0.510,
      "y": 0.320,
      "rotation": 180.0
    }
  ]
}
```

---

## 🛠️ Roadmap

- [x] Configuração inicial de Git e Git LFS
- [ ] Modelagem e fatiamento das cantoneiras e bases ArUco
- [ ] Script Python de calibração de 4 pontos da tela
- [ ] Implementação do receptor UDP via Blueprint/C++ na Unreal
- [ ] Sistema dinâmico de Fog of War (Desocultação por raio da base)
- [ ] Shaders de membrana e partículas temáticas (Sangue, Morte, Energia, Conhecimento)