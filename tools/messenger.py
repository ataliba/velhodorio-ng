import os
import logging
import requests

logger = logging.getLogger(__name__)


def send_evolution(chat_id: str, text: str) -> bool:
    """
    Envia uma mensagem de texto via Evolution API (WhatsApp).

    Variáveis de ambiente necessárias (Infisical):
        EVOLUTION_URL      → URL base da sua instância (ex: http://10.0.0.10:8080)
        EVOLUTION_INSTANCE → Nome da instância cadastrada na Evolution (ex: ataliba)
        EVOLUTION_API_KEY  → API Key de autenticação
    """
    base_url  = os.getenv("EVOLUTION_URL", "").rstrip("/")
    instance  = os.getenv("EVOLUTION_INSTANCE", "")
    api_key   = os.getenv("EVOLUTION_API_KEY", "")

    if not all([base_url, instance, api_key]):
        logger.error("❌ Evolution API: variáveis EVOLUTION_URL, EVOLUTION_INSTANCE ou EVOLUTION_API_KEY não configuradas.")
        return False

    url = f"{base_url}/message/sendText/{instance}"
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "number": chat_id,
        "text": text
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        logger.info(f"📱 Evolution: mensagem enviada para {chat_id} (status {resp.status_code})")
        return True
    except requests.RequestException as e:
        logger.error(f"❌ Evolution: falha ao enviar para {chat_id}: {e}")
        return False


def send_telegram(chat_id: str, text: str) -> bool:
    """
    Envia uma mensagem de texto via Telegram Bot API.

    Variáveis de ambiente necessárias (Infisical):
        TELEGRAM_BOT_TOKEN → Token do bot (@BotFather)

    O chat_id deve ser o ID numérico do chat/usuário no Telegram.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    if not token:
        logger.error("❌ Telegram: variável TELEGRAM_BOT_TOKEN não configurada.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        logger.info(f"✈️ Telegram: mensagem enviada para {chat_id} (status {resp.status_code})")
        return True
    except requests.RequestException as e:
        logger.error(f"❌ Telegram: falha ao enviar para {chat_id}: {e}")
        return False


def dispatch(source: str, chat_id: str, text: str) -> bool:
    """
    Roteador central. Decide o canal com base no campo 'source' do JSON.

    Args:
        source  : "evolution" ou "telegram"
        chat_id : destinatário (formato varia por canal)
        text    : conteúdo da resposta gerada pelo agente
    """
    if source == "evolution":
        return send_evolution(chat_id, text)
    elif source == "telegram":
        return send_telegram(chat_id, text)
    else:
        logger.warning(f"⚠️ Canal desconhecido: '{source}'. Nenhuma mensagem enviada.")
        return False
