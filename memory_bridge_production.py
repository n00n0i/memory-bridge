#!/usr/bin/env python3
"""
Production Memory Bridge Service
- Systemd integration
- Security hardening
- Logging
- Health checks
"""

import os
import sys
import json
import logging
import hashlib
import hmac
from datetime import datetime
from functools import wraps
from typing import List, Dict, Any, Optional

# Security: Validate environment
REQUIRED_ENV = ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY']
for env_var in REQUIRED_ENV:
    if not os.getenv(env_var):
        print(f"❌ Error: {env_var} not set")
        sys.exit(1)

# Security: API key for bridge authentication
BRIDGE_API_KEY = os.getenv('BRIDGE_API_KEY')
if not BRIDGE_API_KEY:
    # Generate random key if not set
    import secrets
    BRIDGE_API_KEY = secrets.token_urlsafe(32)
    print(f"⚠️  Generated BRIDGE_API_KEY: {BRIDGE_API_KEY}")
    print("   Set this in environment for consistency")

# Setup logging
log_dir = '/var/log/memory-bridge'
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{log_dir}/memory-bridge.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import dependencies
try:
    from flask import Flask, request, jsonify, abort
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    from flask_cors import CORS
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError as e:
    logger.error(f"Missing dependency: {e}")
    print("Run: pip install flask flask-cors flask-limiter supabase sentence-transformers")
    sys.exit(1)

# Local embedding
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    LOCAL_EMBEDDING = True
    logger.info("Local embedding enabled")
except Exception as e:
    logger.warning(f"Local embedding failed: {e}")
    EMBEDDING_MODEL = None
    LOCAL_EMBEDDING = False

class SecureMemoryBridge:
    """Production memory bridge with security"""
    
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_SERVICE_KEY')
        self.client: Client = create_client(self.url, self.key)
        self.request_count = 0
        logger.info("Memory Bridge initialized")
    
    def _verify_auth(self, request) -> bool:
        """Verify API key"""
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return False
        token = auth_header[7:]
        return hmac.compare_digest(token, BRIDGE_API_KEY)
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding locally"""
        if LOCAL_EMBEDDING and EMBEDDING_MODEL:
            return EMBEDDING_MODEL.encode(text).tolist()
        return []
    
    def store(self, content: str, metadata: Dict = None) -> Dict:
        """Store memory securely"""
        try:
            # Validate input
            if not content or len(content) > 10000:
                return {"status": "error", "message": "Invalid content"}
            
            # Sanitize metadata
            safe_metadata = {}
            if metadata:
                for k, v in metadata.items():
                    if isinstance(k, str) and isinstance(v, (str, int, float, bool)):
                        safe_metadata[k] = str(v)[:100]
            
            # Generate embedding
            embedding = self._generate_embedding(content)
            
            data = {
                "content": content[:5000],  # Limit size
                "metadata": safe_metadata,
                "source": "memory-bridge",
                "created_at": datetime.utcnow().isoformat()
            }
            
            if embedding:
                data["embedding"] = embedding
            
            result = self.client.table("memories").insert(data).execute()
            
            logger.info(f"Stored memory: {result.data[0]['id'] if result.data else 'unknown'}")
            
            return {
                "status": "success",
                "id": result.data[0]["id"] if result.data else None
            }
            
        except Exception as e:
            logger.error(f"Store error: {e}")
            return {"status": "error", "message": str(e)}
    
    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Search memories"""
        try:
            if not query or len(query) > 1000:
                return []
            
            limit = min(max(limit, 1), 20)  # Clamp 1-20
            
            if LOCAL_EMBEDDING and EMBEDDING_MODEL:
                # Vector search
                query_embedding = self._generate_embedding(query)
                result = self.client.rpc(
                    "match_memories",
                    {
                        "query_embedding": query_embedding,
                        "match_threshold": 0.7,
                        "match_count": limit
                    }
                ).execute()
            else:
                # Fallback: text search
                result = self.client.table("memories")\
                    .select("*")\
                    .ilike("content", f"%{query}%")\
                    .limit(limit)\
                    .execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def health(self) -> Dict:
        """Health check"""
        try:
            result = self.client.table("memories").select("count", count="exact").execute()
            return {
                "status": "healthy",
                "supabase_connected": True,
                "local_embedding": LOCAL_EMBEDDING,
                "memory_count": result.count if hasattr(result, 'count') else 0,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

def create_app():
    """Create Flask app with security"""
    app = Flask(__name__)
    
    # Security: Rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["100 per minute", "1000 per hour"]
    )
    
    # Security: CORS (restrict in production)
    allowed_origins = os.getenv('ALLOWED_ORIGINS', '*').split(',')
    CORS(app, origins=allowed_origins)
    
    # Security: Request size limit
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024  # 1MB
    
    bridge = SecureMemoryBridge()
    
    @app.before_request
    def check_auth():
        """Verify API key for all routes except health"""
        if request.endpoint == 'health':
            return
        if not bridge._verify_auth(request):
            logger.warning(f"Unauthorized request from {request.remote_addr}")
            abort(401)
    
    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    @app.errorhandler(429)
    def rate_limit(e):
        return jsonify({"status": "error", "message": "Rate limit exceeded"}), 429
    
    @app.route('/health', methods=['GET'])
    @limiter.exempt
    def health():
        return jsonify(bridge.health())
    
    @app.route('/remember', methods=['POST'])
    @limiter.limit("30 per minute")
    def remember():
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({"status": "error", "message": "Missing content"}), 400
        
        result = bridge.store(
            content=data['content'],
            metadata=data.get('metadata', {})
        )
        return jsonify(result)
    
    @app.route('/recall', methods=['POST'])
    @limiter.limit("60 per minute")
    def recall():
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"status": "error", "message": "Missing query"}), 400
        
        results = bridge.search(
            query=data['query'],
            limit=data.get('limit', 5)
        )
        return jsonify({"results": results})
    
    @app.route('/recent', methods=['GET'])
    @limiter.limit("30 per minute")
    def recent():
        limit = request.args.get('limit', 10, type=int)
        limit = min(max(limit, 1), 50)
        
        try:
            result = bridge.client.table("memories")\
                .select("*")\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return jsonify({"results": result.data or []})
        except Exception as e:
            logger.error(f"Recent error: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    return app

def main():
    """Production entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Memory Bridge Service')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind')
    parser.add_argument('--workers', type=int, default=1, help='Number of workers')
    args = parser.parse_args()
    
    logger.info(f"Starting Memory Bridge on {args.host}:{args.port}")
    logger.info(f"Security: API key required, rate limiting enabled")
    
    app = create_app()
    
    # Production: use gunicorn if available
    if args.workers > 1:
        try:
            from gunicorn.app.base import BaseApplication
            
            class GunicornApp(BaseApplication):
                def __init__(self, app, options=None):
                    self.options = options or {}
                    self.application = app
                    super().__init__()
                
                def load_config(self):
                    for key, value in self.options.items():
                        if key in self.cfg.settings:
                            self.cfg.set(key.lower(), value)
                
                def load(self):
                    return self.application
            
            options = {
                'bind': f'{args.host}:{args.port}',
                'workers': args.workers,
                'accesslog': '/var/log/memory-bridge/access.log',
                'errorlog': '/var/log/memory-bridge/error.log'
            }
            GunicornApp(app, options).run()
        except ImportError:
            logger.warning("Gunicorn not available, using Flask dev server")
            app.run(host=args.host, port=args.port, threaded=True)
    else:
        app.run(host=args.host, port=args.port, threaded=True)

if __name__ == '__main__':
    main()
