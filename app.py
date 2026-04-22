"""
Velho do Rio — AgentOS

Serve o time como uma API FastAPI com 50+ endpoints prontos,
streaming SSE, histórico por sessão e UI via Agno Playground.

Rodar:
    infisical run -- python app.py

Ou via uvicorn diretamente:
    infisical run -- uvicorn app:app --host 0.0.0.0 --port 7777

Docs:
    http://localhost:7777/docs
"""

import os
import logging
from contextlib import asynccontextmanager

from agno.os import AgentOS
from agno.team import Team
from agno.models.openrouter import OpenRouter
from agno.db.sqlite import SqliteDb
from agno.db.postgres import PostgresDb
from agno.tools.mcp import MCPTools
from agno.tools.mcp.params import SSEClientParams, StreamableHTTPClientParams
from agno.tools.google.calendar import GoogleCalendarTools

from tools.music_tools import consultar_acervo_musical
from tools.hackernews import consultar_hackernews
from tools.ponto import registrar_ponto_trabalho

from agents.agendador import get_agendador
from agents.financas import get_financas
from agents.pesquisador import get_pesquisador
from agents.terapeuta import get_terapeuta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------
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

deepseek_v3 = OpenRouter(id="openai/gpt-4o-mini")

calendar_tools = GoogleCalendarTools(
    credentials_path="credentials.json",
    token_path="token.json"
)

# ---------------------------------------------------------------------------
# Helper: conecta um MCPTools isoladamente, retorna None se falhar
# ---------------------------------------------------------------------------
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

async def _disconnect(tool: MCPTools | None):
    if tool is None:
        return
    try:
        await tool.__aexit__(None, None, None)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Lifespan: conecta MCPs no startup, desconecta no shutdown
# ---------------------------------------------------------------------------
_connected: dict = {}

@asynccontextmanager
async def lifespan(app):
    mcp_token    = os.getenv("MCP_TOKEN", "")
    auth_headers = {"Authorization": f"Bearer {mcp_token}"}

    tools = {
        "agendador":  MCPTools(transport="sse", server_params=SSEClientParams(url=os.getenv("MCP_AGENDADOR", "http://localhost/agendador"), headers=auth_headers)),
        # O MCP do Reclaim responde melhor via streamable-http; em SSE ele tende a
        # derrubar o stream com incomplete chunked read mesmo quando a tool funciona.
        "reclaim":    MCPTools(transport="streamable-http", server_params=StreamableHTTPClientParams(url=os.getenv("RECLAIM_URL", "http://localhost:3000/mcp"))),
        "financeiro": MCPTools(transport="sse", server_params=SSEClientParams(url=os.getenv("MCP_FINANCEIRO", "http://localhost/financeiro"), headers=auth_headers)),
        "escavador":  MCPTools(transport="sse", server_params=SSEClientParams(url=os.getenv("MCP_ESCAVADOR", "http://localhost/escavador"), headers=auth_headers)),
    }

    for name, tool in tools.items():
        _connected[name] = await _connect(name, tool)

    # Monta o time com os MCPs que conectaram
    # Mapeamento:
    #   - escavador  → Pesquisador (Wikipedia, SerpAPI, Brave, OpenWeatherMap)
    #   - finance    → Finanças (CoinMarketCap)
    #   - agendador  → Agendador (Todoist, Google Calendar)
    #   - reclaim    → Agendador (proteção de tempo)
    #   - Qdrant     → Terapeuta (RAG - sem MCP, via knowledge)
    agendador   = get_agendador(tools=[_connected["agendador"], _connected["reclaim"], calendar_tools])
    financas    = get_financas(tools=[_connected["financeiro"]])
    pesquisador = get_pesquisador(tools=[_connected["escavador"]])  # só escavador - sem n8n
    terapeuta   = get_terapeuta(tools=None)  # Qdrant via knowledge, sem MCP

    team = Team(
        id="velho-rio",
        name="Velho do Rio",
        model=deepseek_v3,
        role="Interface Central e Orquestrador Cyber-Xamã",
        members=[agendador, financas, pesquisador, terapeuta],
        db=storage,
        read_chat_history=True,
        num_history_messages=15,
        tools=[consultar_acervo_musical, consultar_hackernews, registrar_ponto_trabalho],  # só o que o orquestrador usa diretamente
        show_members_responses=True,
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
            "8. Para tudo mais que não se encaixe acima, responda diretamente.",

            "--- COMPORTAMENTO ---",
            "Não faça o trabalho braçal — coordene.",
            "Use jargões corporativos e humor sagaz quando apropriado, mas mantenha a sabedoria xamânica.",
            "REGRA DE OURO: Utilidade e Clareza acima de tudo. Sem floreios desnecessários.",
            "Você tem a capacidade de 'ouvir' Ataliba através de áudios (que chegam como texto). Responda naturalmente.",
        ],
        markdown=True,
    )

    agent_os.teams = [team]
    agent_os.resync(app)
    logger.info("🌿 Velho do Rio OS pronto.")

    yield

    # Shutdown: desconecta todos os MCPs
    for name, tool in _connected.items():
        await _disconnect(tool)
    logger.info("🌊 Velho do Rio OS encerrado.")

# ---------------------------------------------------------------------------
# AgentOS
# ---------------------------------------------------------------------------
agent_os = AgentOS(
    name="Velho do Rio OS",
    description="Cyber-xamã multi-agente: agenda, finanças, pesquisa e suporte terapêutico.",
    teams=[],   # time é injetado no lifespan após MCPs conectarem
    db=storage,
    tracing=True,
    lifespan=lifespan,
)

app = agent_os.get_app()

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if not os.getenv("OPENROUTER_API_KEY"):
        logger.error("❌ OPENROUTER_API_KEY obrigatória!")
    else:
        # Não use reload=True com MCPTools — causa problemas no lifespan
        agent_os.serve(app="app:app", host="0.0.0.0", port=7777)
