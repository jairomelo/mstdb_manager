# PostgreSQL Full-Text Search Implementation

## Overview

This application uses PostgreSQL's native full-text search capabilities combined with trigram similarity for fuzzy matching, eliminating the need for Elasticsearch.

## Features

- **Full-Text Search**: Using PostgreSQL's `SearchVector` and `SearchQuery` with Spanish language configuration
- **Fuzzy Matching**: Using `pg_trgm` extension for trigram similarity matching
- **Accent-Insensitive**: Using `unaccent` extension for better Spanish text search
- **Weighted Search**: Different fields have different importance in search results
- **Auto-Updated**: Search vectors are automatically updated via Django signals

## Search Fields by Model

### Documento
- **Weight A (Highest)**: `titulo`
- **Weight B**: `descripcion`
- **Weight C**: `tipo_documento.nombre`
- **Weight D (Lowest)**: `folio`

### Persona (Esclavizada/NoEsclavizada)
- **Weight A**: `nombre_normalizado`, `nombres`, `apellidos`
- **Weight C**: `notas`
- **Weight D**: `ocupacion_categoria`

### Lugar
- **Weight A**: `nombre_lugar`
- **Weight B**: `nombre_pais`, `nombre_region`
- **Weight C**: `sinonimos`
- **Weight D**: `notas`

### Corporacion
- **Weight A**: `nombre_institucion`
- **Weight B**: `nombres_alternativos`
- **Weight C**: `notas`

## API Endpoints

### Individual Model Search
- `GET /api/v2/documentos/search/?q=texto`
- `GET /api/v2/personas-esclavizadas/search/?q=texto`
- `GET /api/v2/personas-no-esclavizadas/search/?q=texto`
- `GET /api/v2/lugares/search/?q=texto`
- `GET /api/v2/corporaciones/search/?q=texto`

### Unified Search
- `GET /api/v2/search/?q=texto&entity_type=all`
  - `entity_type` options: `all`, `documentos`, `personas`, `lugares`, `corporaciones`

## Search Algorithm

1. **Full-Text Search**: Matches against `search_vector` field using Spanish text search configuration
2. **Trigram Similarity**: Fuzzy matching with 30% similarity threshold
3. **Ranking**: Results ordered by:
   - Search rank (full-text relevance)
   - Trigram similarity score
   - Updated timestamp

## Database Indexes

All search operations are optimized with GIN (Generalized Inverted Index) indexes:

```sql
-- Full-text search indexes
CREATE INDEX ON dbgestor_documento USING GIN (search_vector);
CREATE INDEX ON dbgestor_persona USING GIN (search_vector);
CREATE INDEX ON dbgestor_lugar USING GIN (search_vector);
CREATE INDEX ON dbgestor_corporacion USING GIN (search_vector);

-- Trigram similarity indexes
CREATE INDEX ON dbgestor_documento USING GIN (titulo gin_trgm_ops);
CREATE INDEX ON dbgestor_persona USING GIN (nombre_normalizado gin_trgm_ops);
CREATE INDEX ON dbgestor_lugar USING GIN (nombre_lugar gin_trgm_ops);
CREATE INDEX ON dbgestor_corporacion USING GIN (nombre_institucion gin_trgm_ops);
```

## Migrations

### Required Migrations (in order)
1. `0003_enable_search_extensions` - Enables `pg_trgm` and `unaccent` extensions
2. `0004_add_search_fields` - Adds `search_vector` fields and GIN indexes

### Populate Existing Data
After migrations, populate search vectors for existing records:

```bash
python manage.py populate_search_vectors
```

Or populate specific models:
```bash
python manage.py populate_search_vectors --model documento
python manage.py populate_search_vectors --model persona
python manage.py populate_search_vectors --model lugar
python manage.py populate_search_vectors --model corporacion
```

## Automatic Updates

Search vectors are automatically updated when models are saved via Django signals in `dbgestor/signals.py`.

The signals handle:
- Creating new records
- Updating existing records
- Polymorphic models (PersonaEsclavizada, PersonaNoEsclavizada)

## Performance

### Why PostgreSQL Instead of Elasticsearch?

For this application's scale (<100k documents), PostgreSQL full-text search provides:

- ✅ **Simpler Architecture**: No separate search cluster to maintain
- ✅ **Lower Resource Usage**: ~100MB RAM vs 2GB+ for Elasticsearch
- ✅ **ACID Compliance**: No eventual consistency issues
- ✅ **Excellent Spanish Support**: Native `spanish` text search configuration
- ✅ **Fuzzy Matching**: Trigram similarity for typo tolerance
- ✅ **Fast Queries**: <100ms average response time with proper indexes

### When to Consider Elasticsearch

Consider migrating to Elasticsearch if:
- Database grows beyond 1 million searchable documents
- Need advanced features like geospatial queries, ML-based ranking
- Require distributed search across multiple data centers
- Need sub-10ms search response times

## Configuration

### Spanish Language Configuration

PostgreSQL uses the `spanish` text search configuration which provides:
- Spanish stop words removal (de, la, el, etc.)
- Spanish stemming (casa, casas → cas)
- Accent handling via `unaccent` extension

### Similarity Threshold

Current threshold: **0.3 (30% similar)**

Adjust in views.py:
```python
Q(nombre_similarity__gt=0.3)  # Increase for stricter matching
```

## Troubleshooting

### Search returns no results
```bash
# Check if extensions are enabled
psql $DATABASE_URL -c "\dx"
# Should show pg_trgm and unaccent

# Check if search vectors are populated
psql $DATABASE_URL -c "SELECT COUNT(*) FROM dbgestor_documento WHERE search_vector IS NOT NULL;"
```

### Re-populate search vectors
```bash
python manage.py populate_search_vectors
```

### Check index usage
```sql
-- Verify indexes exist
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename LIKE 'dbgestor_%' AND indexdef LIKE '%GIN%';

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan 
FROM pg_stat_user_indexes 
WHERE tablename LIKE 'dbgestor_%';
```

## Example Search Queries

### Simple text search
```python
GET /api/v2/documentos/search/?q=esclavitud

# Returns documents with "esclavitud" in titulo, descripcion, or related fields
```

### Multi-word search
```python
GET /api/v2/personas-esclavizadas/search/?q=María López

# Returns persons with "María López" (uses full-text search + fuzzy matching)
```

### Unified search across all entities
```python
GET /api/v2/search/?q=Cartagena&entity_type=all

# Returns results from documentos, personas, lugares, and corporaciones
```

## Code References

- **Models**: `dbgestor/models.py` - SearchVectorField definitions
- **Signals**: `dbgestor/signals.py` - Auto-update logic
- **Views**: `api/v2/views.py` - Search endpoint implementations
- **Migrations**: `dbgestor/migrations/0003_*.py`, `0004_*.py`
- **Management Command**: `dbgestor/management/commands/populate_search_vectors.py`
