"""Script para extrair todo o banco de dados do Supabase original e gerar
arquivos JSON limpos + um script SQL completo para rodar no seu próprio Supabase ou PostgreSQL/SQLite.
"""

import os
import json
import urllib.request
import urllib.parse
from pathlib import Path

SUPABASE_URL = "https://duoesappjstgejlwxkyp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR1b2VzYXBwanN0Z2VqbHd4a3lwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMwNTkwMzcsImV4cCI6MjA5ODYzNTAzN30.6r1GAxv420BfB1YgBmDzyyh4sBXYYIkVTSDhkqLuQ2w"

TABLES_TO_DUMP = [
    "Origens",
    "Grupo de Origens",
    "Perícias",
    "Rituais",
    "Símbolos Rituais",
    "Armas",
    "Trilhas",
    "Itens",
    "Itens Amaldiçoados",
    "Maldições",
    "Modificações",
    "Munições",
    "Progressão NEX",
    "Proteções",
    "Poderes",
    "PoderesParanormais"
]

def fetch_table(table_name: str):
    encoded_name = urllib.parse.quote(table_name)
    url = f"{SUPABASE_URL}/rest/v1/{encoded_name}?select=*"
    
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Range-Unit": "items",
        "Range": "0-9999"
    })
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except Exception as e:
        print(f"  [!] Erro ao buscar tabela '{table_name}': {e}")
        return []

def sql_escape(val):
    if val is None:
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (dict, list)):
        s = json.dumps(val, ensure_ascii=False).replace("'", "''")
        return f"'{s}'"
    s = str(val).replace("'", "''")
    return f"'{s}'"

def infer_sql_type(col_name: str, sample_vals: list) -> str:
    # Remove nulls
    non_nulls = [v for v in sample_vals if v is not None]
    if not non_nulls:
        return "TEXT"
    
    first = non_nulls[0]
    if isinstance(first, bool):
        return "BOOLEAN"
    if isinstance(first, int):
        # Verifica se todos são int
        if all(isinstance(v, int) for v in non_nulls):
            return "BIGINT"
    if isinstance(first, float):
        return "NUMERIC"
    if isinstance(first, (dict, list)):
        return "JSONB"
    return "TEXT"

def dump_all(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    json_dir = output_dir / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    
    sql_file_path = output_dir / "supabase_full_migration.sql"
    
    print(f"Iniciando dump de {len(TABLES_TO_DUMP)} tabelas para: {output_dir.resolve()}\n")
    
    sql_lines = [
        "-- ==========================================================================",
        "-- MIGRAÇÃO COMPLETA: ORDEM PARANORMAL RPG",
        "-- Gerado automaticamente a partir do banco oficial do projeto",
        "-- Compatível com PostgreSQL / Supabase SQL Editor",
        "-- ==========================================================================\n"
    ]
    
    summary = {}
    
    for table in TABLES_TO_DUMP:
        print(f"[+] Baixando tabela: {table} ...")
        rows = fetch_table(table)
        summary[table] = len(rows)
        print(f"    -> {len(rows)} registros encontrados.")
        
        # Salva JSON
        safe_name = table.lower().replace(" ", "_").replace("ç", "c").replace("õ", "o").replace("ã", "a").replace("í", "i")
        table_json_path = json_dir / f"{safe_name}.json"
        with open(table_json_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
            
        if not rows:
            continue
            
        # Gera CREATE TABLE
        columns = list(rows[0].keys())
        col_defs = []
        for col in columns:
            samples = [r.get(col) for r in rows[:50]]
            sql_t = infer_sql_type(col, samples)
            col_defs.append(f'  "{col}" {sql_t}')
            
        sql_lines.append(f'-- Tabela: "{table}" ({len(rows)} linhas)')
        sql_lines.append(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
        sql_lines.append(f'CREATE TABLE "{table}" (\n' + ",\n".join(col_defs) + '\n);\n')
        
        # Gera INSERTS em blocos
        insert_batch_size = 50
        for i in range(0, len(rows), insert_batch_size):
            batch = rows[i:i + insert_batch_size]
            col_names_str = ", ".join([f'"{c}"' for c in columns])
            
            value_rows = []
            for r in batch:
                vals = [sql_escape(r.get(c)) for c in columns]
                value_rows.append(f"({', '.join(vals)})")
                
            sql_lines.append(f'INSERT INTO "{table}" ({col_names_str}) VALUES\n' + ",\n".join(value_rows) + ";\n")
            
        sql_lines.append("\n")
        
    with open(sql_file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_lines))
        
    print("\n" + "=" * 60)
    print("DUMP CONCLUÍDO COM SUCESSO!")
    print("=" * 60)
    for t, cnt in summary.items():
        print(f"  - {t:<22} : {cnt} registros")
    print(f"\nArquivo SQL completo gerado em:\n  {sql_file_path.resolve()}")
    print("=" * 60)

if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "database_dump"
    dump_all(out)
