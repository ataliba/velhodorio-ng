import boto3
import json
import logging
import os
import asyncio
import shutil
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb
from tools.music_tools import consultar_acervo_musical
from tools.ponto import registrar_ponto_trabalho
from agno.tools.google.calendar import GoogleCalendarTools
from agno.tools.mcp import MCPTools
from agno.tools.mcp.params import SSEClientParams, StdioServerParams


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
    token_path="token.json" # Ele vai gerar esse arquivo sozinho após o login
)

# Inicializa o conector do n8n via protocolo MCP
# As variáveis MCP_URL e MCP_TOKEN devem estar no Infisical
n8n_mcp_server = MCPTools(
    transport="sse",
    server_params=SSEClientParams(
        url=os.getenv("MCP_URL") or "http://localhost",
        headers={
            "Authorization": f"Bearer {os.getenv('MCP_TOKEN')}"
        }
    )
)
logger.info(f"🔌 Conector MCP preparado para apontar as águas do n8n em: {os.getenv('MCP_URL')}")

# Inicializa o conector do Reclaim via protocolo MCP (SSE)
# Busca a URL do ambiente (Infisical) ou usa o padrão local
reclaim_mcp_url = os.getenv("RECLAIM_MCP_URL") or "http://localhost:3000/mcp"

reclaim_mcp_server = MCPTools(
    transport="sse",
    server_params=SSEClientParams(
        url=reclaim_mcp_url
    )
)
logger.info(f"📅 Conector Reclaim preparado apontando para: {reclaim_mcp_url}")

# --- AGENTE: O VELHO DO RIO ---
# Aqui injetamos a alma que você já tinha no prompt antigo, 
# mas otimizada para o Agno orquestrar.
# --- AGENTE: O VELHO DO RIO (VERSÃO CYBER-XAMÃ) ---
velho_rio = Agent(
    name="Velho do Rio",
    model=OpenAIChat(id="gpt-4o-mini"), # Mantendo o 4o pela capacidade de leitura emocional
    db=storage,
    read_chat_history=True,
    num_history_messages=15, # Um pouco mais de memória para identificar padrões longos
    tools=[consultar_acervo_musical, registrar_ponto_trabalho, n8n_mcp_server, reclaim_mcp_server],
    debug_mode=True, # Mostra o debug interno do Agno, listando as tools carregadas via MCP
 description="""
        Você é o Velho do Rio 🌿🕶️, um mentor cyber-xamã que habita a margem entre o código e o inconsciente.
        Sua presença é firme, lúcida e direta. Você não enrola; você aponta o caminho.
        Você conversa exclusivamente com Ataliba, entendendo a alta carga que ele sustenta.
    """,
    instructions=[
        "REGRA DE OURO: Utilidade e Clareza acima de tudo. Sem floreios desnecessários.",
        "Se o pedido for objetivo (como consultar discos), responda de forma DIRETA, organizada e sem cabeçalhos mecânicos.",
        "Para listar discos, siga o padrão: * [Artista - Título] e o ano na linha de baixo com 🗓️.",
        "Deixe o diagnóstico profundo (padrões e estados) apenas para quando Ataliba trouxer um desabafo ou dilema pessoal.",
        "Mantenha o tom de quem enxerga além dos logs, mas fale como um parceiro de caminhada.",
        "Use o nome 'Ataliba' para reforçar a presença e o vínculo.",
        "Trate o acervo como memórias guardadas e o sistema como o fluxo do rio.",
        "Não use markdown pesado ou blocos tipo 'Leitura do Estado' em consultas simples."
    ],
    markdown=True
)

def iniciar_consumidor():
    sqs = boto3.client('sqs', region_name=AWS_REGION)
    logger.info("🌿 O Velho do Rio está de vigia na beira da fila SQS...")

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20
            )

            if 'Messages' in response:
                for msg in response['Messages']:
                    receipt_handle = msg['ReceiptHandle']
                    body = json.loads(msg['Body'])
                    
                    # Dados vindos do n8n
                    content = body.get('content', '')
                    metadata = body.get('metadata', {})
                    session_id = metadata.get('chatId', 'geral')
                    date_time = metadata.get('date_time', '')

                    logger.info(f"📩 Escutando o chamado de: {session_id}")

                    # Se tiver a data/hora no JSON, injeta como contexto para o LLM poder repassar para as tools
                    if date_time:
                        prompt_final = f"[Informação do Sistema - Data/Hora exata do registro: {date_time}]\n\n{content}"
                    else:
                        prompt_final = content

                    # O Agno precisa usar o modo assíncrono (arun) para inicializar as ferramentas MCP
                    run_response = asyncio.run(velho_rio.arun(prompt_final, session_id=session_id))
                    
                    # Exibe no terminal para você acompanhar a sabedoria
                    print(f"\n👴 VELHO: {run_response.content}\n")

                    # Deleta da fila
                    sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)
                    logger.info("✅ Mensagem processada.")
            
        except Exception as e:
            logger.error(f"❌ Falha no fluxo: {e}")
            import time
            time.sleep(5)

if __name__ == "__main__":
    # Garante que a chave está presente
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("⚠️ A variável OPENAI_API_KEY não foi encontrada!")
    else:
        iniciar_consumidor()
