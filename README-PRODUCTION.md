# Memory Bridge - Production Deployment

## Security Features

- ✅ API Key Authentication (Bearer token)
- ✅ Rate Limiting (100/min, 1000/hour)
- ✅ Input Validation & Sanitization
- ✅ Request Size Limits (1MB)
- ✅ CORS Protection
- ✅ Systemd Sandboxing
- ✅ Audit Logging
- ✅ No New Privileges

## Quick Install

```bash
# Set environment variables
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="your-service-key"
export BRIDGE_API_KEY="your-secure-random-key"  # Optional, will generate

# Run installer
curl -fsSL https://raw.githubusercontent.com/n00n0i/memory-bridge/main/install-production.sh | sudo bash
```

## Manual Install

```bash
# 1. Install dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip

# 2. Create directories
sudo mkdir -p /opt/memory-bridge /var/log/memory-bridge /etc/memory-bridge

# 3. Create virtual environment
sudo python3 -m venv /opt/memory-bridge/venv
source /opt/memory-bridge/venv/bin/activate
pip install flask flask-cors flask-limiter supabase sentence-transformers gunicorn

# 4. Download app
sudo curl -fsSL https://raw.githubusercontent.com/n00n0i/memory-bridge/main/memory_bridge_production.py \
    -o /opt/memory-bridge/memory_bridge_production.py

# 5. Create environment file
sudo tee /etc/memory-bridge/env << EOF
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
BRIDGE_API_KEY=your-secure-api-key
EOF
sudo chmod 600 /etc/memory-bridge/env

# 6. Create systemd service
sudo curl -fsSL https://raw.githubusercontent.com/n00n0i/memory-bridge/main/systemd/memory-bridge.service \
    -o /etc/systemd/system/memory-bridge.service

# 7. Start service
sudo systemctl daemon-reload
sudo systemctl enable memory-bridge
sudo systemctl start memory-bridge
```

## API Usage

### Authentication

All endpoints (except /health) require Bearer token:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" ...
```

### Endpoints

| Endpoint | Auth | Rate Limit | Description |
|:---|:---:|:---:|:---|
| `GET /health` | No | Exempt | Health check |
| `POST /remember` | Yes | 30/min | Store memory |
| `POST /recall` | Yes | 60/min | Search memories |
| `GET /recent` | Yes | 30/min | List recent |

### Examples

```bash
# Health check
curl http://localhost:5000/health

# Store memory (with auth)
curl -X POST http://localhost:5000/remember \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content": "User likes Python", "metadata": {"topic": "programming"}}'

# Search memories
curl -X POST http://localhost:5000/recall \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "programming language", "limit": 5}'
```

## Management

```bash
# Check status
sudo systemctl status memory-bridge

# View logs
sudo tail -f /var/log/memory-bridge/memory-bridge.log

# Restart
sudo systemctl restart memory-bridge

# Stop
sudo systemctl stop memory-bridge

# Update
sudo systemctl stop memory-bridge
sudo curl -fsSL https://raw.githubusercontent.com/n00n0i/memory-bridge/main/memory_bridge_production.py \
    -o /opt/memory-bridge/memory_bridge_production.py
sudo systemctl start memory-bridge
```

## Expose to Internet

Use reverse proxy (nginx) or tunnel:

```bash
# ngrok (development)
ngrok http 5000

# Cloudflare Tunnel (production)
cloudflared tunnel --url http://localhost:5000
```

Then tell OpenClaw your public URL.
