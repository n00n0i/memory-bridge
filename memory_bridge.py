#!/usr/bin/env python3
"""
Memory Bridge Service
Connects OpenClaw to Supabase with local embeddings
Run this on your machine with SUPABASE_SERVICE_KEY set
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any

# Try to import local embedding
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from embedding_service import generate_embedding, generate_embeddings
    LOCAL_EMBEDDING_AVAILABLE = True
except ImportError:
    LOCAL_EMBEDDING_AVAILABLE = False
    print("⚠️  Local embedding not available, using Supabase RPC fallback")

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("❌ Supabase not installed: pip install supabase")
    sys.exit(1)

class MemoryBridge:
    """Bridge between OpenClaw and Supabase"""
    
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.url or not self.key:
            print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY required")
            print("Set them as environment variables:")
            print("  export SUPABASE_URL=https://your-project.supabase.co")
            print("  export SUPABASE_SERVICE_KEY=your-key")
            sys.exit(1)
        
        self.client: Client = create_client(self.url, self.key)
        print(f"✅ Connected to Supabase: {self.url[:40]}...")
        
        if LOCAL_EMBEDDING_AVAILABLE:
            print("✅ Local embedding enabled (no API key needed)")
    
    def store(self, content: str, metadata: Dict = None) -> Dict:
        """Store memory with local embedding"""
        try:
            # Generate embedding locally
            if LOCAL_EMBEDDING_AVAILABLE:
                embedding = generate_embedding(content)
            else:
                # Fallback: store without embedding, use full-text search
                embedding = None
            
            data = {
                "content": content,
                "metadata": metadata or {},
                "source": "openclaw-bridge",
                "created_at": datetime.now().isoformat()
            }
            
            if embedding:
                data["embedding"] = embedding
            
            result = self.client.table("memories").insert(data).execute()
            
            return {
                "status": "success",
                "id": result.data[0]["id"] if result.data else None,
                "content": content
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Search memories using local embedding"""
        try:
            if LOCAL_EMBEDDING_AVAILABLE:
                # Use vector search with local embedding
                query_embedding = generate_embedding(query)
                
                result = self.client.rpc(
                    "match_memories",
                    {
                        "query_embedding": query_embedding,
                        "match_threshold": 0.7,
                        "match_count": limit
                    }
                ).execute()
                
                return result.data or []
            else:
                # Fallback: simple text search
                result = self.client.table("memories")\
                    .select("*")\
                    .ilike("content", f"%{query}%")\
                    .limit(limit)\
                    .execute()
                
                return result.data or []
                
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def list_recent(self, limit: int = 10) -> List[Dict]:
        """List recent memories"""
        try:
            result = self.client.table("memories")\
                .select("*")\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data or []
        except Exception as e:
            print(f"List error: {e}")
            return []
    
    def health(self) -> Dict:
        """Health check"""
        try:
            # Test connection
            result = self.client.table("memories").select("count", count="exact").execute()
            count = result.count if hasattr(result, 'count') else 0
            
            return {
                "status": "healthy",
                "supabase_connected": True,
                "local_embedding": LOCAL_EMBEDDING_AVAILABLE,
                "memory_count": count
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

# Flask app for HTTP API
def create_app():
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    
    app = Flask(__name__)
    CORS(app)  # Allow cross-origin requests
    
    bridge = MemoryBridge()
    
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify(bridge.health())
    
    @app.route('/remember', methods=['POST'])
    def remember():
        data = request.json
        result = bridge.store(
            content=data.get('content', ''),
            metadata=data.get('metadata', {})
        )
        return jsonify(result)
    
    @app.route('/recall', methods=['POST'])
    def recall():
        data = request.json
        results = bridge.search(
            query=data.get('query', ''),
            limit=data.get('limit', 5)
        )
        return jsonify({"results": results})
    
    @app.route('/recent', methods=['GET'])
    def recent():
        limit = request.args.get('limit', 10, type=int)
        results = bridge.list_recent(limit)
        return jsonify({"results": results})
    
    return app

def main():
    """Run the bridge service"""
    print("=" * 50)
    print("  OpenClaw Memory Bridge")
    print("=" * 50)
    print()
    
    # Check dependencies
    try:
        from flask import Flask
        from flask_cors import CORS
    except ImportError:
        print("❌ Flask not installed")
        print("Run: pip install flask flask-cors")
        sys.exit(1)
    
    # Create and run app
    app = create_app()
    
    port = int(os.getenv("PORT", "5000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 Starting server on {host}:{port}")
    print(f"📡 Health check: http://{host}:{port}/health")
    print(f"💾 Remember: POST http://{host}:{port}/remember")
    print(f"🔍 Recall: POST http://{host}:{port}/recall")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    app.run(host=host, port=port, debug=False)

if __name__ == "__main__":
    main()
