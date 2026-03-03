-- Memory Bridge Database Migration Guide

## Prerequisites

1. Supabase project with pgvector extension enabled
2. Service role key with full database access

## Migration Steps

### Step 1: Open Supabase SQL Editor

Go to: `https://app.supabase.com/project/{your-project-ref}/sql`

### Step 2: Run Migration Script

Copy and paste the contents of `sql/01_create_memories_table.sql` into the SQL Editor.

Click **"Run"**.

### Step 3: Verify

Run this query to verify:
```sql
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'memories';
```

Expected columns:
- `id` (UUID, PK)
- `type` (TEXT, nullable)
- `title` (TEXT, nullable)
- `tags` (TEXT[], nullable)
- `importance` (INTEGER, default 3)
- `content` (TEXT, required)
- `summary` (TEXT, nullable)
- `created_at` (TIMESTAMPTZ, default now)
- `updated_at` (TIMESTAMPTZ, default now)
- `metadata` (JSONB, default '{}')
- `source` (TEXT, default 'unknown')
- `embedding` (VECTOR(384), nullable)

### Step 4: Start Memory Bridge

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="your-service-role-key"
export BRIDGE_API_KEY="your-random-api-key"

python memory_bridge_production.py --port 5000
```

## Troubleshooting

### Error: "Could not find the 'embedding' column"

**Cause:** pgvector extension not enabled or column missing.

**Fix:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS embedding VECTOR(384);
```

### Error: "null value in column 'type' violates not-null constraint"

**Cause:** Existing table with NOT NULL constraints.

**Fix:**
```sql
ALTER TABLE memories 
ALTER COLUMN type DROP NOT NULL,
ALTER COLUMN title DROP NOT NULL;
```

### Error: "function match_memories does not exist"

**Cause:** Function not created.

**Fix:** Run the `CREATE OR REPLACE FUNCTION match_memories...` section from the migration script.

## Schema Versions

| Version | File | Description |
|:---|:---|:---|
| v1.0 | `01_create_memories_table.sql` | Initial schema with vector support |
