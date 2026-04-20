#!/bin/bash

# 📅 Reclaim MCP - Script de Instalação Independente
# Este script instala apenas o servidor MCP do Reclaim.

set -e

INSTALL_DIR="$HOME/reclaim-mcp-server"
MCP_REPO="https://github.com/erikmackinnon/reclaim-mcp-server.git"

echo "📅 Iniciando setup do servidor Reclaim MCP..."

# 1. Instalação de Dependências Node.js
if [ -f /etc/alpine-release ]; then
    sudo apk update
    sudo apk add nodejs npm git curl bash
elif [ -f /etc/debian_version ] || [ -f /etc/lsb-release ]; then
    sudo apt-get update
    sudo apt-get install -y nodejs npm git curl
else
    sudo dnf install -y nodejs npm git curl
fi

# 2. Instalação do Infisical CLI
if ! command -v infisical &> /dev/null; then
    if command -v apt-get &> /dev/null; then
        curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.deb.sh' | sudo -E bash
        sudo apt-get install -y infisical
    elif command -v dnf &> /dev/null; then
        curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.rpm.sh' | sudo -E bash
        sudo dnf install -y infisical
    fi
fi

# 3. Download e Build do MCP
if [ ! -d "$INSTALL_DIR" ]; then
    git clone "$MCP_REPO" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"
npm install
npm run build

# 4. Instalação do PM2 (Opcional, mas recomendado)
echo "🚀 Instalando PM2 para gerenciamento de processos..."
sudo npm install -g pm2

# 5. Inicialização via PM2 (Universal para Alpine/Debian)
echo "⚙️ Configurando serviço no PM2..."
pm2 delete reclaim-mcp 2>/dev/null || true
# Rodamos através do Infisical para injetar as chaves
pm2 start "infisical run -- node dist/index.js" --name reclaim-mcp --env MCP_TRANSPORT=http --env MCP_HTTP_HOST=0.0.0.0 --env MCP_HTTP_PORT=3000 --env MCP_HTTP_ALLOW_ANY_ORIGIN=true

# Salvar para persistir no boot
pm2 save

echo ""
echo "✨ Servidor MCP instalado e rodando via PM2 na porta 3000!"
echo "👉 Veja os logs: pm2 logs reclaim-mcp"
echo "👉 Status: pm2 list"
