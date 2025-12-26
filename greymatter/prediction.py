#!/usr/bin/env python3
"""
Context Prediction - Predict what memories you'll need

Like human intuition - surfaces relevant memories before you ask.

Features:
- File-based prediction: Opening a file? Get related memories.
- Time-based patterns: Same time as yesterday? Similar context.
- Command patterns: Running tests? Get testing memories.
- Topic chains: Working on auth? Pre-load auth memories.
- Frequently accessed: Recently recalled? Keep warm.
"""

import os
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from collections import Counter, defaultdict
from pathlib import Path


class AccessPattern:
    """Track memory access patterns"""

    def __init__(self):
        self.file_to_memories: Dict[str, Set[int]] = defaultdict(set)
        self.command_to_memories: Dict[str, Set[int]] = defaultdict(set)
        self.time_patterns: Dict[int, List[int]] = defaultdict(list)  # hour -> memory_ids
        self.topic_chains: Dict[str, Set[str]] = defaultdict(set)
        self.access_counts: Counter = Counter()
        self.recent_access: List[int] = []

    def record_access(self, memory_id: int, context: Dict = None):
        """Record memory access with context"""
        self.access_counts[memory_id] += 1
        self.recent_access.append(memory_id)
        if len(self.recent_access) > 100:
            self.recent_access.pop(0)

        if context:
            # File context
            if context.get('file'):
                self.file_to_memories[context['file']].add(memory_id)

            # Command context
            if context.get('command'):
                cmd = context['command'].split()[0]  # First word
                self.command_to_memories[cmd].add(memory_id)

            # Time context
            hour = datetime.now().hour
            self.time_patterns[hour].append(memory_id)

            # Topic context
            if context.get('topic'):
                for other_topic in context.get('related_topics', []):
                    self.topic_chains[context['topic']].add(other_topic)

    def get_frequent(self, limit: int = 10) -> List[int]:
        """Get frequently accessed memories"""
        return [id for id, _ in self.access_counts.most_common(limit)]

    def get_recent(self, limit: int = 10) -> List[int]:
        """Get recently accessed memories"""
        seen = set()
        result = []
        for id in reversed(self.recent_access):
            if id not in seen:
                seen.add(id)
                result.append(id)
                if len(result) >= limit:
                    break
        return result


class ContextPredictor:
    """
    Predict what memories you'll need based on context.

    Works by analyzing:
    1. Current file/directory
    2. Time of day patterns
    3. Recent activity
    4. Topic associations
    """

    def __init__(self):
        self.patterns = AccessPattern()
        self.file_keywords: Dict[str, List[str]] = {}
        self.prediction_cache: Dict[str, List[int]] = {}
        self.cache_ttl = timedelta(minutes=5)
        self.cache_time: Dict[str, datetime] = {}

    def predict(self, context: Dict = None) -> List[int]:
        """
        Predict memory IDs that will be useful.

        Context can include:
        - file: Current file path
        - directory: Current directory
        - command: Command being run
        - query: User's query/prompt
        - topics: Detected topics
        """
        context = context or {}
        predictions = set()

        # 1. File-based prediction
        if context.get('file'):
            predictions.update(self._predict_from_file(context['file']))

        # 2. Directory-based prediction
        if context.get('directory'):
            predictions.update(self._predict_from_directory(context['directory']))

        # 3. Command-based prediction
        if context.get('command'):
            predictions.update(self._predict_from_command(context['command']))

        # 4. Query/topic-based prediction
        if context.get('query'):
            predictions.update(self._predict_from_query(context['query']))

        # 5. Time-based prediction
        predictions.update(self._predict_from_time())

        # 6. Always include frequently accessed
        predictions.update(self.patterns.get_frequent(5))

        # 7. Always include recently accessed
        predictions.update(self.patterns.get_recent(5))

        return list(predictions)

    def record_useful(self, memory_id: int, context: Dict = None):
        """Record that a memory was useful in this context"""
        self.patterns.record_access(memory_id, context)

        # Update file keywords
        if context and context.get('file'):
            file_path = context['file']
            keywords = self._extract_keywords(context.get('query', ''))
            if file_path not in self.file_keywords:
                self.file_keywords[file_path] = []
            self.file_keywords[file_path].extend(keywords)

    def _predict_from_file(self, file_path: str) -> Set[int]:
        """Predict based on current file"""
        predictions = set()

        # Direct file associations
        predictions.update(self.patterns.file_to_memories.get(file_path, set()))

        # File extension associations
        ext = Path(file_path).suffix
        for other_file, memories in self.patterns.file_to_memories.items():
            if Path(other_file).suffix == ext:
                predictions.update(memories)

        # Filename pattern associations
        name = Path(file_path).stem.lower()
        for other_file, memories in self.patterns.file_to_memories.items():
            if name in Path(other_file).stem.lower():
                predictions.update(memories)

        return predictions

    def _predict_from_directory(self, directory: str) -> Set[int]:
        """Predict based on directory"""
        predictions = set()
        dir_path = Path(directory)

        for file_path, memories in self.patterns.file_to_memories.items():
            try:
                if Path(file_path).is_relative_to(dir_path):
                    predictions.update(memories)
            except (ValueError, TypeError):
                pass

        return predictions

    def _predict_from_command(self, command: str) -> Set[int]:
        """Predict based on command being run"""
        predictions = set()

        # Extract command name
        cmd_parts = command.lower().split()
        if not cmd_parts:
            return predictions

        cmd = cmd_parts[0]

        # Direct associations
        predictions.update(self.patterns.command_to_memories.get(cmd, set()))

        # Similar commands
        similar_cmds = {
            'test': ['jest', 'pytest', 'npm', 'cargo'],
            'build': ['npm', 'cargo', 'make', 'gradle'],
            'run': ['npm', 'python', 'node', 'go'],
            'install': ['npm', 'pip', 'cargo', 'brew'],
        }

        for group, cmds in similar_cmds.items():
            if cmd in cmds:
                for similar_cmd in cmds:
                    predictions.update(
                        self.patterns.command_to_memories.get(similar_cmd, set())
                    )

        return predictions

    def _predict_from_query(self, query: str) -> Set[int]:
        """Predict based on query/prompt content"""
        from .embeddings import get_semantic_search
        from .memory import get_memory

        memory = get_memory()
        search = get_semantic_search()

        # Get all memories
        all_memories = memory.get_recent(limit=100)

        # Semantic search
        results = search.search(query, all_memories, top_k=10)

        return {m['id'] for m in results}

    def _predict_from_time(self) -> Set[int]:
        """Predict based on time patterns"""
        hour = datetime.now().hour
        return set(self.patterns.time_patterns.get(hour, [])[-10:])

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction
        words = re.findall(r'\b[a-z]+\b', text.lower())
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by'}
        return [w for w in words if w not in stopwords and len(w) > 3]


class PrefetchManager:
    """
    Manage memory prefetching for fast access.

    Loads predicted memories into a warm cache.
    """

    def __init__(self, max_cache_size: int = 50):
        self.predictor = ContextPredictor()
        self.warm_cache: Dict[int, Dict] = {}
        self.max_cache_size = max_cache_size

    def prefetch(self, context: Dict = None):
        """Prefetch memories based on context"""
        from .memory import get_memory

        memory = get_memory()
        predicted_ids = self.predictor.predict(context)

        # Load into cache
        for mem in memory.get_recent(limit=100):
            if mem['id'] in predicted_ids:
                self.warm_cache[mem['id']] = mem

        # Trim cache if too large
        while len(self.warm_cache) > self.max_cache_size:
            # Remove oldest
            oldest_id = min(self.warm_cache.keys())
            del self.warm_cache[oldest_id]

    def get_cached(self, memory_id: int) -> Optional[Dict]:
        """Get memory from cache if available"""
        return self.warm_cache.get(memory_id)

    def get_predicted_context(self, context: Dict = None, limit: int = 10) -> str:
        """Get predicted context as string for injection"""
        from .memory import get_memory

        memory = get_memory()

        # Prefetch
        self.prefetch(context)

        # Get predicted memories
        predicted_ids = self.predictor.predict(context)[:limit]

        # Build context
        parts = ["## Predicted Context (you might need these)"]

        for mem_id in predicted_ids:
            # Try cache first
            mem = self.warm_cache.get(mem_id)
            if not mem:
                # Fallback to database
                continue

            parts.append(f"- [{mem.get('type', 'note')}] {mem['content'][:100]}")

        if len(parts) == 1:
            return ""

        return '\n'.join(parts)


# Singleton
_predictor = None
_prefetch = None

def get_predictor() -> ContextPredictor:
    global _predictor
    if _predictor is None:
        _predictor = ContextPredictor()
    return _predictor

def get_prefetch() -> PrefetchManager:
    global _prefetch
    if _prefetch is None:
        _prefetch = PrefetchManager()
    return _prefetch
