# 🌿🕶️ Velho do Rio (Next Generation)

> *"A margem entre o código e o inconsciente."*

**Velho do Rio** é um agente de inteligência artificial autônomo, desenhado sob uma persona de um **"cyber-xamã"**. Ele atua como um mentor lúcido e direto, criado exclusivamente para auxiliar seu mantenedor nas atividades cotidianas e orquestrar de forma fluida os sistemas de automação de plano de fundo.

Construído em **Python**, usando o framework **[Agno v2](https://github.com/agno-ai/agno)**, o agente processa mensagens de forma assíncrona, consumindo chamadas diretamente de uma fila AWS SQS e interagindo com o mundo exterior (n8n, MongoDB, APIs) através de ferramentas e do protocolo **MCP** (Model Context Protocol).

---

## ✨ Características e Arquitetura

* **Conexão MCP (Model Context Protocol):** Comunicação direta e assíncrona via *Server-Sent Events* (SSE) com fluxos avançados do **n8n**. O agente descobre e utiliza ferramentas dinamicamente (como consultar preços de criptomoedas no CoinMarketCap).
* **Consumo de Filas (AWS SQS):** Trabalha de forma reativa e não-bloqueante consumindo payloads vindos do WhatsApp (API Evolution).
* **Segurança e Cofre de Segredos:** Configuração centralizada e segura utilizando o **Infisical**. Zero chaves ou credenciais em hardcode (API OpenAI, Tokens MCP, senhas do Webhook e credenciais do MongoDB).
* **Persistência de Sessões:** Todo o histórico conversacional é armazenado localmente em um banco de dados **SQLite** isolando os contextos por usuário (`chatId`).
* **Ferramentas Locais Customizadas:**
    * 🎵 `consultar_acervo_musical`: Consulta nativa no MongoDB da coleção de discos.
    * ⏱️ `registrar_ponto_trabalho`: Gatilho de automação n8n para ponto eletrônico com envio preciso de `date_time` (timestamp extraído dos metadados).

---

## 🚀 Como Executar

### Pré-requisitos
* Python 3.10+
* CLI do [Infisical](https://infisical.com/) devidamente instalada e autenticada.
* Arquivo `.infisical.json` linkado ao projeto para injeção correta das variáveis.

### 1. Preparar o Ambiente
Crie e ative seu ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate
```

### 2. Instalar as Dependências
Todas as bibliotecas necessárias constam no `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 3. Rodar o Agente via Infisical
Para garantir que as variáveis de ambiente sensíveis (como `OPENAI_API_KEY`, senhas e `MCP_TOKEN`) sejam injetadas no processo sem precisar de um arquivo local vulnerável, execute:
```bash
infisical run -- python velhodorio.py
```
*(Opcional: use nohup, pm2 ou systemd para mantê-lo rodando em background em seu servidor).*

---

## 🔐 Variáveis de Ambiente Esperadas (Infisical)
O Agente necessita que as seguintes chaves estejam no cofre para funcionar:
* `OPENAI_API_KEY`: Para processamento com GPT-4o-mini
* `MONGODB_USER` / `MONGODB_PASS`: Acesso ao banco de discos.
* `WEBHOOK_USER` / `WEBHOOK_PASS`: Autenticação HTTP Basic no nodo do n8n.
* `MCP_URL` / `MCP_TOKEN`: Endereço SSE e Token Bearer de autorização do seu servidor MCP do n8n.

---

## 📜 Princípios e Persona
> *- "Se o pedido for objetivo, responda de forma DIRETA, organizada e sem cabeçalhos mecânicos."*
> *- "Mantenha o tom de quem enxerga além dos logs, mas fale como um parceiro de caminhada."*
> *- "O acervo são memórias guardadas e o sistema é como o fluxo do rio."*

---
*Mantenha-se atento ao fluxo do rio.* 🌊
