# 01 · PostgreSQL + Qdrant + BGE-M3 Migration (P1)

**Goal**: Replace MongoDB + in-memory cosine + 256-dim hash pseudo-embedding with production stack: PostgreSQL (with Row-Level Security) + Qdrant (vector DB) + BAAI/bge-m3 (1024-dim multilingual embeddings).

## Why
- True data sovereignty (RLS enforces tenant isolation at DB layer)
- BGE-M3 produces semantic embeddings that actually understand Finnish/English (current hash version only matches exact n-grams)
- Qdrant scales to millions of fragments; current in-memory cosine is O(N²) on each `_update_clusters()`

## Estimated effort
4-6 hours of focused work. **Cannot be tested in this Kubernetes pod** (no Postgres/Qdrant available). Implement and test in production.

## Steps

### 1. Add services to `docker-compose.yml` (in user's prod repo)
```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: talktoplus
      POSTGRES_PASSWORD: ${PG_PASSWORD}
      POSTGRES_DB: talktoplus
    volumes: ["pgdata:/var/lib/postgresql/data"]
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: ["qdrantdata:/qdrant/storage"]
volumes:
  pgdata: {}
  qdrantdata: {}
```

### 2. Update `backend/.env`
```
POSTGRES_URL=postgresql+asyncpg://talktoplus:${PG_PASSWORD}@postgres:5432/talktoplus
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=
EMBEDDING_MODEL=BAAI/bge-m3
```

### 3. Add deps to `backend/requirements.txt`
```
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
alembic==1.14.0
qdrant-client==1.12.0
sentence-transformers==3.3.1
```

### 4. Models (`backend/db/models.py`) — SQLAlchemy
Map every Pydantic model in `server.py` to SQLAlchemy:
- `User`, `Tenant`, `Signal`, `ActionCard`, `StrategyDoc`, `AuditLog` → tables
- `SwarmFragment`, `UniversalBottleneck` → SEPARATE database `talktoplus_mothership` (or schema)
- Add `tenant_id` to every Sovereign Edge table + RLS policy:
```sql
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON signals
  USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

### 5. Replace `semantic_embed()` in `server.py`
```python
from sentence_transformers import SentenceTransformer
_model = SentenceTransformer("BAAI/bge-m3")
def semantic_embed(text: str) -> List[float]:
    return _model.encode(text, normalize_embeddings=True).tolist()
```
Update `VECTOR_DIM = 1024`.

### 6. Replace cosine clustering with Qdrant
```python
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
qdrant = AsyncQdrantClient(url=os.environ["QDRANT_URL"])

# in startup:
await qdrant.recreate_collection(
    "swarm_fragments",
    vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
)

# replace _update_clusters() — use Qdrant's clustering or scroll+greedy
```

### 7. Migrate code endpoint by endpoint
Replace every `db.X.find_one(...)` with SQLAlchemy `session.execute(select(X)...)`. Keep route signatures and response models identical.

### 8. Alembic migrations
```bash
alembic init backend/migrations
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### 9. Data migration script
`scripts/migrate_mongo_to_postgres.py` — read every Mongo collection, insert via SQLAlchemy. Re-embed all signals with BGE-M3.

## Success criteria
- [ ] All 21 endpoints work identically (run pytest suite)
- [ ] RLS verified: user from tenant A cannot read tenant B's signals via direct SQL
- [ ] Qdrant returns >0.7 cosine on Finnish synonym tests (e.g. "resurssipula" matches "henkilöstövaje")
- [ ] Frontend works without changes
- [ ] `_update_clusters()` runs in <1s on 10k fragments

## Rollback plan
Keep MongoDB running parallel for 7 days. Add `USE_POSTGRES=true` flag — if false, fall back to current Mongo paths.
