# 📜 Changelog - Velho do Rio

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

---

## [0.6.0] - 2026-04-26

### ✨ Adicionado
- **Agente Tank**: Novo especialista técnico e profissional. Acessa base vetorial `profissional` no Qdrant via embeddings Gemini. Domínio: DevSecOps, AWS, Python, Golang, Hotmart, infraestrutura e code diary.
- **Slot MCP_TANK**: Tank aceita MCP técnico opcional (ex: Kiro/AWS docs). Se ausente, sobe apenas com Qdrant.

### 🗑️ Removido
- **AgentOS (`app.py`)**: Removida a camada REST API FastAPI. O projeto roda exclusivamente como consumidor SQS. `velhodorio-agentos.service` também removido.

### 📝 Documentação
- README e CLAUDE.md atualizados com Tank na tabela de agentes e `MCP_TANK` nas variáveis de ambiente.

---

## [0.5.0] - 2026-04-21

### ✨ Adicionado
- **AgentOS (`app.py`)**: Time servido como API REST FastAPI via `agno.os.AgentOS` na porta `7777`. Inclui Swagger, streaming SSE, histórico por sessão e tracing.
- **Systemd unit files**: `velhodorio.service` e `velhodorio-agentos.service` prontos para deploy em Debian/Ubuntu.
- **Persistência PostgreSQL**: Suporte a PostgreSQL como backend de sessões. Fallback automático para SQLite se variáveis ausentes.

### 🛠️ Alterado
- **Padrão `_connect()` para MCPs**: Substituído `async with` aninhado por helper `_connect()` que isola falhas por MCP.
- **Reclaim MCP usa `streamable-http`**: Trocado transport de `sse` para `streamable-http` com `StreamableHTTPClientParams`.
- **`QDRANT_API_TOKEN` → `QDRANT_API_KEY`**: Corrigido nome da variável para bater com Infisical.
- **Import path do GeminiEmbedder**: Corrigido de `agno.knowledge.embedder.gemini` para `agno.knowledge.embedder.google`.
- **`PostgresDb` usa `db_schema`**: Corrigido argumento `schema` → `db_schema` conforme API do Agno.
- **Dependências**: `ddgs`, `google-genai`, `psycopg[binary]`, `qdrant-client` adicionadas ao `requirements.txt`.

---

## [0.4.0] - 2026-04-21

### ✨ Adicionado
- **Agente Terapeuta**: Novo membro do time com acesso à base vetorial `rag_terapeuta` no Qdrant via embeddings Gemini (`models/text-embedding-004`).
- **DuckDuckGo nativo no Pesquisador**: Integração com `DuckDuckGoTools` do Agno, busca web independente do MCP Escavador.

### 🛠️ Alterado
- **Arquitetura Async Completa**: `velhodorio.py` refatorado para `asyncio`. MCPTools inicializados via `async with` no startup. Loop principal usa `arun()`.
- **`_null_ctx`**: Context manager nulo para MCPs offline — degradação graciosa sem `if/else` aninhados.
- **MCPs dos agentes corrigidos**: Agendador recebe `reclaim_mcp_server` corretamente. Todos os especialistas recebem MCPs com conexão ativa.

---

## [0.3.0] - 2026-04-21

### ✨ Adicionado
- **Arquitetura Multi-Agente (Agno Team)**: Transição de agente único para time de especialistas liderado pelo Velho do Rio.
- **Modelos OpenRouter**: DeepSeek V3, DeepSeek R1 e Claude 3.5 Haiku para diferentes especialidades.
- **Agentes Especialistas**: Agendador (produtividade + Reclaim), Finanças (cripto), Pesquisador (inteligência de mercado).

---

## [0.2.0] - 2026-04-21

### ✨ Adicionado
- **`limpa_fila.py`**: Script utilitário para consumir e descartar mensagens SQS durante testes.

### 🛠️ Alterado
- **ElevenLabs SDK v2**: Atualizada para `client.text_to_speech.convert`.
- **Mensageria**: `dispatch` refatorado para evitar envio duplo (texto + áudio em balões separados).
- **Economia de ElevenLabs**: Geração de áudio desabilitada por padrão (`VOICE_ALWAYS=false`).
- **Correção Telegram 400**: Removidas captions problemáticas em mensagens de voz.

---

## [0.1.0] - 2026-04-20

### ✨ Adicionado
- **Arquitetura MCP Distribuída**: Servidores MCP via HTTP/SSE em máquinas ou containers separados.
- **`setup_velhodorio.sh`**: Automação completa de instalação do ambiente Python e systemd.
- **`setup_mcp_reclaim.sh`**: Setup independente para Node.js e servidor Reclaim MCP.
- **Integração Reclaim.ai**: Gerenciamento de calendário e tarefas via MCP.

### 🛠️ Alterado
- **Portabilidade**: `velhodorio.py` detecta dinamicamente o caminho do Node, usa `RECLAIM_MCP_URL`.
- **Systemd nativo**: Substituída dependência do PM2 pelo Systemd (Debian 13).

### 🔒 Segurança
- **Segredos via Infisical**: Injeção de variáveis sensíveis via systemd + CLI Infisical.

---

## [0.0.1] - 2026-04-19

- Versão inicial estável do Velho do Rio com suporte a SQS, n8n MCP e consulta de acervo musical.
