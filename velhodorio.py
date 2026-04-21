import boto3
import json
import logging
import os
import asyncio
import shutil
import requests as _requests
from elevenlabs import ElevenLabs, save
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

def _reclaim_online(url: str, timeout: int = 3) -> bool:
    """Verifica se o servidor Reclaim MCP está acessível."""
    try:
        # Bate na raiz do servidor (não na rota /mcp) para checar conectividade
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
logger.info(f"🔌 Conector MCP n8n preparado em: {os.getenv('MCP_URL')}")

# 2. Conector MCP_AGENDADOR (Todoist, Calendar, Jira)
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
    logger.info(f"📅 MCP Agendador online → {mcp_agendador_url}")
else:
    logger.warning(f"⚠️  MCP Agendador offline ou URL ausente ({mcp_agendador_url}) — agendador sobe sem as tools de Todoist/Jira.")

# 3. Conector Reclaim (SSE)
reclaim_mcp_url = os.getenv("RECLAIM_URL") or "http://localhost:3000/mcp"
reclaim_mcp_server = None
if _reclaim_online(reclaim_mcp_url):
    reclaim_mcp_server = MCPTools(
        transport="sse",
        server_params=SSEClientParams(url=reclaim_mcp_url)
    )
    logger.info(f"📅 Reclaim MCP online → {reclaim_mcp_url}")
else:
    logger.warning(f"⚠️  Reclaim MCP offline em {reclaim_mcp_url} — agente sobe sem ele.")

# 4. Conector MCP_FINANCEIRO (Cripto, FastAPI Trader)
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
    logger.info(f"💰 MCP Financeiro online → {mcp_financeiro_url}")
else:
    logger.warning(f"⚠️  MCP Financeiro offline ou URL ausente ({mcp_financeiro_url}) — agente de finanças sobe sem as tools de Trading.")

# 5. Conector MCP_ESCAVADOR (Pesquisa Técnica)
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
    logger.info(f"🕵️‍♂️ MCP Escavador online → {mcp_escavador_url}")
else:
    logger.warning(f"⚠️  MCP Escavador offline ou URL ausente ({mcp_escavador_url}) — pesquisador sobe sem as tools de busca.")

# --- CONFIGURAÇÃO DO LÍDER (O VELHO DO RIO) ---
deepseek_v3 = OpenRouter(id="deepseek/deepseek-chat")

leader = Agent(
    name="Velho do Rio",
    model=deepseek_v3,
    role="Interface Central e Orquestrador",
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
        "Delegue tarefas para os especialistas (Agendador, Finanças, Pesquisador) quando necessário.",
        "Use jargões corporativos e humor sagaz quando apropriado, mas mantenha a sabedoria xamânica.",
        "Não faça o trabalho braçal, apenas coordene a inteligência do time.",
        "REGRA DE OURO: Utilidade e Clareza acima de tudo. Sem floreios desnecessários.",
        "Se o pedido for objetivo (como consultar discos), responda de forma DIRETA.",
        "Você tem a capacidade de 'ouvir' Ataliba através de áudios (que chegam como texto). Responda naturalmente.",
    ],
    markdown=True,
    add_history_to_messages=True,
)

# 1. Criamos os especialistas passando as ferramentas necessárias
agendador = get_agendador(tools=[mcp_agendador_server, calendar_tools])
financas = get_financas(tools=[mcp_financeiro_server])
pesquisador = get_pesquisador(tools=[mcp_escavador_server])

# 2. Montamos o time
velho_rio_team = Team(
    leader=leader,
    members=[agendador, financas, pesquisador],
    show_tool_calls=True,
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
                    raw_body = json.loads(msg['Body'])
                    
                    # Trata se o n8n mandar uma lista [ { ... } ] ou objeto direto { ... }
                    body = raw_body[0] if isinstance(raw_body, list) else raw_body

                    # Extração seguindo a estrutura de metadata/content
                    content    = body.get('content', '')
                    metadata   = body.get('metadata', {})
                    
                    session_id   = metadata.get('sessionId') or metadata.get('chatId', 'geral')
                    chat_id      = metadata.get('chatId', '')
                    source       = metadata.get('source', '')
                    date_time    = metadata.get('date_time', '')
                    message_type = metadata.get('messageType', 'text') # Novo campo

                    logger.info(f"📩 Chamado de: {session_id} | Canal: {source} | Tipo: {message_type}")

                    # Prepara o contexto do sistema
                    system_context = []
                    if date_time:
                        system_context.append(f"Horário: {date_time}")
                    if message_type == 'audio':
                        system_context.append("Mensagem enviada via ÁUDIO (transcrita)")

                    prompt_final = content
                    if system_context:
                        prompt_final = f"[Informação do Sistema - {', '.join(system_context)}]\n\n{content}"

                    # O Agno Team processa a resposta
                    run_response = asyncio.run(velho_rio_team.arun(prompt_final, session_id=str(session_id)))
                    resposta = run_response.content

                    # Geração de Voz (ElevenLabs)
                    audio_path = None
                    eleven_api_key = os.getenv("ELEVENLABS_API_KEY")
                    
                    # Decisão: Gera áudio se a API KEY estiver presente 
                    # E se a entrada foi áudio OU se você quiser áudio sempre
                    gerar_audio = (message_type == 'audio' or os.getenv("VOICE_ALWAYS", "false") == "true")
                    
                    if eleven_api_key and resposta and gerar_audio:
                        try:
                            logger.info("🎙️ Gerando voz da sabedoria...")
                            client = ElevenLabs(api_key=eleven_api_key)
                            voice_id = os.getenv("ELEVENLABS_VOICE_ID") or "pNInz6obpg8ndclJ9tq9" 
                            
                            audio_gen = client.text_to_speech.convert(
                                text=resposta,
                                voice_id=voice_id,
                                model_id="eleven_multilingual_v2"
                            )
                            
                            audio_path = f"temp_voice_{session_id}.mp3"
                            save(audio_gen, audio_path)
                        except Exception as ve:
                            logger.error(f"❌ Falha ao gerar voz: {ve}")

                    # Exibe no terminal para acompanhamento
                    print(f"\n👴 VELHO: {resposta}\n")

                    # Despacha a resposta para o canal de origem (Texto + Áudio)
                    if source and chat_id:
                        dispatch(source, chat_id, resposta, audio_path=audio_path)
                    else:
                        logger.warning("⚠️ 'source' ou 'chatId' ausente no metadata — resposta não enviada ao canal.")

                    # Limpeza do arquivo temporário
                    if audio_path and os.path.exists(audio_path):
                        os.remove(audio_path)


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
