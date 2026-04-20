from pymongo import MongoClient
import logging
import os

# Configura o logger para este arquivo
logger = logging.getLogger(__name__)

def consultar_acervo_musical(termo: str):
    """
    Consulta o acervo de discos no MongoDB do Ataliba.
    """
    logger.info(f"🔍 Tool iniciada: Buscando por '{termo}'...")
    
    try:
        # Busca credenciais do ambiente (Infisical)
        mongo_user = os.getenv("MONGODB_USER")
        mongo_pass = os.getenv("MONGODB_PASS")
        
        # Coloquei o timeout bem curto para não travar o SQS se for rede
        MONGO_URI = f"mongodb://{mongo_user}:{mongo_pass}@192.168.68.38:27017/n8n"
        
        logger.info(f"🔌 Tentando conectar em: 192.168.68.38:27017")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        
        # O comando 'server_info' força a conexão imediata para testar o Auth/Rede
        client.server_info() 
        logger.info("✅ Conexão estabelecida com sucesso!")

        db = client["n8n"]
        collection = db["DiscogsControl"]

        query = {
            "$or": [
                {"artist": {"$regex": termo, "$options": "i"}},
                {"title": {"$regex": termo, "$options": "i"}},
                {"folder": {"$regex": termo, "$options": "i"}}
            ]
        }
        
        logger.info(f"🔎 Executando query no banco...")
        resultados = list(collection.find(query).limit(10))
        logger.info(f"📊 Documentos encontrados: {len(resultados)}")

        if not resultados:
            return f"Percorri as águas e não encontrei nada sobre '{termo}'."

        lista = [f"💿 {r.get('artist')} - {r.get('title')} ({r.get('released')})" for r in resultados]
        return "Registros encontrados:\n" + "\n".join(lista)

    except Exception as e:
        # ISSO AQUI vai cuspir o erro real no seu terminal do Antigravity
        logger.error(f"❌ ERRO CRÍTICO NA TOOL: {type(e).__name__} - {str(e)}")
        # Retorna o erro para a LLM saber o que houve
        return f"Erro técnico na tool: {str(e)}"