"""Dashboard em Streamlit para visualização dos dados e previsões."""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from model import load_or_train_model, predict_needs_irrigation, load_data

DB_PATH = Path(__file__).parent.parent / "db/dados_irrigacao.db"

st.set_page_config(page_title="FarmTech Dashboard", layout="wide")

st.title("🌱 FarmTech Solutions – Dashboard de Irrigação")

# Carrega dados
def get_df():
    conn = sqlite3.connect(DB_PATH)
    df_ = pd.read_sql_query("SELECT * FROM leituras", conn)
    conn.close()
    return df_

# --- MENU LATERAL ---
page = st.sidebar.radio("Selecione a visão:", ("Dashboard", "Dados brutos"))

# --- Carrega dados ---
df = get_df()

# Se coluna de temperatura ainda não existir, cria vazia
if 'temperatura' not in df.columns:
    df['temperatura'] = None

# Força timestamp como datetime
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

# Força bomba como string UPPER segura
df["bomba"] = df["bomba"].astype(str).fillna("").str.upper()

# Filtro de datas
st.sidebar.markdown("### Filtro de datas")
data_min = df["timestamp"].min().date()
data_max = df["timestamp"].max().date()

data_range = st.sidebar.date_input(
    "Selecione o intervalo:",
    value=(data_min, data_max),
    min_value=data_min,
    max_value=data_max
)

# Verifica se é tupla de 2 datas
if isinstance(data_range, tuple) and len(data_range) == 2:
    data_inicio, data_fim = data_range
else:
    st.error("Selecione um intervalo de datas válido (início e fim).")
    st.stop()

# Aplica filtro de intervalo
df = df[(df["timestamp"].dt.date >= data_inicio) & (df["timestamp"].dt.date <= data_fim)]

# Garante que df ainda é DataFrame
if not isinstance(df, pd.DataFrame) or df.empty:
    st.warning("Sem dados disponíveis nesse intervalo.")
    st.stop()

# --- Página de dados brutos ---
if page == "Dados brutos":
    st.subheader("Dados brutos – últimas 500 linhas")
    st.dataframe(df.tail(500), use_container_width=True)
    st.stop()

# --- MÉTRICAS RÁPIDAS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Leituras totais", len(df))
col2.metric("Umidade média (%)", f"{df['umidade'].mean():.1f}")
col3.metric("Temp. média (°C)", f"{df['temperatura'].mean():.1f}")
col4.metric("% Bomba Ligada", f"{(df['bomba'] == 'LIGADA').mean()*100:.1f}%")

# --- VARIAÇÃO DE SENSORES ---
col_umid, col_ph, col_temp = st.columns(3)
with col_umid:
    st.subheader("Variação da Umidade (%)")
    st.line_chart(df.set_index("timestamp")["umidade"])

with col_ph:
    st.subheader("Variação do pH")
    st.line_chart(df.set_index("timestamp")["ph"])

with col_temp:
    st.subheader("Variação da Temperatura (°C)")
    st.line_chart(df.set_index("timestamp")["temperatura"])

# --- PROBABILIDADE DA BOMBA POR HORA ---
df["hora"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.hour

# Protege groupby com Series seguras
total_por_hora = df.loc[:, "hora"].value_counts().sort_index()
ligada_por_hora = df.loc[df["bomba"] == "LIGADA", "hora"].value_counts().sort_index()

prob_on = (ligada_por_hora / total_por_hora * 100).round(1).fillna(0)
prob_on.name = "Probabilidade (%)"

raw_stats = prob_on.copy()

col_on, col_sug = st.columns(2)

with col_on:
    st.subheader("Probabilidade de Irrigação por horário")
    st.bar_chart(prob_on, use_container_width=True, height=300)

with col_sug:
    st.subheader("Horários sugeridos para Irrigação")
    sugeridos = raw_stats[raw_stats > 50].sort_values(ascending=False)
    if sugeridos.empty:
        st.info("Nenhum horário excede 50 % no histórico.")
    else:
        st.bar_chart(sugeridos.head(5), use_container_width=True, height=300)

# --- PREVISÃO AD-HOC ---
st.subheader("Previsão de Necessidade de Irrigação (Regra fixa)")

umidade_input = st.slider("Umidade do Solo (%)", 0.0, 100.0, float(df["umidade"].iloc[-1]), 1.0)
ph_input = st.slider("pH do Solo", 0.0, 14.0, float(df["ph"].iloc[-1]), 0.1)

k_presente = st.checkbox("Potássio presente (K)", value=True)
p_presente = st.checkbox("Fósforo presente (P)", value=True)

if st.button("📊 Prever"):
    precisa = (
        (umidade_input < 40.0) or
        (ph_input < 5.5 or ph_input > 7.5) or
        (not k_presente) or
        (not p_presente)
    )
    msg = "Necessita irrigar!" if precisa else "Não precisa irrigar agora."
    st.success(msg)
