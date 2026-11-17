import pandas as pd


# ############### Funções Base Reutilizáveis ###############


def completed_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra apenas os pedidos com status concluído."""
    return df[df["status"] == "concluido"].copy()


def total_revenue(df: pd.DataFrame) -> float:
    """Calcula a receita total considerando apenas pedidos concluídos."""
    validos = completed_orders(df)
    return round(float(validos["receitas"].sum()), 2)


# ################ Métricas de Negócio ################


def total_orders(df: pd.DataFrame) -> int:
    """Calcula o número total de pedidos únicos concluídos."""
    return int(completed_orders(df)["pedido_id"].nunique())


def products_sold(df: pd.DataFrame) -> int:
    """Calcula a quantidade total de itens vendidos nos pedidos concluídos."""
    return int(completed_orders(df)["quantidade"].sum())


def unique_clients(df: pd.DataFrame) -> int:
    """Calcula o número de clientes únicos entre os pedidos concluídos."""
    return int(completed_orders(df)["cliente_id"].nunique())


def average_ticket(df: pd.DataFrame) -> float:
    """Calcula o ticket médio por pedido concluído."""
    orders = total_orders(df)
    if orders == 0:
        return 0.0
    return round(total_revenue(df) / orders, 2)


def cancellation_rate(df: pd.DataFrame) -> float:
    """
    Calcula a taxa de cancelamento sobre os pedidos efetivamente submetidos
    (ignora eventos ainda em status 'carrinho').
    """
    submitted = df[df["status"].isin(["concluido", "cancelado"])]
    all_orders = submitted["pedido_id"].nunique()
    if all_orders == 0:
        return 0.0

    canceled_orders = submitted.loc[submitted["status"] == "cancelado", "pedido_id"].nunique()
    return round(float((canceled_orders / all_orders) * 100), 2)


def monthly_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa a receita total dos pedidos concluídos por mês (YYYY-MM)."""
    validos = completed_orders(df)
    if "mes" not in validos.columns:
        validos["mes"] = pd.to_datetime(validos["data"]).dt.to_period("M").astype(str)

    return (
        validos.groupby("mes", as_index=False)["receitas"]
        .sum()
        .round({"receitas": 2})
        .sort_values("mes")
    )


def product_conversion_rate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula a taxa de conversão de carrinho por produto:
    - 'intencoes_carrinho': total de clientes únicos que adicionaram o produto (carrinho, concluido ou cancelado).
    - 'clientes_concluidos': total de clientes únicos que concluíram a compra do produto.
    - 'taxa_conversao_pct': percentual de conversão (%).
    - 'clientes_por_venda': a cada quantos clientes interessados 1 compra é concluída.
    """
    if "produto" not in df.columns or df.empty:
        return pd.DataFrame(
            columns=[
                "produto",
                "intencoes_carrinho",
                "clientes_concluidos",
                "taxa_conversao_pct",
                "clientes_por_venda",
            ]
        )

    intents = (
        df.groupby("produto", as_index=False)["cliente_id"]
        .nunique()
        .rename(columns={"cliente_id": "intencoes_carrinho"})
    )

    completed = (
        completed_orders(df)
        .groupby("produto", as_index=False)["cliente_id"]
        .nunique()
        .rename(columns={"cliente_id": "clientes_concluidos"})
    )

    merged = pd.merge(intents, completed, on="produto", how="left").fillna({"clientes_concluidos": 0})
    merged["clientes_concluidos"] = merged["clientes_concluidos"].astype(int)

    merged["taxa_conversao_pct"] = (
        (merged["clientes_concluidos"] / merged["intencoes_carrinho"]) * 100
    ).round(2)

    merged["clientes_por_venda"] = merged.apply(
        lambda row: round(row["intencoes_carrinho"] / row["clientes_concluidos"], 2)
        if row["clientes_concluidos"] > 0
        else None,
        axis=1,
    )

    return merged.sort_values(
        by=["taxa_conversao_pct", "clientes_concluidos"], ascending=[False, False]
    ).reset_index(drop=True)


if __name__ == "__main__":
    df_test = pd.read_csv("data/processed/sales_clean.csv", sep=";", decimal=",")

    print(f"Receita Total: R$ {total_revenue(df_test):,.2f}")
    print(f"Total de Pedidos Concluídos: {total_orders(df_test)}")
    print(f"Produtos Vendidos: {products_sold(df_test)}")
    print(f"Clientes Únicos: {unique_clients(df_test)}")
    print(f"Ticket Médio: R$ {average_ticket(df_test):,.2f}")
    print(f"Taxa de Cancelamento: {cancellation_rate(df_test):.2f}%")
    print("\nConversão por Produto:")
    print(product_conversion_rate(df_test))