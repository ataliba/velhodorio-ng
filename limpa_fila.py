import boto3
import json
import logging
import time

# --- CONFIGURAÇÃO ---
# Mantendo os mesmos dados do velhodorio.py para garantir que limpe a fila correta.
SQS_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/485952611520/velhodorio-queue"
AWS_REGION = "us-east-1"

# --- LOGS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def limpa_fila():
    sqs = boto3.client('sqs', region_name=AWS_REGION)
    logger.info(f"🧹 Iniciando faxina na beira do rio (SQS)...")
    logger.info(f"🔗 Fila: {SQS_QUEUE_URL}")
    
    total_removidas = 0
    
    while True:
        try:
            # Recebe até 10 mensagens por vez
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=2,
                VisibilityTimeout=10 # Pequeno timeout pois vamos deletar logo em seguida
            )
            
            messages = response.get('Messages', [])
            if not messages:
                logger.info("✨ Nada mais para limpar. A correnteza está limpa!")
                break
                
            for msg in messages:
                # Opcional: Logar um resumo do que está sendo removido
                try:
                    body = json.loads(msg['Body'])
                    # Tenta pegar o conteúdo para mostrar no log
                    content = body[0].get('content', '') if isinstance(body, list) else body.get('content', 'Mensagem sem content')
                    logger.info(f"🗑️ Removendo: {content[:50]}...")
                except:
                    logger.info(f"🗑️ Removendo mensagem (formato desconhecido)...")

                sqs.delete_message(
                    QueueUrl=SQS_QUEUE_URL,
                    ReceiptHandle=msg['ReceiptHandle']
                )
                total_removidas += 1
                
        except Exception as e:
            logger.error(f"❌ Erro durante a limpeza: {e}")
            break

    logger.info(f"✅ Faxina concluída! Total de mensagens removidas: {total_removidas}")

if __name__ == "__main__":
    limpa_fila()
