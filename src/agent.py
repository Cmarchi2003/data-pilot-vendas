import json
import os
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
import pandas as pd

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

load_dotenv()

FALLBACK_MODELS = [
    os.getenv("OPENROUTER_MODEL", "openrouter/free"),
    "openrouter/free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
]

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_sales_summary",
            "description": (
                "Retorna os KPIs consolidados de vendas (receita total, total de pedidos concluídos, "
                "produtos vendidos, clientes únicos, ticket médio e taxa de cancelamento), "
                "com filtro opcional por categoria."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": {
                        "type": "string",
                        "description": "Nome exato da categoria para filtrar (opcional).",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_monthly_revenue",
            "description": "Retorna a série histórica da receita mensal (YYYY-MM) dos pedidos concluídos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": {
                        "type": "string",
                        "description": "Nome exato da categoria para filtrar (opcional).",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_conversion",
            "description": (
                "Retorna a taxa de conversão de carrinho por produto, mostrando quantos clientes "
                "colocaram o produto no carrinho, quantos concluíram a compra, o percentual de "
                "conversão e a razão de a cada quantos clientes 1 venda é concluída."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "produto": {
                        "type": "string",
                        "description": "Nome do produto específico para filtrar (opcional).",
                    }
                },
            },
        },
    },
]


def _execute_tool(name: str, args: dict, df: pd.DataFrame) -> str:
    target_df = df.copy()

    categoria = args.get("categoria")
    if categoria and "categoria" in target_df.columns:
        mask = target_df["categoria"].str.lower() == categoria.strip().lower()
        if mask.any():
            target_df = target_df[mask]

    if name == "get_sales_summary":
        result = {
            "filtro_categoria": categoria or "Todas",
            "receita_total_brl": total_revenue(target_df),
            "pedidos_concluidos": total_orders(target_df),
            "produtos_vendidos": products_sold(target_df),
            "clientes_unicos": unique_clients(target_df),
            "ticket_medio_brl": average_ticket(target_df),
            "taxa_cancelamento_pct": cancellation_rate(target_df),
        }
        return json.dumps(result, ensure_ascii=False)

    if name == "get_monthly_revenue":
        rev_df = monthly_revenue(target_df)
        return rev_df.to_json(orient="records", force_ascii=False)

    if name == "get_product_conversion":
        conv_df = product_conversion_rate(target_df)
        produto = args.get("produto")
        if produto and not conv_df.empty:
            mask = conv_df["produto"].str.lower().str.contains(produto.strip().lower(), na=False)
            if mask.any():
                conv_df = conv_df[mask]
        return conv_df.to_json(orient="records", force_ascii=False)

    return json.dumps({"erro": f"Ferramenta desconhecida: {name}"}, ensure_ascii=False)


def _call_with_fallback(client: OpenAI, messages: list, tools: list | None = None):
    tried = []
    for model in dict.fromkeys(FALLBACK_MODELS):
        if not model:
            continue
        tried.append(model)
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": 0.2,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            return client.chat.completions.create(**kwargs)
        except RateLimitError:
            continue

    raise RateLimitError(
        message=f"Todos os modelos gratuitos estão ocupados no momento ({', '.join(tried)}).",
        response=None,
        body=None,
    )


def ask_data_pilot(user_prompt: str, chat_history: list[dict], df: pd.DataFrame) -> str:
    """
    Envia a pergunta do usuário ao OpenRouter com acesso às ferramentas de métricas.
    O Python executa os cálculos e o LLM redige a análise em português.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return (
            "⚠️ Chave `OPENROUTER_API_KEY` não encontrada no arquivo `.env`. "
            "Configure sua chave do OpenRouter para ativar o agente."
        )

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    categorias_disponiveis = (
        sorted(df["categoria"].dropna().unique().tolist()) if "categoria" in df.columns else []
    )
    produtos_disponiveis = (
        sorted(df["produto"].dropna().unique().tolist()) if "produto" in df.columns else []
    )

    system_prompt = (
        "Você é o Data Pilot, um analista de dados sênior especialista em e-commerce e varejo. "
        "Responda sempre em português claro, objetivo e orientado a negócios. "
        "REGRA OBRIGATÓRIA: Nunca faça contas de cabeça e nunca invente números. "
        "Sempre chame as ferramentas disponíveis para obter os dados exatos antes de responder. "
        "Formate valores monetários em Reais (R$ X.XXX,XX) e percentuais com 2 casas decimais. "
        f"Categorias existentes na base: {categorias_disponiveis}. "
        f"Produtos existentes na base: {produtos_disponiveis}."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_prompt})

    try:
        response = _call_with_fallback(client, messages, tools=TOOLS_SCHEMA)
        assistant_msg = response.choices[0].message

        if assistant_msg.tool_calls:
            messages.append(assistant_msg)
            for tool_call in assistant_msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments or "{}")
                tool_output = _execute_tool(fn_name, fn_args, df)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_output,
                    }
                )

            final_response = _call_with_fallback(client, messages)
            return final_response.choices[0].message.content or "Não foi possível gerar a análise."

        return assistant_msg.content or "Não foi possível gerar a análise."

    except RateLimitError:
        return (
            "⏳ Os modelos gratuitos do OpenRouter atingiram o limite de requisições agora. "
            "Aguarde alguns segundos e envie sua pergunta novamente."
        )
    except Exception as e:
        return f"⚠️ Erro ao consultar o agente: {e}"