---
name: vector-search
description: ChromaDB semantic vector retrieval using nomic-embed-text-v1.5 (384-dim), RAG pipelines, and hybrid search
triggers: [chroma, vector search, semantic search, embedding, similarity, retrieve, nomic, rag, nearest neighbor, vector store, chromadb, dense retrieval, hybrid search]
roles: [reasoner, tandem, coder]
---

## When to activate
User asks for semantic search, RAG-style retrieval, embedding-based lookup, or ChromaDB operations.

## Embedding model
**nomic-embed-text-v1.5** — 384-dimensional dense embeddings
- Context window: 8192 tokens
- Matryoshka dimensions supported: 64, 128, 256, 384
- Instruction prefix for retrieval tasks: `"search_query: "` (query), `"search_document: "` (document)

## ChromaDB collection schema
```python
import chromadb
from chromadb.utils import embedding_functions

nomic_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="nomic-ai/nomic-embed-text-v1.5",
    trust_remote_code=True
)

client = chromadb.HttpClient(host="chroma", port=8000)   # docker-internal
collection = client.get_or_create_collection(
    name="agent_q3",
    embedding_function=nomic_ef,
    metadata={"hnsw:space": "cosine"}   # cosine distance (default)
)
```

## Adding documents
```python
collection.add(
    ids=["doc_001", "doc_002"],
    documents=["search_document: <text>", "search_document: <text>"],
    metadatas=[{"source": "arxiv", "domain": "research"}, {"source": "github"}]
)
```

## Querying
```python
results = collection.query(
    query_texts=["search_query: <user query>"],
    n_results=5,
    where={"domain": "research"},        # optional metadata filter
    include=["documents", "metadatas", "distances"]
)
# results["distances"][0] — cosine distances (lower = more similar)
```

## Via MCP bridge
```
POST http://mcp-bridge:8004/mcp/call
{
  "server": "chroma-mcp",
  "tool": "query_collection",
  "args": {
    "collection": "agent_q3",
    "query": "<user query>",
    "n_results": 5
  }
}
```

## Hybrid search (ChromaDB semantic + Redis exact match)

Use when you need both semantic similarity AND exact keyword or session memory:

1. **Redis** (via `memory_skill`) — exact match on tags, session IDs, canonical facts
2. **ChromaDB** — top-k semantic neighbours for the same query
3. **Merge**: interleave results, deduplicate by document ID, rank by combined score

```python
# Reciprocal Rank Fusion (simple merge)
def rrf(redis_results, chroma_results, k=60):
    scores = {}
    for rank, doc_id in enumerate(redis_results):
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
    for rank, doc_id in enumerate(chroma_results):
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)
```

## Matryoshka truncation (speed vs. quality tradeoff)
```python
# For low-latency retrieval, truncate to 128 dims
collection_fast = client.get_or_create_collection(
    name="agent_q3_fast",
    embedding_function=nomic_ef,
    metadata={"hnsw:space": "cosine", "embedding_dim": 128}
)
```

## RAG pipeline (retrieve → augment → generate)
1. Embed user query with nomic-embed-text-v1.5
2. Query ChromaDB for top-5 relevant chunks
3. Prepend retrieved chunks to system prompt
4. Route to appropriate model:
   - Short context (< 4K tokens): Harmonic-Hermes
   - Long context (> 4K tokens): Kimi-Linear (1M ctx window)

## Snapshot restore
ChromaDB vector snapshots are stored in HF bucket `MADdegens/agent-q3` under `hq/chroma/`.
To restore:
```bash
huggingface-cli download MADdegens/agent-q3 --include "hq/chroma/**" --local-dir ./data/chroma
# Then mount ./data/chroma as the ChromaDB persistence directory
```
