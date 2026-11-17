from datetime import datetime
from pathlib import Path
import pandas as pd

RAW_PATH = Path("data/raw/sales.csv")
PROCESSED_PATH = Path("data/processed/sales_clean.csv")


def run_etl() -> pd.DataFrame:
    df = pd.read_csv(RAW_PATH)

    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["mes"] = df["data"].dt.to_period("M").astype(str)
    df["status"] = df["status"].str.strip().str.lower()
    df = df.drop_duplicates()

    df["receitas"] = df["quantidade"] * df["preco_unitario"]

    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True) #Verifica se o diretório existe, caso contrário cria.
    df.to_csv(PROCESSED_PATH, index=False, sep=";", decimal=",")
    return df


def register_store_event(
    cliente_id: int,
    produto: str,
    categoria: str,
    quantidade: int,
    preco_unitario: float,
    status: str,
) -> dict:
    """
    Registra uma nova interação da Loja Fachada ('carrinho' ou 'concluido')
    diretamente no CSV processado, respeitando a estrutura de colunas existente.
    """
    df = pd.read_csv(PROCESSED_PATH, sep=";", decimal=",")
    now = datetime.now()

    next_order_id = 1 #Define id padrão caso não haja pedidos existentes
    if "pedido_id" in df.columns and not df["pedido_id"].dropna().empty: #verifica se a coluna existe e não está vazia
        numeric_ids = pd.to_numeric(df["pedido_id"], errors="coerce").dropna()
        if not numeric_ids.empty:
            next_order_id = int(numeric_ids.max()) + 1 #Se houver pedidos existentes, define o próximo id como o maior id existente + 1

    new_row = {
        "pedido_id": next_order_id,
        "cliente_id": int(cliente_id),
        "data": now.strftime("%Y-%m-%d"),
        "mes": now.strftime("%Y-%m"),
        "produto": produto,
        "categoria": categoria,
        "quantidade": int(quantidade),
        "preco_unitario": round(float(preco_unitario), 2),
        "receitas": round(float(quantidade * preco_unitario), 2),
        "status": status.strip().lower(),
    }

    # Garante alinhamento exato com as colunas existentes no CSV limpo
    aligned_row = {col: new_row.get(col, "") for col in df.columns}
    df_updated = pd.concat([df, pd.DataFrame([aligned_row])], ignore_index=True)
    df_updated.to_csv(PROCESSED_PATH, index=False, sep=";", decimal=",")

    return aligned_row


if __name__ == "__main__":
    df_clean = run_etl()
    print(f"Dados processados ({len(df_clean)} linhas) e salvos em '{PROCESSED_PATH}'")