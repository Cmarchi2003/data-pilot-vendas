import pandas as pd
import plotly.express as px
import streamlit as st

from src.metrics import average_ticket, monthly_revenue, total_orders, total_revenue


@st.cache_data
def load_data():
    df = pd.read_csv("data/processed/sales_clean.csv", sep=";", decimal=",")
    return df


def main():
    st.set_page_config(
        page_title="Data Analysis Dashboard",
        page_icon=":material/analytics:",
        layout="wide",
    )

    df = load_data()

    with st.sidebar:
        st.subheader(":material/tune: Controle")
        st.caption("Selecione as categorias que deseja analisar")
        categories = st.pills(
            "Categorias",
            sorted(df["categoria"].unique()),
            selection_mode="multi",
            width="stretch",
            key="categories",
        )

    filtered_df = df[df["categoria"].isin(categories)] if categories else df
    data = monthly_revenue(filtered_df)

    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        with st.container(gap="xxsmall"):
            st.title(":material/space_dashboard: :violet[Dashboard de Análise de Dados]", anchor=False)
            st.caption(
                "Dashboard interativo para análise de dados de vendas, incluindo métricas como receita total, ticket médio e taxa de cancelamento."
            )
        st.badge("Painel de vendas", icon=":material/analytics:", color="violet")

    st.space("small")

    revenue_panel, secondary_panel = st.columns([1.65, 1])
    revenue_panel.metric(
        ":violet-badge[:material/paid: Receita Total]",
        f"R$ {total_revenue(filtered_df):,.2f}",
        border=True,
        height=300,
        chart_data=data["receitas"],
        chart_type="area",
        delta_color="violet",
    )

    with secondary_panel:
        st.metric(
            ":blue-badge[:material/receipt_long: Pedidos]",
            total_orders(filtered_df),
            border=True,
            height=130,
        )
        st.metric(
            ":green-badge[:material/analytics: Ticket Médio]",
            f"R$ {average_ticket(filtered_df):,.2f}",
            border=True,
            height=130,
        )

    st.space("small")

    fig = px.line(data, x="mes", y="receitas", markers=True)
    fig.update_traces(
        line={"color": "violet", "width": 4},
        marker={"size": 10, "color": "violet"},
        fill="tozeroy",
        fillcolor="rgba(238, 130, 238, 0.2)",
    )
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=20, b=16),
        hovermode="x unified",
        xaxis_title=None,
        yaxis_title=None,
    )
    fig.update_yaxes(tickprefix="R$ ", tickformat="~s")

    with st.container(border=True):
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
            st.subheader(":material/show_chart: Receita Mensal")
            st.badge("Mensal", color="blue")
        st.plotly_chart(
            fig,
            width="stretch",
            config={"displayModeBar": False, "scrollZoom": False},
        )


if __name__ == "__main__":
    main()