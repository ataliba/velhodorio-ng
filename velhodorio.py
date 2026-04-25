from agno.agent import Agent
from agno.team import Team
from agno.models.openrouter import OpenRouter
from agno.db.sqlite import SqliteDb
from agno.db.postgres import PostgresDb
from tools.music_tools import consultar_acervo_musical
from tools.hackernews import consultar_hackernews
from tools.messenger import dispatch
from tools.ponto import (
    registrar_ponto_trabalho,
    reset_current_message_date_time,
    set_current_message_date_time,
)
from agno.tools.google.calendar import GoogleCalendarTools
from agno.tools.mcp import MCPTools
from agno.tools.mcp.params import SSEClientParams, StreamableHTTPClientParams

from agents.agendador import get_agendador
from agents.financas import get_financas
from agents.pesquisador import get_pesquisador
from agents.terapeuta import get_terapeuta

import asyncio
import os
import time
import json
import logging

# --- LOGS RAIZ ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÃO ---
SQS_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/485952611520/velhodorio-queue"
AWS_REGION = "us-east-1"

# --- PERSISTÊNCIA ---
# Usa Postgres se as variáveis estiverem definidas no Infisical, senão SQLite local
_pg_url  = os.getenv("POSTGRES_URL")
_pg_user = os.getenv("POSTGRES_USER")
_pg_pass = os.getenv("POSTGRES_PASS")

if _pg_url and _pg_user and _pg_pass:
    _conn = _pg_url.replace("://", f"://{_pg_user}:{_pg_pass}@", 1) if "@" not in _pg_url else _pg_url
    if not _conn.startswith("postgresql+psycopg"):
        _conn = _conn.replace("postgresql://", "postgresql+psycopg://", 1)
    storage = PostgresDb(db_url=_conn, db_schema="public")
    logger.info("🐘 Persistência: PostgreSQL")
else:
    storage = SqliteDb(session_table="velho_rio_sessions", db_file="velho_rio.db")
    logger.info("📦 Persistência: SQLite (fallback)")

calendar_tools = GoogleCalendarTools(
    credentials_path="credentials.json",
    token_path="token.json"
)

deepseek_v3 = OpenRouter(id="openai/gpt-4o-mini")


def _build_team(
    mcp_agendador: MCPTools | None,
    reclaim: MCPTools | None,
    mcp_financeiro: MCPTools | None,
    mcp_escavador: MCPTools | None,
) -> Team:
    """Monta o time com os MCPTools já inicializados (dentro do async with).

    Mapeamento de ferramentas por MCP:
      escavador: Wikipedia, SerpAPI, Brave Search, OpenWeatherMap → Pesquisador
      finance:   CoinMarketCap Price, Crypto Map, Global Metrics → Finanças
      agendas:   Todoist, Google Calendar → Agendador
      reclaim:   Proteção de tempo → Agendador
      Qdrant:    rag_terapeuta → Terapeuta (via knowledge, sem MCP)
    """

    agendador   = get_agendador(tools=[mcp_agendador, reclaim, calendar_tools])
    financas    = get_financas(tools=[mcp_financeiro])
    pesquisador = get_pesquisador(tools=[mcp_escavador])  # só escavador
    terapeuta   = get_terapeuta(tools=None)  # Qdrant via knowledge

    return Team(
        name="Velho do Rio",
        model=deepseek_v3,
        role="Interface Central e Orquestrador Cyber-Xamã",
        members=[agendador, financas, pesquisador, terapeuta],
        db=storage,
        read_chat_history=True,
        num_history_messages=15,
        add_history_to_context = True,
        tools=[consultar_acervo_musical, consultar_hackernews, registrar_ponto_trabalho],  # só o que o orquestrador usa diretamente
        show_members_responses=True,
        debug_mode=True,
        description="""
            Você é o Velho do Rio 🌿🕶️, um mentor cyber-xamã que habita a margem entre o código e o inconsciente.
            Sua presença é firme, lúcida e direta. Você não enrola; você aponta o caminho.
            Você conversa exclusivamente com Ataliba, entendendo a alta carga que ele sustenta.
        """,
        instructions=[
            "Você é o Velho do Rio. Pragmático, visionário e direto.",

            "--- REGRAS DE DELEGAÇÃO (SIGA SEMPRE) ---",
            "1. PESQUISA NA INTERNET: qualquer busca web, notícia, fato externo, pesquisa de mercado → delegue ao 'pesquisador'. NUNCA use suas próprias ferramentas para isso.",
            "2. AGENDA, TAREFAS, CALENDÁRIO, RECLAIM, JIRA, TODOIST → delegue ao 'agendador'.",
            "3. CRIPTO, FINANÇAS, PREÇO DE ATIVO, P&L → delegue ao 'financas'.",
            "4. EMOÇÕES, SAÚDE MENTAL, SOBRECARGA, TERAPIA → delegue ao 'terapeuta'.",
            "5. ACERVO DE DISCOS → use a ferramenta 'consultar_acervo_musical' diretamente e passe a frase completa do usuário para a tool.",
            "6. HACKER NEWS, HN, TOP STORIES, ASK HN, SHOW HN, JOBS DO HN → use a ferramenta 'consultar_hackernews' diretamente.",
            "7. PONTO DE TRABALHO → use a ferramenta 'registrar_ponto_trabalho' diretamente.",
            "7.1. Ao registrar ponto, considere que a data/hora oficial vem sempre do timestamp real da mensagem atual. Nunca invente, estime ou reconstrua a data por conta própria.",
            "7.2. Se a ferramenta de ponto retornar erro indicando ausência de 'metadata.date_time', responda de forma natural que nao foi possivel bater o ponto porque a mensagem chegou sem data/hora de referencia. Nao exponha o erro cru nem tente contornar isso com suposicoes.",
            "7.3. Se a ferramenta de ponto retornar 'SUCESSO:' com a hora registrada, transforme isso em confirmacao natural para o usuario, deixando clara a hora efetivamente usada no registro, sem repetir o prefixo tecnico.",
            "8. Para tudo mais que não se encaixe acima, responda diretamente.",

            "--- COMPORTAMENTO ---",
            "Não faça o trabalho braçal — coordene.",
            "Use jargões corporativos e humor sagaz quando apropriado, mas mantenha a sabedoria xamânica.",
            "REGRA DE OURO: Utilidade e Clareza acima de tudo. Sem floreios desnecessários.",
            "Você tem a capacidade de 'ouvir' Ataliba através de áudios (que chegam como texto). Responda naturalmente.",
        ],
        markdown=True,
    )


async def iniciar_consumidor():
    import boto3
    sqs = boto3.client('sqs', region_name=AWS_REGION)

    # --- URLs dos MCPs ---
    agendador_url  = os.getenv("MCP_AGENDADOR") or "http://localhost/agendador"
    reclaim_url    = os.getenv("RECLAIM_URL") or "http://localhost:3000/mcp"
    financeiro_url = os.getenv("MCP_FINANCEIRO") or "http://localhost/financeiro"
    escavador_url  = os.getenv("MCP_ESCAVADOR") or "http://localhost/escavador"
    mcp_token      = os.getenv("MCP_TOKEN", "")
    auth_headers   = {"Authorization": f"Bearer {mcp_token}"}

    # --- Conecta cada MCP individualmente, isolando falhas ---
    async def _connect(name: str, tool: MCPTools) -> MCPTools | None:
        try:
            await tool.__aenter__()
            logger.info(f"🔌 {name}: ✅ conectado")
            return tool
        except Exception as e:
            logger.warning(f"🔌 {name}: ❌ offline ({type(e).__name__})")
            try:
                await tool.__aexit__(None, None, None)
            except Exception:
                pass
            return None

    async def _disconnect(name: str, tool: MCPTools | None):
        if tool is None:
            return
        try:
            await tool.__aexit__(None, None, None)
        except Exception:
            pass

    mcp_agendador  = MCPTools(transport="sse", server_params=SSEClientParams(url=agendador_url, headers=auth_headers))
    mcp_reclaim    = MCPTools(transport="streamable-http", server_params=StreamableHTTPClientParams(url=reclaim_url))
    mcp_financeiro = MCPTools(transport="sse", server_params=SSEClientParams(url=financeiro_url, headers=auth_headers))
    mcp_escavador  = MCPTools(transport="sse", server_params=SSEClientParams(url=escavador_url, headers=auth_headers))

    agendador_conn  = await _connect("MCP Agendador",  mcp_agendador)
    reclaim_conn    = await _connect("MCP Reclaim",    mcp_reclaim)
    financeiro_conn = await _connect("MCP Financeiro", mcp_financeiro)
    escavador_conn  = await _connect("MCP Escavador",  mcp_escavador)

    try:
        velho_rio_team = _build_team(
            mcp_agendador=agendador_conn,
            reclaim=reclaim_conn,
            mcp_financeiro=financeiro_conn,
            mcp_escavador=escavador_conn,
        )

        logger.info("🌿 Velho do Rio (Team v2) ouvindo as águas do SQS...")

        while True:
            try:
                response = sqs.receive_message(
                    QueueUrl=SQS_QUEUE_URL,
                    MaxNumberOfMessages=1,
                    WaitTimeSeconds=20
                )

                if 'Messages' in response:
                    for msg in response['Messages']:
                        body     = json.loads(msg['Body'])
                        prompt   = body.get("content", "")
                        metadata = body.get("metadata", {})
                        chat_id  = metadata.get("chatId")
                        source   = metadata.get("source", "whatsapp")
                        date_time = metadata.get("date_time")

                        if not chat_id:
                            logger.warning("⚠️ Mensagem sem chatId ignorada.")
                            sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=msg['ReceiptHandle'])
                            continue

                        logger.info(f"📩 Mensagem recebida de {chat_id}: {prompt}")
                        date_time_token = set_current_message_date_time(date_time)
                        try:
                            res = await velho_rio_team.arun(prompt, session_id=chat_id)
                        finally:
                            reset_current_message_date_time(date_time_token)

                        if hasattr(res, 'history') and res.history:
                            for step in res.history:
                                if hasattr(step, 'tool_calls') and step.tool_calls:
                                    logger.info(f"🛠️ Ferramentas usadas: {step.tool_calls}")

                        resposta_texto = res.content if hasattr(res, 'content') else str(res)
                        dispatch(source, chat_id, resposta_texto)
                        sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=msg['ReceiptHandle'])

            except Exception as e:
                logger.error(f"💥 Erro no ciclo do consumidor: {e}")
                await asyncio.sleep(5)

    finally:
        for name, tool in [
            ("Agendador", agendador_conn), ("Reclaim", reclaim_conn),
            ("Financeiro", financeiro_conn), ("Escavador", escavador_conn),
        ]:
            await _disconnect(name, tool)



if __name__ == "__main__":
    if not os.getenv("OPENROUTER_API_KEY"):
        logger.error("❌ OPENROUTER_API_KEY obrigatória!")
    else:
        asyncio.run(iniciar_consumidor())
