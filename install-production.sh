#!/bin/bash
# Production installation script for Memory Bridge

set -e

echo "========================================"
echo "  Memory Bridge - Production Install"
echo "========================================"
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root or with sudo"
    exit 1
fi

# Configuration
INSTALL_DIR="/opt/memory-bridge"
LOG_DIR="/var/log/memory-bridge"
CONFIG_DIR="/etc/memory-bridge"
USER="memory-bridge"

# Check environment
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_KEY" ]; then
    echo "❌ Environment variables not set"
    echo "Please set:"
    echo "  export SUPABASE_URL=https://your-project.supabase.co"
    echo "  export SUPABASE_SERVICE_KEY=your-key"
    echo "  export BRIDGE_API_KEY=your-secure-random-key"
    exit 1
fi

echo "✅ Environment variables set"

# Create user
echo "👤 Creating service user..."
if ! id "$USER" &> /dev/null; then
    useradd -r -s /bin/false -d "$INSTALL_DIR" "$USER"
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p "$INSTALL_DIR" "$LOG_DIR" "$CONFIG_DIR"
chown "$USER:$USER" "$INSTALL_DIR" "$LOG_DIR"

# Install Python dependencies
echo "📦 Installing dependencies..."
apt-get update
apt-get install -y python3 python3-venv python3-pip

# Create virtual environment
echo "🐍 Creating virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"

pip install --upgrade pip
pip install flask flask-cors flask-limiter supabase sentence-transformers gunicorn

# Download application
echo "⬇️  Downloading application..."
curl -fsSL https://raw.githubusercontent.com/n00n0i/memory-bridge/main/memory_bridge_production.py \
    -o "$INSTALL_DIR/memory_bridge_production.py"

# Create environment file
echo "🔐 Creating environment file..."
cat > "$CONFIG_DIR/env" << EOF
SUPABASE_URL=$SUPABASE_URL
SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY
BRIDGE_API_KEY=${BRIDGE_API_KEY:-$(openssl rand -hex 32)}
ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-*}
EOF

chmod 600 "$CONFIG_DIR/env"
chown "$USER:$USER" "$CONFIG_DIR/env"

# Create systemd service
echo "⚙️  Creating systemd service..."
curl -fsSL https://raw.githubusercontent.com/n00n0i/memory-bridge/main/systemd/memory-bridge.service \
    -o /etc/systemd/system/memory-bridge.service

systemctl daemon-reload
systemctl enable memory-bridge

# Create logrotate config
echo "📝 Creating logrotate config..."
cat > /etc/logrotate.d/memory-bridge << 'EOF'
/var/log/memory-bridge/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 memory-bridge memory-bridge
    sharedscripts
    postrotate
        systemctl reload memory-bridge
    endscript
}
EOF

# Start service
echo "🚀 Starting service..."
systemctl start memory-bridge

# Wait for startup
sleep 3

# Check status
if systemctl is-active --quiet memory-bridge; then
    echo ""
    echo "========================================"
    echo "✅ Memory Bridge installed successfully!"
    echo "========================================"
    echo ""
    echo "Service: systemctl status memory-bridge"
    echo "Logs: tail -f /var/log/memory-bridge/memory-bridge.log"
    echo "Config: /etc/memory-bridge/env"
    echo ""
    echo "API Key: $(grep BRIDGE_API_KEY /etc/memory-bridge/env | cut -d= -f2)"
    echo ""
    echo "Test: curl -H 'Authorization: Bearer YOUR_API_KEY' http://localhost:5000/health"
    echo "========================================"
else
    echo "❌ Service failed to start"
    echo "Check logs: journalctl -u memory-bridge -n 50"
    exit 1
fi
