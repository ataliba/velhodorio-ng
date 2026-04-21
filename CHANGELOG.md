# 📜 Changelog - Velho do Rio

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

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
