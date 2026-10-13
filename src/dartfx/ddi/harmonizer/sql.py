"""PostgreSQL DDL, indexing, and CTE query generators for Resource Banks and Catalogs.

Generates production-grade SQL for:
- JSONB `hashes` schema and table creation
- Expression B-Tree indexes on root digests and sub-facets (O(1) lookups)
- GIN Trigram indexes on signatures (`pg_trgm`)
- Multi-tier matching Common Table Expression (CTE) queries
"""

from __future__ import annotations


def generate_bank_schema_ddl(table_name: str = "resource_bank") -> str:
    """Generates PostgreSQL DDL with optimized expression and trigram indexes."""
    return f"""-- Enable PostgreSQL Trigram extension for fuzzy string matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Table definition for {table_name}
CREATE TABLE IF NOT EXISTS {table_name} (
    urn TEXT PRIMARY KEY,
    resource_type VARCHAR(64) NOT NULL,
    canonical_urn TEXT REFERENCES {table_name}(urn) ON DELETE SET NULL,
    payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    hashes JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 1. Exact Merkle Root Digest lookup (B-Tree: O(1) exact content deduplication)
CREATE INDEX IF NOT EXISTS idx_{table_name}_hash_root
ON {table_name} (((hashes->>'root')));

-- 2. Permutation / Unordered Set Digest lookup (B-Tree: O(1) set matching)
CREATE INDEX IF NOT EXISTS idx_{table_name}_hash_unordered
ON {table_name} (((hashes->>'unordered')))
WHERE hashes->>'unordered' IS NOT NULL;

-- 3. Expression B-Tree indexes on core Merkle sub-facets
CREATE INDEX IF NOT EXISTS idx_{table_name}_facet_literal
ON {table_name} (((hashes->'facets'->>'literal')))
WHERE hashes->'facets'->>'literal' IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_{table_name}_facet_pivot_literal
ON {table_name} (((hashes->'facets'->>'pivot_literal')))
WHERE hashes->'facets'->>'pivot_literal' IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_{table_name}_facet_subst_set
ON {table_name} (((hashes->'facets'->>'substantive_code_set')))
WHERE hashes->'facets'->>'substantive_code_set' IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_{table_name}_facet_category_set
ON {table_name} (((hashes->'facets'->>'category_set')))
WHERE hashes->'facets'->>'category_set' IS NOT NULL;

-- 4. GIN Index on all JSONB facets (supports arbitrary @> containment queries)
CREATE INDEX IF NOT EXISTS idx_{table_name}_hashes_facets_gin
ON {table_name} USING gin ((hashes->'facets'));

-- 5. GIN Trigram Index on normalized text signature for fuzzy similarity
CREATE INDEX IF NOT EXISTS idx_{table_name}_sig_trgm
ON {table_name} USING gin (((hashes->>'signature')) gin_trgm_ops);
"""


def generate_tiered_matching_cte_query(table_name: str = "resource_bank") -> str:
    """Generates parameterized SQL query executing 4-tier matching for a candidate resource."""
    return f"""-- 4-Tier Match Query for Candidate Resource
-- Parameters:
--   $1: Candidate URN
--   $2: Candidate Root Digest (hashes->>'root')
--   $3: Candidate Literal Facet Digest (hashes->'facets'->>'literal')
--   $4: Candidate Pivot Literal Facet Digest (hashes->'facets'->>'pivot_literal')
--   $5: Candidate Signature String (hashes->>'signature')
--   $6: Minimum Fuzzy Similarity Threshold (e.g. 0.70)

WITH tier1_urn AS (
    SELECT
        urn,
        canonical_urn,
        1.0::float AS score,
        'IDENTIFIER_EXACT' AS match_type,
        1 AS tier_priority,
        'Matched by identical primary URN' AS reason
    FROM {table_name}
    WHERE urn = $1
),
tier2_root_exact AS (
    SELECT
        urn,
        canonical_urn,
        1.0::float AS score,
        'CONTENT_EXACT' AS match_type,
        2 AS tier_priority,
        'Matched by exact cryptographic Merkle root digest' AS reason
    FROM {table_name}
    WHERE (hashes->>'root') = $2
      AND NOT EXISTS (SELECT 1 FROM tier1_urn)
),
tier3_facet_exact AS (
    SELECT
        urn,
        canonical_urn,
        0.95::float AS score,
        'FACET_EXACT' AS match_type,
        3 AS tier_priority,
        CASE
            WHEN (hashes->'facets'->>'literal') = $3 THEN 'Matched by exact prompt literal facet'
            ELSE 'Matched by cross-lingual pivot literal facet'
        END AS reason
    FROM {table_name}
    WHERE (
        ((hashes->'facets'->>'literal') = $3 AND $3 IS NOT NULL)
        OR
        ((hashes->'facets'->>'pivot_literal') = $4 AND $4 IS NOT NULL)
    )
      AND NOT EXISTS (SELECT 1 FROM tier1_urn)
      AND NOT EXISTS (SELECT 1 FROM tier2_root_exact)
),
tier4_fuzzy_trgm AS (
    SELECT
        urn,
        canonical_urn,
        similarity((hashes->>'signature'), $5)::float AS score,
        'FUZZY_SIMILARITY' AS match_type,
        4 AS tier_priority,
        'Matched via PostgreSQL pg_trgm signature similarity' AS reason
    FROM {table_name}
    WHERE (hashes->>'signature') % $5
      AND similarity((hashes->>'signature'), $5) >= $6
      AND NOT EXISTS (SELECT 1 FROM tier1_urn)
      AND NOT EXISTS (SELECT 1 FROM tier2_root_exact)
      AND NOT EXISTS (SELECT 1 FROM tier3_facet_exact)
    ORDER BY score DESC
    LIMIT 5
)
SELECT * FROM tier1_urn
UNION ALL
SELECT * FROM tier2_root_exact
UNION ALL
SELECT * FROM tier3_facet_exact
UNION ALL
SELECT * FROM tier4_fuzzy_trgm
ORDER BY tier_priority ASC, score DESC;
"""
