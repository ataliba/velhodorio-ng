# 📜 Changelog - Velho do Rio

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

## [1.5.0] - 2026-04-21

### ✨ Adicionado
- **AgentOS (`app.py`)**: O time agora pode ser servido como API REST FastAPI via `agno.os.AgentOS` na porta `7777`. Inclui Swagger, streaming SSE, histórico por sessão e tracing. Independente do consumidor SQS.
- **Systemd unit files**: `velhodorio.service` e `velhodorio-agentos.service` prontos para deploy em Debian/Ubuntu.
- **Persistência PostgreSQL**: Suporte a PostgreSQL como backend de sessões. Se `POSTGRES_URL`, `POSTGRES_USER` e `POSTGRES_PASS` estiverem definidos no Infisical, o Postgres é usado automaticamente — senão cai no SQLite como fallback.

### 🛠️ Alterado
- **Padrão `_connect()` para MCPs**: Substituído o padrão `async with` aninhado por um helper `_connect()` que tenta cada MCP individualmente. Falhas são isoladas — um MCP offline não derruba os outros nem o processo.
- **Reclaim MCP usa `streamable-http`**: Trocado o transport do Reclaim de `sse` para `streamable-http` com `StreamableHTTPClientParams`, compatível com o servidor `reclaim-mcp-server` de Erik MacKinnon.
- **`QDRANT_API_TOKEN` → `QDRANT_API_KEY`**: Corrigido o nome da variável de ambiente para bater com o que está no Infisical.
- **Import path do GeminiEmbedder**: Corrigido de `agno.knowledge.embedder.gemini` para `agno.knowledge.embedder.google` (nome real do módulo instalado).
- **`PostgresDb` usa `db_schema`**: Corrigido argumento `schema` → `db_schema` conforme API do Agno.
- **`ddgs` + `google-genai` + `psycopg[binary]` + `qdrant-client`**: Adicionadas dependências ao `requirements.txt`.

---

## [1.4.0] - 2026-04-21

### ✨ Adicionado
- **Agente Terapeuta**: Novo membro do time com acesso à base vetorial `rag_terapeuta` no Qdrant via embeddings Gemini (`models/text-embedding-004`). Atua como âncora terapêutica para questões emocionais e de saúde mental delegadas pelo orquestrador.
- **DuckDuckGo nativo no Pesquisador**: Integração com `DuckDuckGoTools` do Agno (lib `ddgs`), dando ao agente busca web e busca de notícias sem depender exclusivamente do MCP Escavador.

### 🛠️ Alterado
- **Arquitetura Async Completa (`velhodorio.py`)**: Refatorado para `asyncio`. Todos os `MCPTools` agora são inicializados via `async with` no startup, garantindo que a conexão SSE seja estabelecida de verdade antes de qualquer mensagem ser processada. O loop principal usa `arun()` em vez de `run()`.
- **`_null_ctx`**: Adicionado context manager nulo para MCPs offline, permitindo degradação graciosa sem `if/else` aninhados.
- **MCPs dos agentes secundários corrigidos**: `Agendador` agora recebe `reclaim_mcp_server` (que estava sendo criado mas nunca entregue). Todos os agentes especialistas recebem seus MCPs já com conexão ativa.
- **README atualizado**: Tabela de agentes com MCPs correspondentes, tabela completa de variáveis de ambiente, remoção de artefatos de edição (números de linha soltos), correção de `RECLAIM_MCP_URL` → `RECLAIM_URL`.

---

## [1.3.0] - 2026-04-21

### ✨ Adicionado
- **Arquitetura Multi-Agente (Agno Team)**: Transição de um único agente para um time de especialistas liderados pelo Velho do Rio.
- **Modelos OpenRouter**: Integração com DeepSeek V3, DeepSeek R1 e Claude 3.5 Haiku para diferentes especialidades.
- **Agentes Especialistas**:
    - `Agendador`: Gerenciamento de produtividade e Reclaim.io.
    - `Finanças`: Estrategista de ativos e cripto (DeepSeek R1).
    - `Pesquisador`: Inteligência de mercado e documentação (Claude Haiku).
- **Orquestração Inteligente**: O Velho do Rio agora atua como interface central, delegando tarefas complexas para o time.

---

## [1.2.0] - 2026-04-21

### ✨ Adicionado
- **Ferramenta de Limpeza de Fila (`limpa_fila.py`)**: Script utilitário para consumir e descartar mensagens da fila SQS rapidamente durante fases de teste.

### 🛠️ Alterado
- **ElevenLabs SDK v2**: Atualizada a integração de voz para compatibilidade com a versão 2.x da SDK da ElevenLabs (uso de `client.text_to_speech.convert`).
- **Otimização de Mensageria**: Refatorado o roteador de mensagens (`dispatch`) para evitar o envio duplo (Texto + Áudio). Agora o texto é enviado primeiro, seguido do áudio em um balão separado para garantir a entrega e evitar erros de Markdown no Telegram.
- **Economia de ElevenLabs**: Geração de áudio agora é desabilitada por padrão para mensagens de texto (`VOICE_ALWAYS` default `false`), economizando créditos da API.
- **Correção Telegram 400**: Resolvido erro de "Bad Request" no Telegram ao remover legendas (captions) problemáticas em mensagens de voz.

---

## [1.1.0] - 2026-04-20

### ✨ Adicionado
- **Arquitetura Distribuída para MCP**: Suporte a servidores MCP rodando via HTTP/SSE em máquinas ou containers separados.
- **Script de Setup do Agente (`setup_velhodorio.sh`)**: Automação completa de instalação do ambiente Python e serviços systemd para o Agente.
- **Script de Setup do Reclaim MCP (`setup_mcp_reclaim.sh`)**: Script independente para instalar Node.js e o servidor Reclaim MCP em qualquer máquina da rede.
- **Integração com Reclaim.ai**: O Velho do Rio agora possui ferramentas para gerenciar calendário e tarefas diretamente via MCP.

### 🛠️ Alterado
- **Portabilidade do Agente**: `velhodorio.py` agora detecta dinamicamente o caminho do Node e utiliza a variável de ambiente `RECLAIM_MCP_URL`.
- **Arquitetura Nativa (Debian)**: Substituída a dependência do PM2 pelo Systemd nativo para maior estabilidade e integração com o Debian 13.
- **Scripts de Setup Robustos**: Atualizados para suportar Debian/Ubuntu como alvo principal e Alpine como fallback.
- **README Atualizado**: Novas seções sobre instalação automatizada e arquitetura distribuída.

### 🔒 Segurança
- **Segredos via Infisical**: Reforçada a injeção de variáveis sensíveis (`RECLAIM_TOKEN`, etc) via serviços systemd usando o CLI do Infisical.

---
## [1.0.0] - 2026-04-19
- Versão inicial estável do Velho do Rio com suporte a SQS, n8n MCP e consulta de acervo musical.
