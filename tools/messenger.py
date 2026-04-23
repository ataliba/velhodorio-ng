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

    # Validação básica do chat_id
    if not chat_id or not chat_id.lstrip('-').isdigit():
        logger.error(f"❌ Telegram: chat_id inválido: {chat_id}")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Limpa o texto de caracteres problemáticos para Markdown
    text_clean = text.replace('\x00', '').strip()
    
    payload = {
        "chat_id": chat_id,
        "text": text_clean,
    }
    
    # Usa Markdown apenas se o texto não tiver caracteres especiais problemáticos
    # Caracteres que podem causar 400: _ * [ ] ( ) ~ ` > # + - = | { } .
    markdown_chars = {'_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.'}
    if text_clean and not any(c in text_clean for c in markdown_chars):
        payload["parse_mode"] = "Markdown"
    
    logger.debug(f"📤 Telegram payload: chat_id={chat_id}, text_len={len(text_clean)}, parse_mode={payload.get('parse_mode', 'None')}")

    try:
        resp = requests.post(url, json=payload, timeout=15)
        
        # Log detalhado para debug
        if resp.status_code != 200:
            try:
                error_data = resp.json()
                logger.error(f"❌ Telegram API error: {error_data}")
            except:
                logger.error(f"❌ Telegram response: {resp.text[:500]}")
        
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
    Roteador central. Prioriza o envio de áudio se disponível. 
    Se o áudio falhar ou não existir, envia o texto como fallback.
    """
    target_id = chat_id
    if source == "telegram":
        # Prioriza o ID numérico do Infisical para evitar erros com usernames no envio de voz
        target_id = os.getenv("TELEGRAM_CHAT") or chat_id
    
    if not target_id:
        logger.error(f"❌ Destinatário ausente para o canal {source}")
        return False

    logger.info(f"📤 Despachando para {source} | Destino: {target_id}")

    # 1. Tentativa de envio de Áudio (se disponível)
    if audio_path and os.path.exists(audio_path):
        logger.info(f"🎙️ Tentando envio de áudio para {source}...")
        audio_ok = False
        if source == "evolution":
            audio_ok = send_audio_evolution(target_id, audio_path)
        elif source == "telegram":
            audio_ok = send_audio_telegram(target_id, audio_path)
        
        # Se o áudio foi enviado com sucesso, encerramos aqui para evitar duplicidade
        if audio_ok:
            return True
        else:
            logger.warning(f"⚠️ Falha no envio do áudio para {source}, recorrendo ao texto...")

    # 2. Envio de Texto (Fallback ou Mensagem Original de Texto)
    if source == "evolution":
        return send_evolution(target_id, text)
    elif source == "telegram":
        return send_telegram(target_id, text)
    
    return False
