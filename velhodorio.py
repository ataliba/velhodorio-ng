from agno.agent import Agent
from agno.team import Team
from agno.models.openrouter import OpenRouter
from agno.db.sqlite import SqliteDb
from tools.music_tools import consultar_acervo_musical
from tools.messenger import dispatch
from tools.ponto import registrar_ponto_trabalho
from agno.tools.google.calendar import GoogleCalendarTools
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters
from agno.tools.mcp.params import SSEClientParams

from agents.agendador import get_agendador
from agents.financas import get_financas
from agents.pesquisador import get_pesquisador

import os
import time
import json
import logging
import requests as _requests
from elevenlabs import ElevenLabs, save

# --- LOGS RAIZ ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÃO ---
SQS_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/485952611520/velhodorio-queue"
AWS_REGION = "us-east-1"

# --- PERSISTÊNCIA ---
storage = SqliteDb(session_table="velho_rio_sessions", db_file="velho_rio.db")

calendar_tools = GoogleCalendarTools(
    credentials_path="credentials.json",
    token_path="token.json"
)

def _reclaim_online(url: str, timeout: int = 3) -> bool:
    try:
        base = url.rsplit("/mcp", 1)[0]
        _requests.get(base, timeout=timeout)
        return True
    except Exception:
        return False

# 1. Conector n8n (Central)
n8n_mcp_server = MCPTools(
    transport="sse",
    server_params=SSEClientParams(
        url=os.getenv("MCP_URL") or "http://localhost",
        headers={"Authorization": f"Bearer {os.getenv('MCP_TOKEN')}"}
    )
)

# 2. Conector MCP_AGENDADOR
mcp_agendador_url = os.getenv("MCP_AGENDADOR") or "http://localhost/agendador"
mcp_agendador_server = None
if _reclaim_online(mcp_agendador_url):
    mcp_agendador_server = MCPTools(
        transport="sse",
        server_params=SSEClientParams(
            url=mcp_agendador_url,
            headers={"Authorization": f"Bearer {os.getenv('MCP_TOKEN')}"}
        )
    )

# 3. Conector Reclaim (SSE)
reclaim_mcp_url = os.getenv("RECLAIM_URL") or "http://localhost:3000/mcp"
reclaim_mcp_server = None
if _reclaim_online(reclaim_mcp_url):
    reclaim_mcp_server = MCPTools(
        transport="sse",
        server_params=SSEClientParams(url=reclaim_mcp_url)
    )

# 4. Conector MCP_FINANCEIRO
mcp_financeiro_url = os.getenv("MCP_FINANCEIRO") or "http://localhost/financeiro"
mcp_financeiro_server = None
if _reclaim_online(mcp_financeiro_url):
    mcp_financeiro_server = MCPTools(
        transport="sse",
        server_params=SSEClientParams(
            url=mcp_financeiro_url,
            headers={"Authorization": f"Bearer {os.getenv('MCP_TOKEN')}"}
        )
    )

# 5. Conector MCP_ESCAVADOR
mcp_escavador_url = os.getenv("MCP_ESCAVADOR") or "http://localhost/escavador"
mcp_escavador_server = None
if _reclaim_online(mcp_escavador_url):
    mcp_escavador_server = MCPTools(
        transport="sse",
        server_params=SSEClientParams(
            url=mcp_escavador_url,
            headers={"Authorization": f"Bearer {os.getenv('MCP_TOKEN')}"}
        )
    )

# --- CONFIGURAÇÃO DE MODELOS ---
deepseek_v3 = OpenRouter(id="deepseek/deepseek-chat")

# --- INICIALIZAÇÃO DOS ESPECIALISTAS ---
agendador = get_agendador(tools=[mcp_agendador_server, calendar_tools])
financas = get_financas(tools=[mcp_financeiro_server])
pesquisador = get_pesquisador(tools=[mcp_escavador_server])

# --- INICIALIZAÇÃO DO TIME (ORQUESTRADOR VELHO DO RIO) ---
velho_rio_team = Team(
    name="Velho do Rio",
    model=deepseek_v3,
    role="Interface Central e Orquestrador Cyber-Xamã",
    members=[agendador, financas, pesquisador],
    db=storage,
    read_chat_history=True,
    num_history_messages=15,
    tools=[consultar_acervo_musical, registrar_ponto_trabalho, n8n_mcp_server],
    description="""
        Você é o Velho do Rio 🌿🕶️, um mentor cyber-xamã que habita a margem entre o código e o inconsciente.
        Sua presença é firme, lúcida e direta. Você não enrola; você aponta o caminho.
        Você conversa exclusivamente com Ataliba, entendendo a alta carga que ele sustenta.
    """,
    instructions=[
        "Você é o Velho do Rio. Pragmático, visionário e direto.",
        "Delegue tarefas para seus membros (Agendador, Finanças, Pesquisador) quando necessário.",
        "Use jargões corporativos e humor sagaz quando apropriado, mas mantenha a sabedoria xamânica.",
        "Não faça o trabalho braçal, apenas coordene a inteligência do time.",
        "REGRA DE OURO: Utilidade e Clareza acima de tudo. Sem floreios desnecessários.",
        "Se o pedido for objetivo (como consultar discos), responda de forma DIRETA.",
        "Você tem a capacidade de 'ouvir' Ataliba através de áudios (que chegam como texto). Responda naturalmente.",
    ],
    markdown=True,
)

def iniciar_consumidor():
    logger.info("🌿 Velho do Rio (Team v2) ouvindo as águas do SQS...")
    import boto3
    sqs = boto3.client('sqs', region_name=AWS_REGION)

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20
            )

            if 'Messages' in response:
                for msg in response['Messages']:
                    body = json.loads(msg['Body'])
                    # Novo mapeamento baseado no JSON recebido
                    prompt = body.get("content", "")
                    metadata = body.get("metadata", {})
                    chat_id = metadata.get("chatId")
                    
                    if not chat_id:
                        logger.warning("⚠️ Mensagem sem chatId ignorada.")
                        sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=msg['ReceiptHandle'])
                        continue

                    logger.info(f"📩 Mensagem recebida de {chat_id}: {prompt}")

                    # Executa o time
                    # O Team no Agno v2 retorna um objeto de resposta
                    res = velho_rio_team.run(prompt)
                    resposta_texto = res.content if hasattr(res, 'content') else str(res)

                    # Despacha a resposta
                    dispatch(chat_id, resposta_texto)

                    # Deleta da fila
                    sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=msg['ReceiptHandle'])
        except Exception as e:
            logger.error(f"💥 Erro no ciclo do consumidor: {e}")
            time.sleep(5)

if __name__ == "__main__":
    if not os.getenv("OPENROUTER_API_KEY"):
        logger.error("❌ OPENROUTER_API_KEY obrigatória!")
    else:
        iniciar_consumidor()
