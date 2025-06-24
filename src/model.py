"""Modelo preditivo para necessidade de irrigação.

Treina (ou carrega) um modelo de classificação simples usando Scikit-learn
com base nos dados históricos armazenados em `dados_irrigacao.db`.
"""

import sqlite3
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

MODEL_PATH = Path(__file__).parent / "irrigation_model.joblib"
DB_PATH = Path(__file__).parent / "db/dados_irrigacao.db"


def load_data():
    """Lê o banco SQLite e devolve um DataFrame pronto para treino."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT timestamp, umidade, ph, bomba FROM leituras", conn)
    conn.close()

    # Converte target para binário: 1 = LIGADA, 0 = DESLIGADA
    df["target"] = df["bomba"].str.strip().str.upper().eq("LIGADA").astype(int)
    # Colunas temporais opcionais
    df["hora"]   = pd.to_datetime(df["timestamp"]).dt.hour
    df["diaSem"] = pd.to_datetime(df["timestamp"]).dt.dayofweek  # 0=Seg … 6=Dom
    return df.dropna()


def train_model(df: pd.DataFrame):
    """Treina um modelo simples e salva em disco."""
    X = df[["umidade", "ph"]].values
    y = df["target"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipe = Pipeline(
        steps=[("scaler", StandardScaler()), ("clf", LogisticRegression())]
    )
    pipe.fit(X_train, y_train)

    acc = pipe.score(X_test, y_test)
    print(f"Acurácia (valid.): {acc:.2%}")

    joblib.dump(pipe, MODEL_PATH)
    return pipe


def load_or_train_model(df: pd.DataFrame | None = None):
    """Carrega o modelo se existir; caso contrário, treina."""
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)

    if df is None:
        df = load_data()
    return train_model(df)


def predict_needs_irrigation(model, umidade: float, ph: float, threshold: float = 0.5) -> tuple[bool, float]:
    """Prediz a probabilidade de necessidade de irrigação.

    Retorna (precisa_irrigar, probabilidade).
    """
    proba = model.predict_proba(np.array([[umidade, ph]]))[0][1]
    return proba >= threshold, proba


if __name__ == "__main__":
    data = load_data()
    model = train_model(data)
    print("Modelo treinado e salvo em", MODEL_PATH) 