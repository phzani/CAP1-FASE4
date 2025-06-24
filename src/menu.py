#!/usr/bin/env python3
"""Menu de execução do FarmTech Solutions (Fase 4).

Executa operações comuns:
1. Gerar dados sintéticos
2. Treinar/atualizar modelo
3. Ver estatísticas
4. Adicionar leitura manual
5. Excluir leitura
6. Listar últimas leituras
"""
from __future__ import annotations

import random
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

# Diretórios base
SRC_DIR = Path(__file__).resolve().parent  # pasta src
ROOT_DIR = SRC_DIR.parent

# Garante que src/ está no PYTHONPATH para execuções externas
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from armazenamento_sql import (
    inserir_leitura,
    consultar_leituras,
    remover_leitura,
)
from model import load_data, train_model

DB_PATH = SRC_DIR / "db" / "dados_irrigacao.db"

MENU = """
==================== MENU ====================
1) Gerar dados sintéticos
2) Treinar modelo preditivo
3) Ver estatísticas do banco
4) Adicionar leitura manual
5) Excluir leitura por ID
6) Listar últimas 10 leituras
7) Abrir dashboard Streamlit
8) Abrir Wokwi (diagram.json)
9) Excluir TODAS as leituras
0) Sair
=============================================
Escolha uma opção: """

def gerar_dados_sinteticos():
    try:
        n = int(input("Quantas leituras deseja gerar? "))
    except ValueError:
        print("Valor inválido.")
        return

    ph_range = (4.5, 8.5)
    umid_range = (20.0, 80.0)
    temp_range = (15.0, 35.0)
    base_time = datetime.now() - timedelta(hours=n)

    for i in range(n):
        ts = base_time + timedelta(hours=i)
        fosforo = random.choice(["PRESENTE", "AUSENTE"])
        potassio = random.choice(["PRESENTE", "AUSENTE"])
        ph = round(random.uniform(*ph_range), 2)
        umidade = round(random.uniform(*umid_range), 1)
        temperatura = round(random.uniform(*temp_range), 1)

        falta_nutriente = fosforo == "AUSENTE" or potassio == "AUSENTE"
        solo_seco = umidade < 40.0
        ph_ruim = ph < 5.5 or ph > 7.5
        bomba_on = falta_nutriente or solo_seco or ph_ruim

        motivos = []
        if falta_nutriente:
            motivos.append("[Nutriente ausente]")
        if solo_seco:
            motivos.append("[Solo seco]")
        if ph_ruim:
            motivos.append("[pH fora do ideal]")

        inserir_leitura(
            fosforo,
            potassio,
            ph,
            umidade,
            temperatura,
            "LIGADA" if bomba_on else "DESLIGADA",
            " ".join(motivos),
            timestamp=ts.isoformat(),
        )
    print(f"{n} leituras geradas.")


def treinar_modelo():
    df = load_data()
    if df.empty:
        print("Sem dados suficientes.")
        return
    print(f"Treinando em {len(df)} registros…")
    train_model(df)


def ver_estatisticas():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Métricas básicas
    cur.execute("SELECT COUNT(*), AVG(umidade), MIN(umidade), MAX(umidade), AVG(ph), MIN(ph), MAX(ph), AVG(temperatura), MIN(temperatura), MAX(temperatura) FROM leituras")
    row = cur.fetchone()
    total = row[0] or 0
    avg_umid, min_umid, max_umid = row[1:4]
    avg_ph, min_ph, max_ph = row[4:7]
    avg_temp, min_temp, max_temp = row[7:10]

    cur.execute("SELECT COUNT(*) FROM leituras WHERE bomba='LIGADA'")
    ligadas = cur.fetchone()[0] or 0
    perc_bomba = ligadas / total * 100 if total else 0

    # Variação percentual (amplitude relativa à média)
    var_umid = ((max_umid - min_umid) / avg_umid * 100) if avg_umid else 0
    var_ph = ((max_ph - min_ph) / avg_ph * 100) if avg_ph else 0
    var_temp = ((max_temp - min_temp) / avg_temp * 100) if avg_temp else 0

    # Nutrientes – porcentagem de AUSENTE
    cur.execute("SELECT SUM(potassio='AUSENTE'), SUM(fosforo='AUSENTE') FROM leituras")
    aus_pot, aus_fos = cur.fetchone()
    perc_pot = aus_pot / total * 100 if total else 0
    perc_fos = aus_fos / total * 100 if total else 0

    print("\n--- Estatísticas ---")
    print(f"Total leituras             : {total}")
    print(f"Umidade média              : {avg_umid:.1f}%")
    print(f"Variação de umidade        : {var_umid:.1f}% (min {min_umid:.1f} / max {max_umid:.1f})")
    print(f"pH médio                   : {avg_ph:.2f}")
    print(f"Variação de pH             : {var_ph:.1f}% (min {min_ph:.2f} / max {max_ph:.2f})")
    print(f"Temperatura média          : {avg_temp:.1f} °C")
    print(f"Variação de temperatura    : {var_temp:.1f}% (min {min_temp:.1f} / max {max_temp:.1f})")
    print(f"Potássio AUSENTE           : {perc_pot:.1f}% das leituras")
    print(f"Fósforo AUSENTE            : {perc_fos:.1f}% das leituras")
    print(f"% Bomba ligada             : {perc_bomba:.1f}%\n")
    conn.close()


def adicionar_leitura_manual():
    fosforo = input("Fósforo (PRESENTE/AUSENTE): ").strip().upper()
    potassio = input("Potássio (PRESENTE/AUSENTE): ").strip().upper()
    try:
        ph = float(input("pH: "))
        umidade = float(input("Umidade (%): "))
        temperatura = float(input("Temperatura (°C): "))
    except ValueError:
        print("Valores inválidos.")
        return

    # --- Regras de decisão ---
    falta_nutriente = fosforo == "AUSENTE" or potassio == "AUSENTE"
    solo_seco = umidade < 40.0
    ph_ruim = ph < 5.5 or ph > 7.5
    bomba_on = falta_nutriente or solo_seco or ph_ruim

    motivos = []
    if falta_nutriente:
        motivos.append("[Nutriente ausente]")
    if solo_seco:
        motivos.append("[Solo seco]")
    if ph_ruim:
        motivos.append("[pH fora do ideal]")

    bomba = "LIGADA" if bomba_on else "DESLIGADA"
    motivo = " ".join(motivos)

    inserir_leitura(fosforo, potassio, ph, umidade, temperatura, bomba, motivo)
    print(f"Leitura adicionada. Bomba {bomba}. Motivo: {motivo or '---'}\n")


def excluir_leitura():
    try:
        id_ = int(input("ID da leitura a excluir: "))
    except ValueError:
        print("ID inválido.")
        return
    remover_leitura(id_)
    print("Leitura excluída (se existia).\n")


def listar_ultimas():
    rows = consultar_leituras()[-10:]
    if not rows:
        print("Sem leituras.")
        return
    print("\nÚltimas 10 leituras:")
    for r in rows:
        print(r)
    print()


def abrir_dashboard():
    """Abre o dashboard Streamlit em um processo separado."""
    script_path = SRC_DIR / "dashboard" / "dashboard.py"
    if not script_path.exists():
        print("Dashboard não encontrado em", script_path)
        return
    print("Iniciando Streamlit em nova janela…")
    if sys.platform.startswith("win"):
        # 'start' abre nova janela de terminal no Windows
        cmd = ["cmd", "/c", "start", "", sys.executable, "-m", "streamlit", "run", str(script_path)]
        subprocess.Popen(cmd)
    else:
        # Em Unix, abre no background na mesma janela
        subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(script_path)])


def excluir_todas_leituras():
    conf = input("Tem certeza que deseja excluir TODAS as leituras? (s/N): ").lower()
    if conf != "s":
        print("Operação cancelada.")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM leituras")
    conn.commit()
    conn.close()
    print("Todas as leituras foram removidas.\n")


def abrir_wokwi():
    """Abre o arquivo diagram.json do Wokwi no VS Code ou app padrão."""
    diagram_path = SRC_DIR / "wokwi" / "diagram.json"
    if not diagram_path.exists():
        print("Arquivo não encontrado:", diagram_path)
        return

    resp = input("Você já possui a extensão \"Wokwi for VS Code\" instalada? (s/N): ").lower()
    if resp != "s":
        print("Por favor, instale a extensão Wokwi no VS Code antes de abrir o diagrama: https://marketplace.visualstudio.com/items?itemName=wokwi.wokwi-vscode")
        return

    print("Abrindo Wokwi…")

    # Tenta VS Code primeiro
    try:
        subprocess.Popen(["code", str(diagram_path)])
        return
    except FileNotFoundError:
        print("Comando 'code' não encontrado. Verifique se o VS Code está instalado e o comando adicionado ao PATH.")
        # Fallback pelo sistema
        if sys.platform.startswith("win"):
            subprocess.Popen(["cmd", "/c", "start", "", str(diagram_path)])
        elif sys.platform.startswith("darwin"):
            subprocess.Popen(["open", str(diagram_path)])
        else:
            subprocess.Popen(["xdg-open", str(diagram_path)])


def main():
    while True:
        opc = input(MENU).strip()
        if opc == "1":
            gerar_dados_sinteticos()
        elif opc == "2":
            treinar_modelo()
        elif opc == "3":
            ver_estatisticas()
        elif opc == "4":
            adicionar_leitura_manual()
        elif opc == "5":
            excluir_leitura()
        elif opc == "6":
            listar_ultimas()
        elif opc == "7":
            abrir_dashboard()
        elif opc == "8":
            abrir_wokwi()
        elif opc == "9":
            excluir_todas_leituras()
        elif opc == "0":
            break
        else:
            print("Opção inválida.\n")


if __name__ == "__main__":
    main() 