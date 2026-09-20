"""Utilitário para gerar marcadores ArUco em alta resolução prontos para impressão.

Gera os marcadores correspondentes aos tokens configurados em tokens_config.json.
"""

import os
from pathlib import Path
import cv2 as cv
import json

from tracker.detector import ARUCO_DICTS
from tracker import config

def generate_aruco_markers(output_dir="markers", marker_size=600):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    dict_id = ARUCO_DICTS.get(config.ARUCO_DICT_NAME, cv.aruco.DICT_4X4_50)
    aruco_dict = cv.aruco.getPredefinedDictionary(dict_id)

    # Lê IDs configurados
    tokens_config_path = config.TOKENS_CONFIG_FILE
    ids_to_generate = []
    
    if tokens_config_path.exists():
        with open(tokens_config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            mappings = data.get("mappings", {})
            ids_to_generate = [(int(k), v.get("name", f"Token {k}"), v.get("type", "token")) for k, v in mappings.items()]
    
    # Se não houver, gera os primeiros 15
    if not ids_to_generate:
        ids_to_generate = [(i, f"Token {i}", "token") for i in range(1, 16)]

    print(f"Gerando {len(ids_to_generate)} marcadores ArUco ({config.ARUCO_DICT_NAME}) em: {output_path.resolve()}")

    for marker_id, name, token_type in ids_to_generate:
        # Gera o marcador
        marker_img = cv.aruco.generateImageMarker(aruco_dict, marker_id, marker_size)
        
        # Adiciona borda branca com texto para identificação fácil antes de recortar
        border_size = 60
        bordered = cv.copyMakeBorder(
            marker_img, 
            border_size, border_size + 40, border_size, border_size, 
            cv.BORDER_CONSTANT, value=255
        )
        
        caption = f"ID: {marker_id} | {name} [{token_type}]"
        cv.putText(
            bordered, caption, (border_size, marker_size + border_size + 28),
            cv.FONT_HERSHEY_SIMPLEX, 0.7, 0, 2, cv.LINE_AA
        )

        filename = output_path / f"aruco_{config.ARUCO_DICT_NAME}_id_{marker_id}_{token_type}.png"
        cv.imwrite(str(filename), bordered)
        print(f"  [+] Gerado: {filename.name}")

    print("\n[Sucesso] Todos os marcadores foram gerados. Prontos para imprimir e colar nas bases de 25mm/32mm!")

if __name__ == "__main__":
    generate_aruco_markers()
