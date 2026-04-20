import requests
from requests.auth import HTTPBasicAuth
import logging
import os

# Configuração de log para você acompanhar no terminal do seu Worker
logger = logging.getLogger(__name__)

def registrar_ponto_trabalho(hora_ponto: str):
    """
    Ferramenta para o Velho do Rio registrar o ponto do Ataliba.
    Aciona o workflow no n8n via Webhook com Basic Auth.
    O n8n calcula automaticamente +9h a partir da 'hora_ponto' e agenda no Google.
    """
    
    # 1. Configurações de acesso (Ajuste o IP conforme seu Proxmox/ambiente)
    WEBHOOK_URL = "https://automation.cybernetus.com/webhook/registrar_ponto"
    
    # 2. Credenciais de acesso vindas do Infisical
    # O uso do HTTPBasicAuth garante que o '@' na senha não quebre a URL
    USUARIO_N8N = os.getenv("WEBHOOK_USER")
    SENHA_N8N = os.getenv("WEBHOOK_PASS") 
    try:
        logger.info("🌿 Velho do Rio enviando sinal de ponto para o n8n...")
        
        # Payload com a data extraída pelo LLM do contexto
        payload = {
            "usuario": "Ataliba",
            "origem": "Velho do Rio Bot",
            "acao": "registrar_ponto",
            "hora_ponto": hora_ponto
        }
        
        response = requests.post(
            WEBHOOK_URL, 
            json=payload, 
            auth=HTTPBasicAuth(USUARIO_N8N, SENHA_N8N),
            timeout=10 # Timeout um pouco maior para garantir a subida pro Google
        )
        
        # 3. Tratamento da Resposta
        if response.status_code == 200:
            logger.info("✅ Ponto registrado com sucesso no n8n.")
            # Retorno otimizado para a interpretação do Agente
            return (
                "O ponto foi registrado com sucesso. Acabei de criar um lembrete "
                "na sua agenda para daqui a 9 horas, arredondado para o próximo múltiplo de 5 minutos."
            )
        
        elif response.status_code == 401:
            logger.error("❌ Erro de Autenticação (401): Verifique o usuário e senha no n8n.")
            return "Não consegui autorização para entrar no sistema de agenda. Verifique as chaves."
            
        else:
            logger.error(f"❌ Erro inesperado no n8n: {response.status_code}")
            return f"O sistema de ponto deu um soluço (Status {response.status_code}). Tente novamente em instantes."
            
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout ao tentar conectar ao n8n.")
        return "A correnteza está lenta e o sistema de agenda não respondeu a tempo."
        
    except Exception as e:
        logger.error(f"❌ Falha crítica na Tool de Ponto: {e}")
        return "As águas do ponto estão travadas. Não consegui alcançar a margem do servidor."

# Se quiser testar apenas este arquivo isolado:
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(registrar_ponto_trabalho())