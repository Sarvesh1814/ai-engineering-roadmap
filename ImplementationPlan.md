# 🚀 AI Engineering Roadmap – RAG Specialization

> **Goal:** Become an industry-ready AI/LLM Engineer by mastering Retrieval-Augmented Generation (RAG), building production-quality projects, and creating a strong GitHub portfolio.

---

# 📌 Learning Strategy

This roadmap is **project-first**, not course-first.

For every module:

- 📖 Learn the theory
- 💻 Implement it from scratch
- 📊 Benchmark against alternatives
- 📝 Document findings
- 🚀 Push to GitHub

By the end, you'll have a portfolio demonstrating real engineering skills rather than just completed tutorials.

---

# 🗂 Modules

- [ ] Module 1 – Retrieval
- [ ] Module 2 – Chunking
- [ ] Module 3 – Embeddings
- [ ] Module 4 – Vector Databases
- [ ] Module 5 – Query Optimization
- [ ] Module 6 – Reranking
- [ ] Module 7 – Evaluation
- [ ] Module 8 – Advanced RAG
- [ ] Module 9 – Production
- [ ] Module 10 – Capstone Project

---

# 📘 Module 1 – Retrieval (Week 1)

## 🎯 Goal

Understand **why retrieval works**, not just how to call `.as_retriever()`.

---

## ✅ Topics to Learn

### 1. Similarity Search

- Basic cosine similarity
- Top-K retrieval
- Similarity scores

**Deliverable**

- Understand the baseline retrieval algorithm
- Use it as a comparison for all future retrieval methods

---

### 2. Maximum Marginal Relevance (MMR)

Instead of retrieving:

```
Chunk A
Chunk A'
Chunk A''
Chunk A'''
```

Retrieve:

```
Chunk A
Chunk B
Chunk C
Chunk D
```

### Learn

- lambda parameter
- fetch_k
- k
- Diversity vs relevance

**Deliverable**

Compare:

- Similarity Search
- MMR

Measure:

- Diversity
- Retrieval quality
- Latency

---

### 3. Score Threshold Retrieval

Instead of:

```
Top 5 Chunks
```

Retrieve:

```
All chunks with similarity > Threshold
```

### Learn

- Similarity thresholds
- Precision vs Recall
- Choosing threshold values

---

### 4. Metadata Filtering

Example metadata:

```
Project = AI
Department = HR
Year = 2025
```

Only retrieve documents matching filters.

### Learn

- Metadata indexing
- Filtered search
- Enterprise search use cases

---

### 5. Hybrid Search

Combine:

```
BM25

+

Vector Search
```

### Learn

- BM25
- Sparse embeddings
- Dense embeddings
- Hybrid retrieval

Compare against vector-only retrieval.

---

### 6. Multi Query Retrieval

LLM transforms:

```
How do I migrate Azure pipelines?
```

Into:

```
Pipeline migration

Classic pipeline migration

YAML pipeline migration

Migration guide
```

Each query retrieves documents.

Results are merged together.

### Learn

- Query expansion
- Multi-query generation
- Retrieval fusion

---

### 7. Self Query Retriever

Instead of manually filtering:

```
department = finance
```

The LLM extracts metadata automatically.

Example:

```
Show me AI documents after January
```

↓

```
topic = AI

date > January
```

### Learn

- Metadata extraction
- Structured querying
- Natural language filters

---

### 8. Parent Document Retrieval

Instead of retrieving:

```
200-token chunk
```

Retrieve:

```
Entire parent section
```

### Learn

- Parent-child chunking
- Context preservation
- Retrieval hierarchy

---

### 9. Context Compression

Retrieve:

```
10 Pages
```

Compress into:

```
Only relevant paragraphs
```

before sending to the LLM.

### Learn

- Context compression
- Token reduction
- Cost optimization

---

## 📂 Suggested Repository

```
01-rag-retrieval-benchmarks
```

Suggested notebooks:

```
01_similarity_vs_mmr.ipynb

02_metadata_filtering.ipynb

03_hybrid_search.ipynb

04_multi_query.ipynb

05_self_query.ipynb

06_parent_document.ipynb

07_context_compression.ipynb

08_retrieval_benchmark.ipynb
```

---

# 📘 Module 2 – Chunking

## 🎯 Goal

Understand how chunking impacts retrieval quality.

### Compare

- Recursive Character
- Markdown
- Token
- Semantic
- Parent-Child
- Sentence
- Hierarchical

### Learn

- Chunk overlap
- Chunk size
- Trade-offs
- Best use cases

---

# 📘 Module 3 – Embeddings

## Compare embedding models

- BGE
- E5
- Nomic
- OpenAI
- Voyage
- Jina

### Benchmark

- Embedding dimensions
- Latency
- Retrieval quality
- Multilingual performance
- Memory usage

---

# 📘 Module 4 – Vector Databases

Compare

- FAISS
- Qdrant
- Chroma
- Milvus
- Weaviate

Learn index types

- Flat
- IVF
- HNSW

Understand:

- Search speed
- Memory usage
- Scalability

---

# 📘 Module 5 – Query Optimization

Improve retrieval before embedding search.

Learn

- HyDE
- Step-back Prompting
- Multi-query
- Query Rewriting
- Hypothetical Documents

Benchmark each technique.

---

# 📘 Module 6 – Reranking

Current pipeline

```
Question

↓

Retriever

↓

LLM
```

Improved pipeline

```
Question

↓

Retriever

↓

Reranker

↓

Top Results

↓

LLM
```

Compare rerankers

- BAAI bge-reranker
- Cohere Rerank
- Jina Reranker

Measure

- Latency
- Retrieval quality
- Final answer quality

---

# 📘 Module 7 – Evaluation

Measure whether your RAG system is actually improving.

Questions to answer

- Is retrieval good?
- Are answers grounded?
- Is context relevant?
- Did hallucinations decrease?

Metrics

- Precision@K
- Recall@K
- MRR
- nDCG
- Faithfulness
- Answer Relevance
- Context Precision

Frameworks

- Ragas
- DeepEval

---

# 📘 Module 8 – Advanced RAG

Study architectures

- Corrective RAG
- Adaptive RAG
- Agentic RAG
- Graph RAG
- Knowledge Graph RAG

Understand:

- When to use each
- Advantages
- Limitations

---

# 📘 Module 9 – Production

Production-ready AI systems.

Topics

- Docker
- FastAPI
- Authentication
- Logging
- Monitoring
- Streaming Responses
- Caching
- Rate Limiting

---

# 📘 Module 10 – Capstone Project

## Enterprise Document Assistant

```
Upload PDFs

↓

Hybrid Search

↓

Metadata Filtering

↓

Reranker

↓

Context Compression

↓

Answer Generation

↓

Evaluation Dashboard

↓

Docker

↓

FastAPI

↓

Authentication
```

This should become the flagship project in your GitHub portfolio.

---

# 🎯 End Goal

By completing this roadmap, I should be able to:

- Design production-grade RAG systems
- Compare retrieval strategies with benchmarks
- Optimize retrieval quality
- Evaluate RAG performance using industry metrics
- Deploy scalable AI applications
- Build enterprise-ready AI solutions
- Demonstrate practical AI engineering skills through GitHub projects

---

# 🚀 Portfolio Roadmap

- [ ] 01-rag-retrieval-benchmarks
- [ ] 02-rag-chunking-lab
- [ ] 03-embedding-benchmark
- [ ] 04-vector-db-comparison
- [ ] 05-query-optimization
- [ ] 06-reranking-benchmark
- [ ] 07-rag-evaluation
- [ ] 08-enterprise-rag
- [ ] 09-production-rag-api
- [ ] 10-ai-document-assistant