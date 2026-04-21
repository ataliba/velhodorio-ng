# 🌿🕶️ Velho do Rio (Next Generation)

> *"A margem entre o código e o inconsciente."*

**Velho do Rio** é um agente de inteligência artificial autônomo, desenhado sob uma persona de um **"cyber-xamã"**. Ele atua como um mentor lúcido e direto, criado exclusivamente para auxiliar seu mantenedor nas atividades cotidianas e orquestrar de forma fluida os sistemas de automação de plano de fundo.

Construído em **Python**, usando o framework **[Agno v2](https://github.com/agno-ai/agno)**, o agente processa mensagens de forma assíncrona, consumindo chamadas diretamente de uma fila AWS SQS e interagindo com o mundo exterior (n8n, MongoDB, APIs) através de ferramentas e do protocolo **MCP** (Model Context Protocol).

---

## ✨ Características e Arquitetura

* **Arquitetura Multi-Agente (Agno Team):** O Velho do Rio agora lidera um time de especialistas, delegando tarefas de acordo com a necessidade.
* **Modelos Especializados (OpenRouter):** Utiliza DeepSeek V3 para orquestração, DeepSeek R1 para raciocínio financeiro e Claude 3.5 Haiku para pesquisas rápidas.
* **Conexão MCP (Model Context Protocol):** Comunicação direta e assíncrona via *Server-Sent Events* (SSE) com fluxos avançados do **n8n**.
* **Consumo de Filas (AWS SQS):** Trabalha de forma reativa e não-bloqueante consumindo payloads vindos do WhatsApp (API Evolution) e Telegram.
* **Segurança e Cofre de Segredos:** Configuração centralizada e segura utilizando o **Infisical**. Zero chaves ou credenciais em hardcode (API OpenAI, Tokens MCP, senhas do Webhook e credenciais do MongoDB).
* **Persistência de Sessões:** Todo o histórico conversacional é armazenado localmente em um banco de dados **SQLite** isolando os contextos por usuário (`chatId`).
* **Ferramentas Locais Customizadas:**
    * 🎵 `consultar_acervo_musical`: Consulta nativa no MongoDB da coleção de discos.
    * ⏱️ `registrar_ponto_trabalho`: Gatilho de automação n8n para ponto eletrônico com envio preciso de `date_time` (timestamp extraído dos metadados).
21: 
22: ### 🛠️ Utilitários de Desenvolvimento
23: *   🧹 `limpa_fila.py`: Script para "drenar" a fila SQS. Útil quando você insere dados de teste inválidos e quer limpar a fila sem que o agente os processe.
24:     ```bash
25:     # Execução rápida:
26:     python limpa_fila.py
27:     ```

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

## 🌐 Arquitetura MCP Distribuída
O Velho do Rio utiliza o protocolo **MCP** para expandir suas capacidades. Agora, o sistema está preparado para rodar de forma distribuída:

1.  **Variável `RECLAIM_MCP_URL`**: Defina no Infisical a URL do seu servidor de ferramentas (ex: `http://10.0.0.50:3000/mcp`). 
2.  **SSE Transport**: A comunicação é feita via HTTP/SSE, permitindo que o servidor MCP rode em um container separado do Agente.

---

## 🔐 Variáveis de Ambiente Esperadas (Infisical)
* `OPENAI_API_KEY`: Utilizada para modelos legados ou auxiliares.
* `OPENROUTER_API_KEY`: Chave para acessar DeepSeek e Claude via OpenRouter.
* `RECLAIM_TOKEN`: Chave de API do Reclaim.ai (usada pelo servidor MCP).
* `RECLAIM_MCP_URL`: (Opcional) URL do servidor MCP do Reclaim.
* `MCP_URL` / `MCP_TOKEN`: Configurações do n8n MCP.

---

## 📜 Princípios e Persona
> *- "Se o pedido for objetivo, responda de forma DIRETA, organizada e sem cabeçalhos mecânicos."*
> *- "Mantenha o tom de quem enxerga além dos logs, mas fale como um parceiro de caminhada."*

---
*Mantenha-se atento ao fluxo do rio.* 🌊
