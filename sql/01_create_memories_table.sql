-- Memory Bridge Database Schema Migration
-- Run this in Supabase SQL Editor before starting Memory Bridge

-- Enable pgvector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create memories table with all required columns
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT,
    title TEXT,
    tags TEXT[],
    importance INTEGER DEFAULT 3,
    content TEXT NOT NULL,
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    source TEXT DEFAULT 'unknown',
    embedding VECTOR(384)
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_memories_embedding 
ON memories USING ivfflat (embedding vector_cosine_ops);

-- Create index for metadata queries
CREATE INDEX IF NOT EXISTS idx_memories_metadata 
ON memories USING GIN (metadata);

-- Create index for source filtering
CREATE INDEX IF NOT EXISTS idx_memories_source 
ON memories (source);

-- Create index for timestamp ordering
CREATE INDEX IF NOT EXISTS idx_memories_created_at 
ON memories (created_at DESC);

-- Create vector similarity search function
CREATE OR REPLACE FUNCTION match_memories(
    query_embedding VECTOR(384),
    match_threshold FLOAT,
    match_count INT
)
RETURNS TABLE(
    id UUID,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        memories.id,
        memories.content,
        memories.metadata,
        1 - (memories.embedding <=> query_embedding) AS similarity
    FROM memories
    WHERE 1 - (memories.embedding <=> query_embedding) > match_threshold
    ORDER BY memories.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for auto-updating updated_at
DROP TRIGGER IF EXISTS update_memories_updated_at ON memories;
CREATE TRIGGER update_memories_updated_at
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Verify table structure
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'memories'
ORDER BY ordinal_position;
