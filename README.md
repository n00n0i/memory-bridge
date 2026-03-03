# Memory Bridge for OpenClaw

HTTP bridge service that connects OpenClaw to Supabase with local embeddings.

## Quick Start

### 1. Set Environment Variables

```bash
export SUPABASE_URL="https://zbecvutqewjtglposbkf.supabase.co"
export SUPABASE_SERVICE_KEY="your-service-key-here"
```

### 2. Run

```bash
chmod +x start.sh
./start.sh
```

Or manually:

```bash
pip install flask flask-cors supabase sentence-transformers
python3 memory_bridge.py
```

### 3. Test

```bash
curl http://localhost:5000/health
```

## API Endpoints

| Endpoint | Method | Description |
|:---|:---:|:---|
| `/health` | GET | Check service status |
| `/remember` | POST | Store a memory |
| `/recall` | POST | Search memories |
| `/recent` | GET | List recent memories |

### Store Memory

```bash
curl -X POST http://localhost:5000/remember \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User prefers Python",
    "metadata": {"topic": "programming"}
  }'
```

### Search Memory

```bash
curl -X POST http://localhost:5000/recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What language?",
    "limit": 5
  }'
```

## Expose to Internet (for OpenClaw)

### Option 1: ngrok

```bash
ngrok http 5000
# Use https URL provided
```

### Option 2: localtunnel

```bash
npx localtunnel --port 5000
# Use URL provided
```

### Option 3: Cloudflare Tunnel

```bash
cloudflared tunnel --url http://localhost:5000
```

## OpenClaw Usage

Once exposed, tell OpenClaw your URL:

```
My memory bridge is at: https://your-url.ngrok.io
```

Then OpenClaw can call:
- `POST https://your-url.ngrok.io/remember`
- `POST https://your-url.ngrok.io/recall`
