import sqlite3
from datetime import datetime
from pathlib import Path

# Caminho do banco de dados (pasta src/db)
DB_DIR = Path(__file__).resolve().parent / 'db'
DB_DIR.mkdir(parents=True, exist_ok=True)  # garante que o diretório exista
DB_PATH = DB_DIR / 'dados_irrigacao.db'

# Conexão com o banco de dados SQLite (cria se não existir)
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Criação da tabela
cursor.execute('''
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
''')
conn.commit()

# Garante presença da coluna 'temperatura' caso a tabela já existisse antes da inclusão
cursor.execute("PRAGMA table_info(leituras)")
cols = [col[1] for col in cursor.fetchall()]
if 'temperatura' not in cols:
    cursor.execute("ALTER TABLE leituras ADD COLUMN temperatura REAL")
    conn.commit()

# Função para inserir uma leitura
def inserir_leitura(fosforo, potassio, ph, umidade, temperatura, bomba, motivo, timestamp: str | None = None):
    """Insere uma leitura no banco.

    Se *timestamp* não for informado, utiliza o momento atual.
    """
    if timestamp is None:
        timestamp = datetime.now().isoformat()

    cursor.execute(
        '''
        INSERT INTO leituras (timestamp, fosforo, potassio, ph, umidade, temperatura, bomba, motivo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (timestamp, fosforo, potassio, ph, umidade, temperatura, bomba, motivo),
    )
    conn.commit()

# Função para consultar todas as leituras
def consultar_leituras():
    cursor.execute('SELECT * FROM leituras')
    return cursor.fetchall()

# Função para atualizar uma leitura pelo id
def atualizar_leitura(id, fosforo, potassio, ph, umidade, temperatura, bomba, motivo):
    cursor.execute('''
        UPDATE leituras SET fosforo=?, potassio=?, ph=?, umidade=?, temperatura=?, bomba=?, motivo=? WHERE id=?
    ''', (fosforo, potassio, ph, umidade, temperatura, bomba, motivo, id))
    conn.commit()

# Função para remover uma leitura pelo id
def remover_leitura(id):
    cursor.execute('DELETE FROM leituras WHERE id=?', (id,))
    conn.commit()

# Função para importar dados de um arquivo de texto (ex: dados_serial_exemplo.txt)
def importar_dados_arquivo(nome_arquivo):
    with open(nome_arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            if linha.startswith('#') or not linha.strip():
                continue  # Ignora comentários e linhas vazias
            # Exemplo de linha:
            # Fosforo: AUSENTE | Potassio: AUSENTE | pH: 3.00 | Umidade: 40.0% | Bomba: LIGADA | Motivo: [Nutriente ausente] [pH fora do ideal]
            partes = linha.strip().split('|')
            fosforo = partes[0].split(':')[1].strip()
            potassio = partes[1].split(':')[1].strip()
            ph = float(partes[2].split(':')[1].strip())
            umidade = float(partes[3].split(':')[1].replace('%','').strip())
            bomba = partes[4].split(':')[1].strip()
            motivo = partes[5].split(':',1)[1].strip() if len(partes) > 5 else ''
            inserir_leitura(fosforo, potassio, ph, umidade, 25.0, bomba, motivo)

# Exemplo de uso:
if __name__ == "__main__":
    # Exemplo de uso: importar dados do arquivo de exemplo
    importar_dados_arquivo('dados_serial_exemplo.txt')

    # Exemplo de inserção (substitua pelos dados reais do Serial Monitor)
    inserir_leitura('PRESENTE', 'AUSENTE', 6.0, 32.0, 25.0, 'LIGADA', '[Nutriente ausente]')
    inserir_leitura('PRESENTE', 'PRESENTE', 7.0, 51.5, 25.0, 'DESLIGADA', '')

    # Consulta
    leituras = consultar_leituras()
    for l in leituras:
        print(l)

    # Atualização
    atualizar_leitura(1, 'AUSENTE', 'AUSENTE', 3.0, 40.0, 25.0, 'LIGADA', '[Nutriente ausente] [pH fora do ideal]')

    # Remoção
    remover_leitura(2)

    # Consulta final
    print('Após atualização e remoção:')
    for l in consultar_leituras():
        print(l)

# Obs.: a conexão é mantida aberta para permitir uso pelos módulos importadores.
# Se executar este arquivo diretamente, a conexão será fechada no bloco __main__ acima.
