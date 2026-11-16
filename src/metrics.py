import pandas as pd


# ############### Funções Base Reutilizáveis ###############


def completed_orders(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtra apenas os pedidos com status concluído.

    Parâmetros:
        df (pd.DataFrame): DataFrame contendo os dados de vendas.

    Retorna:
        pd.DataFrame: Subconjunto apenas com pedidos concluídos.
    """
    return df[df["status"] == "concluido"].copy()


def total_revenue(df: pd.DataFrame) -> float:
    """
    Calcula a receita total considerando apenas pedidos concluídos.

    Parâmetros:
        df (pd.DataFrame): DataFrame contendo os dados de vendas.

    Retorna:
        float: Receita total arredondada em 2 casas decimais.
    """
    validos = completed_orders(df)
    return round(float(validos["receita"].sum()), 2)


# ################ Métricas de Negócio ################


def total_orders(df: pd.DataFrame) -> int:
    """
    Calcula o número total de pedidos concluídos.

    Parâmetros:
        df (pd.DataFrame): DataFrame contendo os dados de vendas.

    Retorna:
        int: Quantidade de pedidos únicos concluídos.
    """
    return int(completed_orders(df)["pedido_id"].nunique())


def products_sold(df: pd.DataFrame) -> int:
    """
    Calcula a quantidade total de itens vendidos nos pedidos concluídos.

    Parâmetros:
        df (pd.DataFrame): DataFrame contendo os dados de vendas.

    Retorna:
        int: Soma das quantidades vendidas.
    """
    return int(completed_orders(df)["quantidade"].sum())


def unique_clients(df: pd.DataFrame) -> int:
    """
    Calcula o número de clientes únicos entre os pedidos concluídos.

    Parâmetros:
        df (pd.DataFrame): DataFrame contendo os dados de vendas.

    Retorna:
        int: Quantidade de clientes distintos.
    """
    return int(completed_orders(df)["cliente_id"].nunique())


def average_ticket(df: pd.DataFrame) -> float:
    """
    Calcula o ticket médio por pedido concluído.

    Parâmetros:
        df (pd.DataFrame): DataFrame contendo os dados de vendas.

    Retorna:
        float: Valor médio por pedido concluído.
    """
    orders = total_orders(df)
    if orders == 0:
        return 0.0
    return round(total_revenue(df) / orders, 2)


def cancellation_rate(df: pd.DataFrame) -> float:
    """
    Calcula a taxa de cancelamento sobre o total geral de pedidos.

    Parâmetros:
        df (pd.DataFrame): DataFrame contendo os dados de vendas.

    Retorna:
        float: Percentual de pedidos cancelados.
    """
    all_orders = df["pedido_id"].nunique()
    if all_orders == 0:
        return 0.0

    canceled_orders = df.loc[df["status"] == "cancelado", "pedido_id"].nunique()
    return round(float((canceled_orders / all_orders) * 100), 2)


def monthly_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrupa a receita total dos pedidos concluídos por mês (YYYY-MM).

    Parâmetros:
        df (pd.DataFrame): DataFrame contendo os dados de vendas.

    Retorna:
        pd.DataFrame: Tabela com as colunas 'mes' e 'receita' ordenadas cronologicamente.
    """
    validos = completed_orders(df)
    if "mes" not in validos.columns:
        validos["mes"] = pd.to_datetime(validos["data"]).dt.to_period("M").astype(str)

    return (
        validos.groupby("mes", as_index=False)["receita"]
        .sum()
        .round({"receita": 2}) #uso da função round() para arredondar a coluna 'receita' para 2 casas decimais
        .sort_values("mes")
    )

if __name__ == "__main__":
    df_test = pd.read_csv("data/processed/sales_clean.csv", sep=";", decimal=",")

    print(f"Receita Total: R$ {total_revenue(df_test):,.2f}")
    print(f"Total de Pedidos Concluídos: {total_orders(df_test)}")
    print(f"Produtos Vendidos: {products_sold(df_test)}")
    print(f"Clientes Únicos: {unique_clients(df_test)}")
    print(f"Ticket Médio: R$ {average_ticket(df_test):,.2f}")
    print(f"Taxa de Cancelamento: {cancellation_rate(df_test):.2f}%")
    print("\nReceita Mensal:")
    print(monthly_revenue(df_test))