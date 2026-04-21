# 🌿🕶️ Velho do Rio (Next Generation)

> *"A margem entre o código e o inconsciente."*

**Velho do Rio** é um agente de inteligência artificial autônomo, desenhado sob uma persona de um **"cyber-xamã"**. Ele atua como um mentor lúcido e direto, criado exclusivamente para auxiliar seu mantenedor nas atividades cotidianas e orquestrar de forma fluida os sistemas de automação de plano de fundo.

Construído em **Python**, usando o framework **[Agno v2](https://github.com/agno-ai/agno)**, o agente processa mensagens de forma assíncrona, consumindo chamadas diretamente de uma fila AWS SQS e interagindo com o mundo exterior (n8n, MongoDB, APIs) através de ferramentas e do protocolo **MCP** (Model Context Protocol).

---

## ✨ Características e Arquitetura

* **Arquitetura Multi-Agente (Agno Team):** O Velho do Rio lidera um time de especialistas, delegando tarefas de acordo com a necessidade.
* **Modelos Especializados (OpenRouter):** Todos os agentes utilizam **GPT-4o-mini** via OpenRouter — tool calling preciso, baixo custo e alta confiabilidade.
* **Conexão MCP com Degradação Graciosa:** Cada servidor MCP é conectado individualmente no startup via `_connect()`. Falhas são isoladas — um MCP offline não derruba os outros nem o processo.
* **Consumo de Filas (AWS SQS):** Trabalha de forma reativa e não-bloqueante consumindo payloads vindos do WhatsApp (API Evolution) e Telegram.
* **Segurança e Cofre de Segredos:** Configuração centralizada e segura utilizando o **Infisical**. Zero chaves ou credenciais em hardcode.
* **Persistência de Sessões:** Histórico conversacional armazenado por usuário (`chatId`) em **PostgreSQL** (recomendado) ou **SQLite** como fallback local.
* **Ferramentas Locais Customizadas:**
    * 🎵 `consultar_acervo_musical`: Consulta nativa no MongoDB da coleção de discos.
    * ⏱️ `registrar_ponto_trabalho`: Gatilho de automação n8n para ponto eletrônico.

---

## 🤖 Time de Agentes

| Agente | Modelo | Especialidade | MCPs / Knowledge |
|---|---|---|---|
| **Velho do Rio** (orquestrador) | GPT-4o-mini | Interface central, delega tarefas | n8n central |
| **Agendador** | GPT-4o-mini | Google Calendar, Todoist, Reclaim.io, Jira | `MCP_AGENDADOR`, `RECLAIM_URL` |
| **Finanças** | GPT-4o-mini | Cripto, CoinMarketCap, P&L | `MCP_FINANCEIRO` |
| **Pesquisador** | GPT-4o-mini | Busca web, inteligência de mercado | `MCP_ESCAVADOR` + DuckDuckGo nativo |
| **Terapeuta** | GPT-4o-mini | Suporte emocional e saúde mental | Qdrant `rag_terapeuta` (Gemini embeddings) |

---

## 🛠️ Utilitários de Desenvolvimento

* 🧹 `limpa_fila.py`: Script para "drenar" a fila SQS. Útil quando você insere dados de teste inválidos e quer limpar a fila sem que o agente os processe.
    ```bash
    python limpa_fila.py
    ```

---

## 🚀 Como Executar

### 📦 Instalação Automatizada (Recomendado)
Para facilitar a replicação em novos servidores ou containers (LXC Proxmox), utilize os scripts de setup:

*   **Agente**: `./setup_velhodorio.sh` (Instala apenas o Python e o Agente).
*   **Reclaim MCP**: `./setup_mcp_reclaim.sh` (Instala Node.js e o Servidor de Calendário).

---

### 1. Preparar o Ambiente Manualmente
Se preferir o modo manual:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Rodar o Agente via Infisical
```bash
infisical run -- python velhodorio.py
```

---

## 🐘 Configurando o PostgreSQL (Opcional)

Por padrão o agente usa SQLite local. Se `POSTGRES_URL`, `POSTGRES_USER` e `POSTGRES_PASS` estiverem definidos no Infisical, o Postgres é usado automaticamente.

### Criando o banco

```sql
-- Conecte como superusuário (ex: psql -U postgres)

-- 1. Cria o usuário
CREATE USER velhodorio WITH PASSWORD 'sua_senha_aqui';

-- 2. Cria o banco
CREATE DATABASE velhodorio OWNER velhodorio;

-- 3. Garante os privilégios
GRANT ALL PRIVILEGES ON DATABASE velhodorio TO velhodorio;

-- 4. (Postgres 15+) Garante acesso ao schema public
\c velhodorio
GRANT ALL ON SCHEMA public TO velhodorio;
```

O Agno cria as tabelas de sessão automaticamente no primeiro boot — não precisa rodar migrations.

### Configurando no Infisical

```
POSTGRES_URL  = postgresql://localhost:5432/velhodorio
POSTGRES_USER = velhodorio
POSTGRES_PASS = sua_senha_aqui
```

> A URL não deve conter usuário/senha — eles são injetados separadamente pelo código para evitar exposição em logs.

---

## 🖥️ AgentOS — API REST + Playground

Além do consumidor SQS (`velhodorio.py`), o time pode ser servido como uma **API FastAPI completa** via AgentOS:

```bash
infisical run -- python app.py
```

Isso sobe um servidor em `http://0.0.0.0:7777` com:
- **`/docs`** — Swagger com todos os endpoints gerados automaticamente
- **Streaming SSE** — respostas em tempo real
- **Histórico por sessão** — contexto isolado por `session_id`
- **Tracing** — rastreamento de execuções no banco SQLite

Para usar via `curl` ou qualquer cliente HTTP:
```bash
# Enviar mensagem para o time
curl -X POST http://localhost:7777/v1/teams/velho-rio/runs \
  -H "Content-Type: application/json" \
  -d '{"message": "como estou me sentindo essa semana?", "session_id": "ataliba"}'
```

> Os dois modos são independentes — você pode rodar `velhodorio.py` (SQS) e `app.py` (API) ao mesmo tempo, cada um com seu próprio processo.

### Systemd

O projeto inclui dois unit files prontos. Para instalar ambos:

```bash
# 1. Edite os arquivos substituindo YOUR_USER pelo seu usuário
nano velhodorio.service
nano velhodorio-agentos.service

# 2. Copie para o systemd
sudo cp velhodorio.service /etc/systemd/system/
sudo cp velhodorio-agentos.service /etc/systemd/system/

# 3. Ative e suba
sudo systemctl daemon-reload
sudo systemctl enable velhodorio velhodorio-agentos
sudo systemctl start velhodorio velhodorio-agentos

# Acompanhar logs
journalctl -u velhodorio -f
journalctl -u velhodorio-agentos -f
```

| Serviço | Arquivo | Função |
|---|---|---|
| `velhodorio` | `velhodorio.service` | Consumidor SQS — responde no WhatsApp/Telegram |
| `velhodorio-agentos` | `velhodorio-agentos.service` | API REST na porta 7777 |
---

## 🌐 Arquitetura MCP Distribuída

O Velho do Rio utiliza o protocolo **MCP** para expandir suas capacidades. O sistema está preparado para rodar de forma distribuída — cada servidor MCP pode estar em uma máquina ou container separado.

* **SSE Transport**: A comunicação é feita via HTTP/SSE.
* **Degradação graciosa**: Se um servidor MCP estiver offline no startup, o agente correspondente sobe sem aquele conjunto de ferramentas. O log de inicialização mostra o status de cada conector.

---

## 🔐 Variáveis de Ambiente Esperadas (Infisical)

| Variável | Descrição |
|---|---|
| `OPENROUTER_API_KEY` | Chave para acessar DeepSeek e Claude via OpenRouter |
| `OPENAI_API_KEY` | Utilizada para modelos legados ou auxiliares |
| `MCP_URL` | URL do servidor MCP central (n8n) |
| `MCP_TOKEN` | Token de autenticação dos servidores MCP |
| `MCP_AGENDADOR` | URL do MCP do Agendador (Todoist, Jira, etc.) |
| `RECLAIM_URL` | URL do servidor MCP do Reclaim.ai |
| `RECLAIM_TOKEN` | Chave de API do Reclaim.ai |
| `MCP_FINANCEIRO` | URL do MCP Financeiro (CoinMarketCap, etc.) |
| `MCP_ESCAVADOR` | URL do MCP do Pesquisador (Brave, SerpAPI, etc.) |
| `GOOGLE_API_KEY` | Chave Google para embeddings Gemini (base rag_terapeuta) |
| `QDRANT_URL` | URL da instância Qdrant |
| `QDRANT_API_KEY` | API Key do Qdrant |
| `EVOLUTION_URL` | URL base da instância Evolution API (WhatsApp) |
| `EVOLUTION_INSTANCE` | Nome da instância Evolution |
| `EVOLUTION_API_KEY` | API Key da Evolution |
| `TELEGRAM_BOT_TOKEN` | Token do bot Telegram |
| `WEBHOOK_USER` / `WEBHOOK_PASS` | Credenciais do webhook n8n (ponto eletrônico) |
| `MONGODB_USER` / `MONGODB_PASS` | Credenciais do MongoDB (acervo musical) |
| `POSTGRES_URL` | URL do PostgreSQL ex: `postgresql://host:5432/velhodorio` (opcional — se ausente usa SQLite) |
| `POSTGRES_USER` | Usuário do PostgreSQL |
| `POSTGRES_PASS` | Senha do PostgreSQL |

---

## 📜 Princípios e Persona
> *- "Se o pedido for objetivo, responda de forma DIRETA, organizada e sem cabeçalhos mecânicos."*
> *- "Mantenha o tom de quem enxerga além dos logs, mas fale como um parceiro de caminhada."*

---
*Mantenha-se atento ao fluxo do rio.* 🌊
