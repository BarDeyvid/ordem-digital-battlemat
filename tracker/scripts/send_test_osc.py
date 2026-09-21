"""Envia mensagens de teste OSC para Unreal Engine na porta 8000."""

import time
from pythonosc import udp_client

client = udp_client.SimpleUDPClient("127.0.0.1", 8000)

print("Enviando rajada de testes OSC para 127.0.0.1:8000...")

# 1. /token/update: [id, type, x, y, rotation]
print("-> Enviando /token/update")
client.send_message("/token/update", [1, "investigador", 0.45, 0.55, 90.0])
time.sleep(0.5)

# 2. /token/status: [id, nome, pv_pct, san_pct, pe_pct, pv_atual, pv_max, san_atual, san_max, pe_atual, pe_max]
print("-> Enviando /token/status")
client.send_message("/token/status", [1, "Dante", 0.80, 0.65, 0.90, 24, 30, 13, 20, 18, 20])
time.sleep(0.5)

# 3. /token/cast: [id, ritual_nome, elemento, alcance, alcance_m, custo_pe]
print("-> Enviando /token/cast")
client.send_message("/token/cast", [1, "Decadência", "Morte", "Curto (9m)", 9.0, 1])

print("Pronto! Todas as mensagens foram enviadas com sucesso.")
