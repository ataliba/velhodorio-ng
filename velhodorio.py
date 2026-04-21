import boto3
import json
import logging
import os
import asyncio
import shutil
import requests as _requests
from elevenlabs import ElevenLabs, save
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb
from tools.music_tools import consultar_acervo_musical
from tools.messenger import dispatch
from tools.ponto import registrar_ponto_trabalho
from agno.tools.google.calendar import GoogleCalendarTools
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters
from agno.tools.mcp.params import SSEClientParams


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
# Faz um health check antes para não travar o agente se o servidor estiver offline
reclaim_mcp_url = os.getenv("RECLAIM_URL") or "http://localhost:3000/mcp"

def _reclaim_online(url: str, timeout: int = 3) -> bool:
    """Verifica se o servidor Reclaim MCP está acessível."""
    try:
        # Bate na raiz do servidor (não na rota /mcp) para checar conectividade
        base = url.rsplit("/mcp", 1)[0]
        _requests.get(base, timeout=timeout)
        return True
    except Exception:
        return False

reclaim_mcp_server = None
if _reclaim_online(reclaim_mcp_url):
    reclaim_mcp_server = MCPTools(
        transport="sse",
        server_params=SSEClientParams(url=reclaim_mcp_url)
    )
    logger.info(f"📅 Reclaim MCP online → {reclaim_mcp_url}")
else:
    logger.warning(f"⚠️  Reclaim MCP offline ou inacessível em {reclaim_mcp_url} — agente sobe sem ele.")

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
    tools=[t for t in [consultar_acervo_musical, registrar_ponto_trabalho, n8n_mcp_server, reclaim_mcp_server] if t is not None],
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
        "Não use markdown pesado ou blocos tipo 'Leitura do Estado' em consultas simples.",
        "Você tem a capacidade de 'ouvir' Ataliba através de áudios (que chegam como texto). Responda naturalmente, sabendo que sua voz será sintetizada de volta para ele."
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

                    # O Agno processa a resposta
                    run_response = asyncio.run(velho_rio.arun(prompt_final, session_id=str(session_id)))
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
