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

# 5. Criação do serviço de inicialização (Systemd ou OpenRC)
if command -v systemctl &> /dev/null; then
    echo "⚙️ Configurando serviço Systemd (Debian/Ubuntu/Alma)..."
    SERVICE_FILE="/etc/systemd/system/velhodorio.service"
    sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=Agente Velho do Rio - Cyber Xamã
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/infisical run -- $PROJECT_DIR/venv/bin/python $PROJECT_DIR/velhodorio.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF"
    sudo systemctl daemon-reload
    echo "✅ Serviço systemd criado."
elif command -v rc-service &> /dev/null; then
    echo "🏔️ Configurando serviço OpenRC (Alpine)..."
    INIT_FILE="/etc/init.d/velhodorio"
    sudo bash -c "cat <<EOF > $INIT_FILE
#!/sbin/openrc-run

name=\"velhodorio\"
description=\"Agente Velho do Rio - Cyber Xamã\"
command=\"/usr/bin/infisical\"
command_args=\"run -- $PROJECT_DIR/venv/bin/python $PROJECT_DIR/velhodorio.py\"
command_user=\"$USER\"
directory=\"$PROJECT_DIR\"
pidfile=\"/run/velhodorio.pid\"
command_background=\"yes\"

depend() {
    need net
}
EOF"
    sudo chmod +x "$INIT_FILE"
    sudo rc-update add velhodorio default
    echo "✅ Serviço OpenRC criado e habilitado no boot."
fi

echo "✨ Agente instalado! Lembre-se de configurar RECLAIM_MCP_URL no Infisical."
