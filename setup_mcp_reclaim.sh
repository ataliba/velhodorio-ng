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

# 4. Criação do serviço Systemd
if command -v systemctl &> /dev/null; then
    echo "⚙️ Criando serviço reclaim-mcp.service..."
    SERVICE_FILE="/etc/systemd/system/reclaim-mcp.service"
    NODE_PATH=$(which node || echo "/usr/bin/node")
    
    sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=Reclaim MCP Server (HTTP)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
# Roda o servidor em modo HTTP e expõe para a rede
ExecStart=/usr/bin/infisical run -- $NODE_PATH dist/index.js
Environment=MCP_TRANSPORT=http
Environment=MCP_HTTP_HOST=0.0.0.0
Environment=MCP_HTTP_PORT=3000
Environment=MCP_HTTP_ALLOW_ANY_ORIGIN=true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF"
    sudo systemctl daemon-reload
    echo "✅ Serviço criado! Inicie com: sudo systemctl start reclaim-mcp"
fi

echo "✨ Servidor MCP instalado com sucesso na porta 3000!"
