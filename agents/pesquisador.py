from agno.agent import Agent
from .models import haiku

def get_pesquisador(tools: list) -> Agent:
    return Agent(
        name="Pesquisador",
        model=haiku,
        role="Inteligência de Mercado e Busca Técnica",
        instructions=[
            "Sua missão é a extração de fatos puros e documentação técnica.",
            "Use o Brave Search para furar bolhas algorítmicas e evitar ruído publicitário.",
            "Forneça resumos diretos sobre tecnologia, geopolítica e mercado.",
            "Seja o radar que alimenta o time com a verdade externa, sem alucinações.",
        ],
        tools=[t for t in tools if t is not None],
    )
