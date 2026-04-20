#!/bin/bash

# 🌿 Velho do Rio - Script de Instalação do AGENTE
# Este script instala apenas o Agente Python.

set -e

PROJECT_NAME="velhodorio-ng"
PROJECT_DIR="$HOME/$PROJECT_NAME"

echo "🌊 Iniciando o fluxo do Rio... (Setup do Agente)"

# 1. Detecção do SO e Instalação de Dependências Python
if [ -f /etc/alpine-release ]; then
    echo "🏔️ Detectado Alpine Linux"
    sudo apk update
    sudo apk add python3 py3-pip git curl bash
    PYTHON_BIN="python3"
elif [ -f /etc/debian_version ] || [ -f /etc/lsb-release ]; then
    echo "🐧 Detectado Debian/Ubuntu"
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv git curl
    PYTHON_BIN="python3"
else
    sudo dnf install -y python3 git curl
    PYTHON_BIN="python3"
fi

# 2. Instalação do Infisical CLI
if ! command -v infisical &> /dev/null; then
    echo "🔐 Instalando Infisical CLI..."
    if command -v apt-get &> /dev/null; then
        curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.deb.sh' | sudo -E bash
        sudo apt-get install -y infisical
    elif command -v dnf &> /dev/null; then
        curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.rpm.sh' | sudo -E bash
        sudo dnf install -y infisical
    fi
fi

# 3. Preparação das Pastas
if [ ! -d "$PROJECT_DIR" ]; then
    git clone https://github.com/ataliba/velhodorio-ng.git "$PROJECT_DIR"
fi
cd "$PROJECT_DIR"

# 4. Setup do Ambiente Python
echo "🐍 Configurando ambiente Python..."
$PYTHON_BIN -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Instalação e Configuração do PM2
echo "🚀 Instalando PM2 para gerenciamento de processos..."
# Garante que o npm existe (instala no Debian se necessário)
if ! command -v npm &> /dev/null; then
    if command -v apt-get &> /dev/null; then sudo apt-get install -y nodejs npm; fi
fi
sudo npm install -g pm2

echo "⚙️ Configurando o Velho do Rio no PM2..."
pm2 delete velhodorio 2>/dev/null || true
# Rodamos através do Infisical e apontamos para o interpretador do venv
pm2 start "infisical run -- $PROJECT_DIR/venv/bin/python $PROJECT_DIR/velhodorio.py" --name velhodorio

# Salvar para persistir no boot
pm2 save

echo ""
echo "✨ Agente Velho do Rio rodando via PM2!"
echo "👉 Veja a sabedoria: pm2 logs velhodorio"
echo "👉 Painel de controle: pm2 monit"
echo "👉 Status: pm2 list"

echo "✨ Agente instalado! Lembre-se de configurar RECLAIM_MCP_URL no Infisical."
