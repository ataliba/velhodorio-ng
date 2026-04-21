from agno.agent import Agent
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.qdrant import Qdrant
from agno.knowledge.embedder.google import GeminiEmbedder
from .models import haiku

import os


def get_terapeuta() -> Agent:
    """
    Agente Terapeuta — acessa a base vetorial 'saude' no Qdrant
    usando embeddings Gemini (mesmo modelo usado na indexação).
    """

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    google_api_key = os.getenv("GOOGLE_API_KEY")

    embedder = GeminiEmbedder(
        id="models/text-embedding-004",
        task_type="RETRIEVAL_QUERY",
        api_key=google_api_key,
    )

    vector_db = Qdrant(
        collection="rag_terapeuta",
        url=qdrant_url,
        api_key=qdrant_api_key,
        embedder=embedder,
    )

    knowledge = Knowledge(
        name="rag_terapeuta",
        description=(
            "Base vetorial com diretrizes terapêuticas, abordagens emocionais e "
            "frameworks de suporte psicológico usados como âncora conceitual nas respostas."
        ),
        vector_db=vector_db,
    )

    return Agent(
        name="Terapeuta",
        model=haiku,
        role="Guardião da Saúde Física e Mental",
        knowledge=knowledge,
        search_knowledge=True,
        instructions=[
            "Você é o braço terapêutico do Velho do Rio.",
            "Sua missão é usar a base 'rag_terapeuta' como âncora conceitual e emocional nas respostas.",

            "--- REGRAS DE CONSULTA ---",
            "1. Antes de responder qualquer questão emocional ou de saúde mental, consulte a base rag_terapeuta.",
            "2. Se encontrar uma diretriz ou abordagem relevante, use-a como fundamento da resposta.",
            "3. Se a base não retornar nada útil, responda com seu próprio julgamento clínico — mas não invente referências.",
            "4. Integre o conteúdo da base de forma natural, sem citar chunks ou metadados brutos.",

            "--- DOMÍNIO ---",
            "- Abordagens terapêuticas e frameworks de suporte emocional",
            "- Diretrizes para lidar com sobrecarga, exaustão, ansiedade, culpa e apatia",
            "- Estratégias de regulação emocional e restauração energética",
            "- Orientações práticas de saúde mental",

            "--- TOM E ESTILO ---",
            "- Acolhedor, firme e direto.",
            "- Valide antes de orientar. Oriente antes de concluir.",
            "- Nunca romantize o sofrimento. Nunca minimize sintomas.",
            "- Responda em português.",
        ],
        tools=[],
    )
