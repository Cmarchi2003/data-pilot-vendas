import pandas as pd
import plotly.express as px
import streamlit as st

from src.agent import ask_data_pilot
from src.etl import register_store_event
from src.metrics import (
    average_ticket,
    cancellation_rate,
    monthly_revenue,
    product_conversion_rate,
    products_sold,
    total_orders,
    total_revenue,
    unique_clients,
)


@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_csv("data/processed/sales_clean.csv", sep=";", decimal=",")


def render_dashboard(df: pd.DataFrame) -> None:
    with st.sidebar:
        st.divider()
        st.subheader(":material/tune: Filtros do Painel")
        st.caption("Selecione as categorias que deseja analisar")
        categories = st.pills(
            "Categorias",
            sorted(df["categoria"].dropna().unique()),
            selection_mode="multi",
            width="stretch",
            key="categories",
        )

    filtered_df = df[df["categoria"].isin(categories)] if categories else df
    data = monthly_revenue(filtered_df)
    conv_df = product_conversion_rate(filtered_df)

    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        with st.container(gap="xxsmall"):
            st.title(":material/space_dashboard: :violet[Data Pilot — Painel de Vendas]", anchor=False)
            st.caption(
                "Análise executiva em tempo real: receita, ticket médio, cancelamentos e funil de conversão por produto."
            )
        st.badge("Ao vivo", icon=":material/analytics:", color="violet")

    st.space("small")

    # Linha Principal de KPIs
    revenue_panel, mid_panel, right_panel = st.columns([1.5, 1, 1])

    revenue_panel.metric(
        ":violet-badge[:material/paid: Receita Total]",
        f"R$ {total_revenue(filtered_df):,.2f}",
        border=True,
        height=290,
        chart_data=data["receitas"] if not data.empty else [0],
        chart_type="area",
        delta_color="violet",
    )

    with mid_panel:
        st.metric(
            ":blue-badge[:material/receipt_long: Pedidos Concluídos]",
            total_orders(filtered_df),
            border=True,
            height=135,
        )
        st.metric(
            ":green-badge[:material/analytics: Ticket Médio]",
            f"R$ {average_ticket(filtered_df):,.2f}",
            border=True,
            height=135,
        )

    with right_panel:
        st.metric(
            ":orange-badge[:material/group: Clientes Únicos]",
            f"{unique_clients(filtered_df)} ({products_sold(filtered_df)} itens)",
            border=True,
            height=135,
        )
        st.metric(
            ":red-badge[:material/cancel: Taxa de Cancelamento]",
            f"{cancellation_rate(filtered_df):.2f}%",
            border=True,
            height=135,
        )

    st.space("small")

    # Gráfico de Receita Mensal + Funil de Conversão por Produto
    chart_col, conv_col = st.columns([1.3, 1])

    with chart_col:
        fig = px.line(data, x="mes", y="receitas", markers=True)
        fig.update_traces(
            line={"color": "violet", "width": 4},
            marker={"size": 10, "color": "violet"},
            fill="tozeroy",
            fillcolor="rgba(238, 130, 238, 0.2)",
        )
        fig.update_layout(
            height=380,
            margin=dict(l=20, r=20, t=20, b=16),
            hovermode="x unified",
            xaxis_title=None,
            yaxis_title=None,
        )
        fig.update_yaxes(tickprefix="R$ ", tickformat="~s")

        with st.container(border=True):
            with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
                st.subheader(":material/show_chart: Receita Mensal")
                st.badge("Evolução", color="blue")
            st.plotly_chart(
                fig,
                width="stretch",
                config={"displayModeBar": False, "scrollZoom": False},
            )

    with conv_col:
        with st.container(border=True):
            with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
                st.subheader(":material/shopping_cart_checkout: Conversão por Produto")
                st.badge("Carrinho → Compra", color="green")

            if conv_df.empty:
                st.info("Sem dados de produtos para o filtro selecionado.")
            else:
                st.dataframe(
                    conv_df,
                    hide_index=True,
                    width="stretch",
                    height=380,
                    column_config={
                        "produto": st.column_config.TextColumn("Produto"),
                        "intencoes_carrinho": st.column_config.NumberColumn("No Carrinho", format="%d"),
                        "clientes_concluidos": st.column_config.NumberColumn("Compraram", format="%d"),
                        "taxa_conversao_pct": st.column_config.ProgressColumn(
                            "Conversão (%)",
                            format="%.1f%%",
                            min_value=0,
                            max_value=100,
                        ),
                        "clientes_por_venda": st.column_config.NumberColumn(
                            "A cada X clientes", format="%.1f"
                        ),
                    },
                )


def render_chat(df: pd.DataFrame) -> None:
    st.title(":material/smart_toy: :violet[Conversa com os Dados]", anchor=False)
    st.caption("Faça perguntas em linguagem natural. Os cálculos são executados pelo Python e explicados pela IA.")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Olá! Sou o **Data Pilot**. Posso analisar sua receita, ticket médio, cancelamentos "
                    "ou a taxa de conversão de carrinho de cada produto. O que você gostaria de saber?"
                ),
            }
        ]

    # Sugestões rápidas de perguntas
    suggestions = [
        "Qual é o resumo geral das vendas?",
        "Qual produto tem a melhor e a pior conversão de carrinho?",
        "Como foi a evolução da receita mensal?",
    ]
    cols = st.columns(len(suggestions))
    selected_suggestion = None
    for idx, text in enumerate(suggestions):
        if cols[idx].button(text, use_container_width=True):
            selected_suggestion = text

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Pergunte sobre vendas, categorias ou conversão de produtos...")
    prompt = selected_suggestion or user_input

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Calculando métricas e analisando..."):
                reply = ask_data_pilot(prompt, st.session_state.messages[:-1], df)
                st.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})


def render_storefront(df: pd.DataFrame) -> None:
    st.title(":material/storefront: :violet[Loja Marchi — Simulador ao Vivo]", anchor=False)
    st.caption(
        "Adicione produtos ao carrinho (intenção de compra) ou finalize o pedido. "
        "Cada ação grava diretamente no CSV e atualiza o painel e o agente na hora."
    )

    # Monta catálogo a partir dos produtos e preços existentes no CSV
    catalog_df = (
        df.groupby(["produto", "categoria"], as_index=False)["preco_unitario"]
        .median()
        .sort_values(["categoria", "produto"])
    )

    if "cart" not in st.session_state:
        st.session_state.cart = []

    col_catalog, col_checkout = st.columns([1.4, 1])

    with col_catalog:
        st.subheader(":material/inventory_2: Vitrine de Produtos")
        cliente_id = st.number_input(
            "ID do Cliente Simulado",
            min_value=1,
            max_value=999999,
            value=1001,
            step=1,
            help="Use IDs diferentes para testar a taxa de conversão (clientes únicos no carrinho vs. concluídos).",
        )

        grid = st.columns(2)
        for idx, row in catalog_df.iterrows():
            card_col = grid[idx % 2]
            with card_col.container(border=True):
                st.badge(str(row["categoria"]), color="violet")
                st.markdown(f"### {row['produto']}")
                st.markdown(f"**R$ {row['preco_unitario']:,.2f}**")
                qty = st.number_input(
                    "Quantidade",
                    min_value=1,
                    max_value=20,
                    value=1,
                    key=f"qty_{idx}",
                )
                if st.button("Adicionar ao Carrinho", key=f"add_{idx}", use_container_width=True):
                    # Registra a intenção no CSV imediatamente para contabilizar no funil
                    register_store_event(
                        cliente_id=int(cliente_id),
                        produto=str(row["produto"]),
                        categoria=str(row["categoria"]),
                        quantidade=int(qty),
                        preco_unitario=float(row["preco_unitario"]),
                        status="carrinho",
                    )
                    st.session_state.cart.append(
                        {
                            "cliente_id": int(cliente_id),
                            "produto": str(row["produto"]),
                            "categoria": str(row["categoria"]),
                            "quantidade": int(qty),
                            "preco_unitario": float(row["preco_unitario"]),
                        }
                    )
                    load_data.clear()
                    st.toast(f"'{row['produto']}' registrado no carrinho (CSV atualizado)!")
                    st.rerun()

    with col_checkout:
        with st.container(border=True):
            st.subheader(":material/shopping_bag: Carrinho Atual")
            if not st.session_state.cart:
                st.info("Seu carrinho está vazio. Adicione um item da vitrine ao lado para gerar intenção de compra.")
            else:
                total_cart = 0.0
                for item in st.session_state.cart:
                    subtotal = item["quantidade"] * item["preco_unitario"]
                    total_cart += subtotal
                    st.markdown(
                        f"- **{item['quantidade']}x {item['produto']}** (Cliente #{item['cliente_id']}) — R$ {subtotal:,.2f}"
                    )

                st.divider()
                st.metric("Total do Carrinho", f"R$ {total_cart:,.2f}")

                btn_buy, btn_cancel = st.columns(2)
                if btn_buy.button(":material/check_circle: Finalizar Compra", type="primary", use_container_width=True):
                    for item in st.session_state.cart:
                        register_store_event(
                            cliente_id=item["cliente_id"],
                            produto=item["produto"],
                            categoria=item["categoria"],
                            quantidade=item["quantidade"],
                            preco_unitario=item["preco_unitario"],
                            status="concluido",
                        )
                    st.session_state.cart = []
                    load_data.clear()
                    st.success("Compra concluída e gravada no CSV! Os KPIs já foram atualizados.")
                    st.rerun()

                if btn_cancel.button(":material/cancel: Cancelar Pedido", use_container_width=True):
                    for item in st.session_state.cart:
                        register_store_event(
                            cliente_id=item["cliente_id"],
                            produto=item["produto"],
                            categoria=item["categoria"],
                            quantidade=item["quantidade"],
                            preco_unitario=item["preco_unitario"],
                            status="cancelado",
                        )
                    st.session_state.cart = []
                    load_data.clear()
                    st.warning("Pedido registrado como cancelado no CSV.")
                    st.rerun()


def main():
    st.set_page_config(
        page_title="Data Pilot",
        page_icon=":material/analytics:",
        layout="wide",
    )

    df = load_data()

    with st.sidebar:
        st.title(":material/rocket_launch: Data Pilot")
        menu = st.radio(
            "Navegação",
            ["Painel de Vendas", "Chat com os Dados", "Loja Teste"],
            label_visibility="collapsed",
        )

    if menu == "Painel de Vendas":
        render_dashboard(df)
    elif menu == "Chat com os Dados":
        render_chat(df)
    elif menu == "Loja Teste":
        render_storefront(df)


if __name__ == "__main__":
    main()