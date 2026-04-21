from agno.models.openrouter import OpenRouter

# --- CONFIGURAÇÃO DE MODELOS (VIA OPENROUTER) ---
# DeepSeek-V3: Eficiência e estruturação de dados
deepseek_v3 = OpenRouter(id="deepseek/deepseek-chat")

# DeepSeek-R1: Raciocínio profundo para finanças
deepseek_r1 = OpenRouter(id="deepseek/deepseek-r1")

# Claude 3.5 Haiku: Velocidade para síntese de pesquisa
haiku = OpenRouter(id="anthropic/claude-3-5-haiku")
