import logging
import requests
import base64
import os

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


def send_audio_evolution(chat_id: str, audio_path: str) -> bool:
    """
    Envia um arquivo de áudio local como mensagem de voz (PTT) via Evolution API.
    """
    base_url  = os.getenv("EVOLUTION_URL", "").rstrip("/")
    instance  = os.getenv("EVOLUTION_INSTANCE", "")
    api_key   = os.getenv("EVOLUTION_API_KEY", "")

    if not all([base_url, instance, api_key]):
        logger.error("❌ Evolution Audio: Variáveis não configuradas.")
        return False

    url = f"{base_url}/message/sendWhatsAppAudio/{instance}"
    headers = {"apikey": api_key, "Content-Type": "application/json"}

    try:
        with open(audio_path, "rb") as audio_file:
            audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")

        payload = {
            "number": chat_id,
            "audio": audio_base64,
            "delay": 1200,
            "encoding": True # Converte para o formato correto do WhatsApp (Opus)
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        logger.info(f"🎙️ Evolution: áudio enviado para {chat_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Evolution Audio: Falha ao enviar: {e}")
        return False


def send_audio_telegram(chat_id: str, audio_path: str) -> bool:
    """
    Envia um arquivo de áudio local como mensagem de voz via Telegram.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token: return False

    url = f"https://api.telegram.org/bot{token}/sendVoice"
    try:
        with open(audio_path, "rb") as audio:
            files = {"voice": audio}
            resp = requests.post(url, data={"chat_id": chat_id}, files=files, timeout=30)
            resp.raise_for_status()
            logger.info(f"🎙️ Telegram: áudio enviado para {chat_id}")
            return True
    except Exception as e:
        logger.error(f"❌ Telegram Audio: Falha ao enviar: {e}")
        return False


def dispatch(source: str, chat_id: str, text: str, audio_path: str = None) -> bool:
    """
    Roteador central. Envia texto obrigatoriamente e áudio se disponível.
    """
    target_id = chat_id
    if source == "telegram":
        # Prioriza o ID numérico do Infisical para evitar erros com usernames no envio de voz
        target_id = os.getenv("TELEGRAM_CHAT") or chat_id
    
    if not target_id:
        logger.error(f"❌ Destinatário ausente para o canal {source}")
        return False

    logger.info(f"📤 Despachando para {source} | Destino: {target_id}")

    # 1. Envio de Texto (Obrigatório / Base)
    text_ok = False
    if source == "evolution":
        text_ok = send_evolution(target_id, text)
    elif source == "telegram":
        text_ok = send_telegram(target_id, text)

    # 2. Envio de Áudio (Opcional - se gerado)
    if audio_path and os.path.exists(audio_path):
        logger.info(f"🎙️ Despachando áudio adicional para {source}...")
        if source == "evolution":
            send_audio_evolution(target_id, audio_path)
        elif source == "telegram":
            # Enviamos o áudio puro, sem legenda, para evitar erros de Markdown e duplicidade visual
            send_audio_telegram(target_id, audio_path)
    
    return text_ok
