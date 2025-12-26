#!/usr/bin/env python3
"""
Embeddings - Semantic Search with Vector Similarity

Two modes:
1. TF-IDF (default): No dependencies, fast, good for exact concepts
2. Neural (optional): sentence-transformers, slower, better semantic

Enables searches like:
- "things related to authentication" → finds JWT, OAuth, login
- "performance issues" → finds slow, optimization, cache
"""

import math
import re
import json
import hashlib
from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict
from pathlib import Path


class TFIDFEmbedder:
    """
    TF-IDF based embeddings - zero dependencies.

    Not as good as neural embeddings but:
    - No pip install needed
    - Instant startup
    - Works offline
    - Good enough for most use cases
    """

    MAX_CACHE_SIZE = 1000  # Prevent unbounded memory growth

    def __init__(self):
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.doc_count = 0
        self.embeddings_cache: Dict[str, List[float]] = {}
        self._cache_keys: List[str] = []  # For LRU eviction

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize and normalize text"""
        # Lowercase
        text = text.lower()
        # Split on non-alphanumeric
        tokens = re.findall(r'\b[a-z]+\b', text)
        # Remove stopwords
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
            'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
            'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'under', 'again', 'further', 'then', 'once',
            'here', 'there', 'when', 'where', 'why', 'how', 'all',
            'each', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
            'too', 'very', 'just', 'and', 'but', 'if', 'or', 'because',
            'until', 'while', 'this', 'that', 'these', 'those', 'it',
            'its', 'i', 'you', 'he', 'she', 'we', 'they', 'what',
            'which', 'who', 'whom', 'my', 'your', 'his', 'her', 'our',
        }
        return [t for t in tokens if t not in stopwords and len(t) > 2]

    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        """Compute term frequency"""
        tf = Counter(tokens)
        total = len(tokens)
        return {word: count / total for word, count in tf.items()} if total > 0 else {}

    def fit(self, documents: List[str]):
        """Fit the model on documents to learn IDF"""
        # Invalidate cache since IDF will change
        self.embeddings_cache.clear()
        self._cache_keys.clear()

        self.doc_count = len(documents)
        doc_freq = defaultdict(int)

        # Count document frequency for each term
        for doc in documents:
            tokens = set(self._tokenize(doc))
            for token in tokens:
                doc_freq[token] += 1
                if token not in self.vocabulary:
                    self.vocabulary[token] = len(self.vocabulary)

        # Compute IDF
        for word, freq in doc_freq.items():
            self.idf[word] = math.log(self.doc_count / (1 + freq))

    def embed(self, text: str) -> List[float]:
        """Create embedding vector for text"""
        # Check cache
        cache_key = hashlib.md5(text.encode()).hexdigest()[:16]
        if cache_key in self.embeddings_cache:
            return self.embeddings_cache[cache_key]

        tokens = self._tokenize(text)
        tf = self._compute_tf(tokens)

        # Create sparse vector (only non-zero values)
        vector = {}
        for word, tf_val in tf.items():
            if word in self.idf:
                vector[word] = tf_val * self.idf[word]

        # Normalize
        magnitude = math.sqrt(sum(v * v for v in vector.values()))
        if magnitude > 0:
            vector = {k: v / magnitude for k, v in vector.items()}

        # Cache with LRU eviction
        self.embeddings_cache[cache_key] = vector
        self._cache_keys.append(cache_key)

        # Evict oldest entries if cache too large
        while len(self.embeddings_cache) > self.MAX_CACHE_SIZE:
            old_key = self._cache_keys.pop(0)
            self.embeddings_cache.pop(old_key, None)

        return vector

    def similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Cosine similarity between two vectors"""
        if not vec1 or not vec2:
            return 0.0

        # Dot product
        common_words = set(vec1.keys()) & set(vec2.keys())
        dot = sum(vec1[w] * vec2[w] for w in common_words)

        return dot  # Already normalized

    def find_similar(self, query: str, documents: List[Tuple[int, str]],
                     top_k: int = 5) -> List[Tuple[int, float]]:
        """Find most similar documents to query"""
        query_vec = self.embed(query)

        scores = []
        for doc_id, doc_text in documents:
            doc_vec = self.embed(doc_text)
            score = self.similarity(query_vec, doc_vec)
            scores.append((doc_id, score))

        # Sort by score descending
        scores.sort(key=lambda x: -x[1])
        return scores[:top_k]


class NeuralEmbedder:
    """
    Neural embeddings using sentence-transformers.

    Requires: pip install sentence-transformers

    Much better semantic understanding but:
    - Requires pip install
    - Slower (uses ML model)
    - Uses more memory
    """

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = None
        self.model_name = model_name
        self._load_model()

    def _load_model(self):
        """Load the model (lazy)"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )

    def embed(self, text: str) -> List[float]:
        """Create embedding vector"""
        return self.model.encode(text).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts efficiently"""
        return self.model.encode(texts).tolist()

    def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Cosine similarity"""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = math.sqrt(sum(a * a for a in vec1))
        mag2 = math.sqrt(sum(b * b for b in vec2))
        return dot / (mag1 * mag2) if mag1 > 0 and mag2 > 0 else 0.0

    def find_similar(self, query: str, documents: List[Tuple[int, str]],
                     top_k: int = 5) -> List[Tuple[int, float]]:
        """Find most similar documents"""
        query_vec = self.embed(query)

        scores = []
        for doc_id, doc_text in documents:
            doc_vec = self.embed(doc_text)
            score = self.similarity(query_vec, doc_vec)
            scores.append((doc_id, score))

        scores.sort(key=lambda x: -x[1])
        return scores[:top_k]


class SemanticSearch:
    """
    High-level semantic search interface.

    Automatically uses best available method:
    1. Neural embeddings if sentence-transformers installed
    2. TF-IDF otherwise
    """

    def __init__(self, use_neural: bool = None):
        self.use_neural = use_neural
        self.embedder = None
        self._init_embedder()

    def _init_embedder(self):
        """Initialize the best available embedder"""
        if self.use_neural is True:
            try:
                self.embedder = NeuralEmbedder()
                return
            except ImportError:
                print("Warning: Neural embeddings not available, using TF-IDF")

        if self.use_neural is None:
            # Auto-detect
            try:
                self.embedder = NeuralEmbedder()
                return
            except ImportError:
                pass

        # Fallback to TF-IDF
        self.embedder = TFIDFEmbedder()

    def index_memories(self, memories: List[Dict]):
        """Index memories for search"""
        if isinstance(self.embedder, TFIDFEmbedder):
            # Fit TF-IDF on all documents
            docs = [m.get('content', '') for m in memories]
            self.embedder.fit(docs)

    def search(self, query: str, memories: List[Dict],
               top_k: int = 5, min_score: float = 0.1) -> List[Dict]:
        """
        Semantic search over memories.

        Returns memories sorted by relevance.
        """
        # Prepare documents
        documents = [(m.get('id', i), m.get('content', ''))
                     for i, m in enumerate(memories)]

        # For TF-IDF, ensure it's fitted
        if isinstance(self.embedder, TFIDFEmbedder) and not self.embedder.idf:
            self.embedder.fit([d[1] for d in documents])

        # Find similar
        results = self.embedder.find_similar(query, documents, top_k=top_k * 2)

        # Filter by min score and map back to memories
        memory_map = {m.get('id', i): m for i, m in enumerate(memories)}
        output = []

        for doc_id, score in results:
            if score >= min_score and doc_id in memory_map:
                mem = memory_map[doc_id].copy()
                mem['semantic_score'] = score
                output.append(mem)

        return output[:top_k]

    def find_related(self, memory: Dict, all_memories: List[Dict],
                     top_k: int = 3) -> List[Dict]:
        """Find memories related to a given memory"""
        content = memory.get('content', '')
        # Exclude self
        others = [m for m in all_memories if m.get('id') != memory.get('id')]
        return self.search(content, others, top_k=top_k)


# Singleton
_search = None

def get_semantic_search(use_neural: bool = None) -> SemanticSearch:
    """Get semantic search instance"""
    global _search
    if _search is None:
        _search = SemanticSearch(use_neural=use_neural)
    return _search
