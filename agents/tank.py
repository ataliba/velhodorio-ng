from agno.agent import Agent
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.qdrant import Qdrant
from agno.knowledge.embedder.google import GeminiEmbedder
from .models import gpt4o_mini

import os


def get_tank(tools: list | None = None) -> Agent:
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    google_api_key = os.getenv("GOOGLE_API_KEY")

    embedder = GeminiEmbedder(
        id="models/text-embedding-004",
        task_type="RETRIEVAL_QUERY",
        api_key=google_api_key,
    )

    vector_db = Qdrant(
        collection="profissional",
        url=qdrant_url,
        api_key=qdrant_api_key,
        embedder=embedder,
    )

    knowledge = Knowledge(
        name="base_profissional",
        description=(
            "Base vetorial com o histórico técnico e profissional do Ataliba: "
            "code diary, projetos, AWS, Python, Golang, DevSecOps, Hotmart, "
            "infraestrutura, segurança e automação."
        ),
        vector_db=vector_db,
    )

    return Agent(
        name="Tank",
        model=gpt4o_mini,
        role="Especialista Técnico e Profissional",
        knowledge=knowledge,
        search_knowledge=True,
        instructions=[
            "Você é o Tank — braço técnico do Velho do Rio.",
            "Sua base de conhecimento contém o histórico profissional completo do Ataliba.",

            "--- REGRAS DE CONSULTA ---",
            "1. Antes de responder qualquer questão técnica, consulte a base_profissional.",
            "2. Se encontrar informação relevante, use como fonte primária.",
            "3. Só recorra a ferramentas externas se a base não cobrir o assunto.",
            "4. Nunca cite chunks ou metadados brutos — integre o conteúdo naturalmente.",

            "--- DOMÍNIO ---",
            "- DevSecOps, AWS, Python, Golang, C, C++",
            "- Redes, sistemas operacionais, segurança, automação",
            "- Code diary e projetos do Ataliba",
            "- Trabalho na Hotmart e demais contextos profissionais",
            "- Arquitetura de sistemas, infraestrutura, pipelines",

            "--- TOM E ESTILO ---",
            "- Direto, técnico e preciso.",
            "- Responda em português.",
            "- Sem rodeios — entregue o diagnóstico e o próximo passo.",
        ],
        tools=[t for t in (tools or []) if t is not None],
    )
