"""Gera dados sintéticos de leituras de sensores e popula o banco SQLite.

Uso:
    python scripts/generate_sample_data.py [n_registros]

Se o banco não existir será criado automaticamente.
"""

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import sqlite3

DB_PATH = Path(__file__).parent.parent / "dados_irrigacao.db"

NUM_ROWS = int(sys.argv[1]) if len(sys.argv) > 1 else 300

random.seed(42)

# Cria conexão
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute(
    """
CREATE TABLE IF NOT EXISTS leituras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    fosforo TEXT,
    potassio TEXT,
    ph REAL,
    umidade REAL,
    temperatura REAL,
    bomba TEXT,
    motivo TEXT
)
"""
)
conn.commit()

base_time = datetime.now() - timedelta(hours=NUM_ROWS)

for i in range(NUM_ROWS):
    ts = (base_time + timedelta(hours=i)).isoformat()
    fosforo = random.choice(["PRESENTE", "AUSENTE"])
    potassio = random.choice(["PRESENTE", "AUSENTE"])
    ph = round(random.uniform(4.5, 8.5), 2)
    umidade = round(random.uniform(20.0, 80.0), 1)
    temperatura = round(random.uniform(15.0, 35.0), 1)

    falta_nutriente = (fosforo == "AUSENTE" or potassio == "AUSENTE")
    solo_seco = umidade < 40.0
    ph_ruim = (ph < 5.5 or ph > 7.5)
    bomba_on = falta_nutriente or solo_seco or ph_ruim

    motivo_parts = []
    if falta_nutriente:
        motivo_parts.append("[Nutriente ausente]")
    if solo_seco:
        motivo_parts.append("[Solo seco]")
    if ph_ruim:
        motivo_parts.append("[pH fora do ideal]")
    motivo = " ".join(motivo_parts)

    cur.execute(
        """
        INSERT INTO leituras (timestamp, fosforo, potassio, ph, umidade, temperatura, bomba, motivo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ts,
            fosforo,
            potassio,
            ph,
            umidade,
            temperatura,
            "LIGADA" if bomba_on else "DESLIGADA",
            motivo,
        ),
    )

conn.commit()
print(f"Inseridas {NUM_ROWS} leituras em {DB_PATH}")
conn.close() 