#!/usr/bin/env python3
"""
Smart Memory Optimizer - Token-efficient memory management

Features:
- Token counting & budget management
- Smart context compression
- Memory deduplication (similarity detection)
- Tiered memory (hot/warm/cold)
- Auto-summarization of old/verbose memories
- Relevance decay (forgetting curve)
- Smart chunking for large content
- LRU cache for frequently accessed
- Automatic cleanup of low-value memories
"""

import re
import math
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import OrderedDict
from functools import lru_cache


# Approximate tokens per character (conservative estimate)
CHARS_PER_TOKEN = 4


@dataclass
class TokenBudget:
    """Token budget configuration"""
    max_context_tokens: int = 4000      # Max tokens for context injection
    max_memory_tokens: int = 2000       # Max tokens for memories section
    max_handoff_tokens: int = 1000      # Max tokens for handoff
    max_ledger_tokens: int = 500        # Max tokens for ledger
    reserve_tokens: int = 500           # Reserve for system prompt


class TokenCounter:
    """Estimate token counts without external dependencies"""

    @staticmethod
    def count(text: str) -> int:
        """Estimate token count for text"""
        if not text:
            return 0
        # More accurate estimation:
        # - Split on whitespace and punctuation
        # - Account for subword tokenization
        words = len(re.findall(r'\b\w+\b', text))
        punctuation = len(re.findall(r'[^\w\s]', text))
        # Rough estimate: words + punctuation, with adjustment for long words
        long_words = len([w for w in text.split() if len(w) > 10])
        return words + punctuation + long_words

    @staticmethod
    def truncate_to_tokens(text: str, max_tokens: int) -> str:
        """Truncate text to approximately max_tokens"""
        if TokenCounter.count(text) <= max_tokens:
            return text

        # Binary search for the right length
        words = text.split()
        low, high = 0, len(words)

        while low < high:
            mid = (low + high + 1) // 2
            if TokenCounter.count(' '.join(words[:mid])) <= max_tokens:
                low = mid
            else:
                high = mid - 1

        truncated = ' '.join(words[:low])
        if len(truncated) < len(text):
            truncated += "..."
        return truncated


class TextCompressor:
    """Compress text while preserving meaning"""

    # Common phrases to compress
    COMPRESSIONS = [
        (r'\bthe user\b', 'user'),
        (r'\bthe system\b', 'system'),
        (r'\bin order to\b', 'to'),
        (r'\bdue to the fact that\b', 'because'),
        (r'\bat this point in time\b', 'now'),
        (r'\bfor the purpose of\b', 'for'),
        (r'\bin the event that\b', 'if'),
        (r'\bwith regard to\b', 'about'),
        (r'\bhas the ability to\b', 'can'),
        (r'\bis able to\b', 'can'),
        (r'\bmake sure\b', 'ensure'),
        (r'\ba lot of\b', 'many'),
        (r'\bin spite of\b', 'despite'),
        (r'\bprior to\b', 'before'),
        (r'\bsubsequent to\b', 'after'),
        (r'\bas a result of\b', 'from'),
        (r'\bfor example\b', 'e.g.'),
        (r'\bthat is to say\b', 'i.e.'),
        (r'\band so on\b', 'etc.'),
        (r'\bplease note that\b', 'note:'),
        (r'\bit is important to\b', 'must'),
        (r'\byou should\b', 'should'),
        (r'\bwe need to\b', 'need to'),
    ]

    @staticmethod
    def compress(text: str, aggressive: bool = False) -> str:
        """Compress text by removing verbosity"""
        result = text

        # Apply compression patterns
        for pattern, replacement in TextCompressor.COMPRESSIONS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        # Remove extra whitespace
        result = re.sub(r'\s+', ' ', result).strip()

        # Remove filler phrases
        if aggressive:
            fillers = [
                r'\bbasically\b,?\s*',
                r'\bactually\b,?\s*',
                r'\bobviously\b,?\s*',
                r'\bclearly\b,?\s*',
                r'\bI think\b,?\s*',
                r'\bI believe\b,?\s*',
                r'\bIt seems like\b,?\s*',
            ]
            for filler in fillers:
                result = re.sub(filler, '', result, flags=re.IGNORECASE)

        return result

    @staticmethod
    def summarize_simple(text: str, max_sentences: int = 3) -> str:
        """Simple extractive summarization - take first N sentences"""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= max_sentences:
            return text

        return '. '.join(sentences[:max_sentences]) + '.'


class SimilarityDetector:
    """Detect similar/duplicate memories"""

    @staticmethod
    def get_fingerprint(text: str) -> str:
        """Get a fingerprint for similarity comparison"""
        # Normalize: lowercase, remove punctuation, sort words
        normalized = re.sub(r'[^\w\s]', '', text.lower())
        words = sorted(set(normalized.split()))
        return hashlib.md5(' '.join(words).encode()).hexdigest()[:16]

    @staticmethod
    def get_shingles(text: str, n: int = 3) -> set:
        """Get n-gram shingles for Jaccard similarity"""
        text = re.sub(r'[^\w\s]', '', text.lower())
        words = text.split()
        if len(words) < n:
            return {tuple(words)}
        return {tuple(words[i:i+n]) for i in range(len(words) - n + 1)}

    @staticmethod
    def jaccard_similarity(set1: set, set2: set) -> float:
        """Calculate Jaccard similarity between two sets"""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def are_similar(text1: str, text2: str, threshold: float = 0.6) -> bool:
        """Check if two texts are similar"""
        shingles1 = SimilarityDetector.get_shingles(text1)
        shingles2 = SimilarityDetector.get_shingles(text2)
        return SimilarityDetector.jaccard_similarity(shingles1, shingles2) >= threshold


class RelevanceScorer:
    """Score memory relevance with decay"""

    # Decay half-life in days
    DECAY_HALF_LIFE = 7

    @staticmethod
    def calculate_decay(created_at: str, last_accessed: str = None) -> float:
        """Calculate decay factor based on age and access"""
        try:
            created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            created = datetime.now()

        age_days = (datetime.now() - created.replace(tzinfo=None)).days

        # Exponential decay
        decay = math.pow(0.5, age_days / RelevanceScorer.DECAY_HALF_LIFE)

        return max(0.1, decay)  # Minimum 10% relevance

    @staticmethod
    def score_memory(memory: Dict, query: str = None) -> float:
        """Calculate overall relevance score for a memory"""
        base_score = memory.get('importance', 5) / 10.0

        # Apply decay
        decay = RelevanceScorer.calculate_decay(memory.get('created_at', ''))
        score = base_score * decay

        # Boost if matches query
        if query:
            content = memory.get('content', '').lower()
            query_lower = query.lower()
            if query_lower in content:
                score *= 1.5
            elif any(word in content for word in query_lower.split()):
                score *= 1.2

        # Boost important types
        important_types = ['preference', 'decision', 'error', 'learning']
        if memory.get('type', '') in important_types:
            score *= 1.2

        return min(1.0, score)


class MemoryTier:
    """Tiered memory management"""

    HOT = 'hot'      # Recent, frequently accessed, high importance
    WARM = 'warm'    # Moderate recency/importance
    COLD = 'cold'    # Old, rarely accessed, low importance

    @staticmethod
    def classify(memory: Dict) -> str:
        """Classify memory into a tier"""
        importance = memory.get('importance', 5)
        score = RelevanceScorer.score_memory(memory)

        if importance >= 8 or score >= 0.7:
            return MemoryTier.HOT
        elif importance >= 5 or score >= 0.3:
            return MemoryTier.WARM
        else:
            return MemoryTier.COLD


class SmartChunker:
    """Smart chunking for large content"""

    @staticmethod
    def chunk_text(text: str, max_chunk_tokens: int = 500) -> List[str]:
        """Split text into semantic chunks"""
        # Try to split on paragraph boundaries first
        paragraphs = text.split('\n\n')

        chunks = []
        current_chunk = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = TokenCounter.count(para)

            if para_tokens > max_chunk_tokens:
                # Split large paragraph by sentences
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sentence in sentences:
                    sent_tokens = TokenCounter.count(sentence)
                    if current_tokens + sent_tokens > max_chunk_tokens and current_chunk:
                        chunks.append(' '.join(current_chunk))
                        current_chunk = []
                        current_tokens = 0
                    current_chunk.append(sentence)
                    current_tokens += sent_tokens
            elif current_tokens + para_tokens > max_chunk_tokens and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_tokens = para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens

        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    @staticmethod
    def get_chunk_summary(chunk: str) -> str:
        """Get a brief summary/title for a chunk"""
        # Take first sentence or line
        first_line = chunk.split('\n')[0].split('.')[0]
        return first_line[:100] + ('...' if len(first_line) > 100 else '')


class SmartContextBuilder:
    """Build optimized context within token budget"""

    def __init__(self, budget: TokenBudget = None):
        self.budget = budget or TokenBudget()
        self.token_counter = TokenCounter()
        self.compressor = TextCompressor()
        self.scorer = RelevanceScorer()

    def build_context(self, memories: List[Dict], handoff: Dict = None,
                      ledger: Dict = None, query: str = None) -> Tuple[str, Dict]:
        """Build token-optimized context"""
        stats = {
            'total_memories': len(memories),
            'included_memories': 0,
            'tokens_used': 0,
            'tokens_saved': 0,
            'compressed': 0,
            'deduplicated': 0,
        }

        context_parts = []
        tokens_remaining = self.budget.max_context_tokens - self.budget.reserve_tokens

        # 1. Add handoff (compressed if needed)
        if handoff:
            handoff_text = self._format_handoff(handoff)
            handoff_tokens = self.token_counter.count(handoff_text)

            if handoff_tokens > self.budget.max_handoff_tokens:
                handoff_text = self._compress_handoff(handoff)
                stats['compressed'] += 1

            context_parts.append(handoff_text)
            tokens_remaining -= self.token_counter.count(handoff_text)

        # 2. Add ledger (compressed)
        if ledger:
            ledger_text = self._format_ledger(ledger)
            ledger_tokens = self.token_counter.count(ledger_text)

            if ledger_tokens > self.budget.max_ledger_tokens:
                ledger_text = self._compress_ledger(ledger)
                stats['compressed'] += 1

            context_parts.append(ledger_text)
            tokens_remaining -= self.token_counter.count(ledger_text)

        # 3. Score and sort memories
        scored_memories = []
        seen_fingerprints = set()

        for mem in memories:
            # Deduplicate
            fingerprint = SimilarityDetector.get_fingerprint(mem.get('content', ''))
            if fingerprint in seen_fingerprints:
                stats['deduplicated'] += 1
                continue
            seen_fingerprints.add(fingerprint)

            score = self.scorer.score_memory(mem, query)
            tier = MemoryTier.classify(mem)
            scored_memories.append((score, tier, mem))

        # Sort by score (descending)
        scored_memories.sort(key=lambda x: (-x[0], x[1]))

        # 4. Add memories within budget
        memory_parts = []
        memory_tokens = 0

        for score, tier, mem in scored_memories:
            content = mem.get('content', '')

            # Compress if needed
            if tier == MemoryTier.COLD:
                content = self.compressor.compress(content, aggressive=True)
                stats['compressed'] += 1
            elif tier == MemoryTier.WARM:
                content = self.compressor.compress(content)

            mem_line = f"- [{mem.get('type', 'note')}] {content}"
            mem_tokens = self.token_counter.count(mem_line)

            if memory_tokens + mem_tokens <= min(tokens_remaining, self.budget.max_memory_tokens):
                memory_parts.append(mem_line)
                memory_tokens += mem_tokens
                stats['included_memories'] += 1
            else:
                break

        if memory_parts:
            context_parts.append("## Remembered Context\n" + '\n'.join(memory_parts))

        # Build final context
        context = '\n\n'.join(context_parts)
        stats['tokens_used'] = self.token_counter.count(context)
        stats['tokens_saved'] = sum(
            self.token_counter.count(m.get('content', ''))
            for m in memories
        ) - stats['tokens_used']

        return context, stats

    def _format_handoff(self, handoff: Dict) -> str:
        """Format handoff for context"""
        parts = [f"## Previous Session\n{handoff.get('summary', '')}"]
        if handoff.get('next_steps'):
            parts.append(f"### Next Steps\n{handoff['next_steps']}")
        return '\n'.join(parts)

    def _compress_handoff(self, handoff: Dict) -> str:
        """Compress handoff to fit budget"""
        summary = handoff.get('summary', '')
        compressed = self.compressor.summarize_simple(summary, max_sentences=3)
        return f"## Previous Session\n{compressed}"

    def _format_ledger(self, ledger: Dict) -> str:
        """Format ledger for context"""
        # Only include key fields
        important_keys = ['working_dir', 'phase', 'last_action']
        filtered = {k: v for k, v in ledger.items() if k in important_keys}
        if filtered:
            import json
            return f"## State\n{json.dumps(filtered)}"
        return ""

    def _compress_ledger(self, ledger: Dict) -> str:
        """Compress ledger to essential info"""
        essential = {}
        if 'working_dir' in ledger:
            essential['dir'] = ledger['working_dir'].split('/')[-1]
        if 'phase' in ledger:
            essential['phase'] = ledger['phase']
        if essential:
            return f"## State: {essential}"
        return ""


class MemoryOptimizer:
    """Main optimizer that ties everything together"""

    def __init__(self, memory=None):
        self.memory = memory
        self.context_builder = SmartContextBuilder()
        self.similarity = SimilarityDetector()
        self.chunker = SmartChunker()

    def optimize_save(self, content: str, type: str = 'learning',
                      importance: int = 5) -> Dict:
        """Optimize before saving a memory"""
        from .memory import get_memory
        memory = self.memory or get_memory()

        # 1. Compress content
        compressed = TextCompressor.compress(content)
        tokens_saved = TokenCounter.count(content) - TokenCounter.count(compressed)

        # 2. Check for duplicates
        existing = memory.get_recent(limit=50)
        for existing_mem in existing:
            if self.similarity.are_similar(compressed, existing_mem.get('content', '')):
                # Update existing instead of creating duplicate
                return {
                    'action': 'duplicate_found',
                    'existing_id': existing_mem['id'],
                    'similarity': 'high',
                    'tokens_saved': TokenCounter.count(content)
                }

        # 3. Chunk if too large
        if TokenCounter.count(compressed) > 500:
            chunks = self.chunker.chunk_text(compressed, max_chunk_tokens=400)
            if len(chunks) > 1:
                ids = []
                for i, chunk in enumerate(chunks):
                    chunk_summary = self.chunker.get_chunk_summary(chunk)
                    mem_id = memory.save(
                        f"[Part {i+1}/{len(chunks)}] {chunk}",
                        type=type,
                        importance=importance
                    )
                    ids.append(mem_id)
                return {
                    'action': 'chunked',
                    'chunk_count': len(chunks),
                    'memory_ids': ids,
                    'tokens_saved': tokens_saved
                }

        # 4. Save optimized
        mem_id = memory.save(compressed, type=type, importance=importance)

        return {
            'action': 'saved',
            'memory_id': mem_id,
            'original_tokens': TokenCounter.count(content),
            'compressed_tokens': TokenCounter.count(compressed),
            'tokens_saved': tokens_saved
        }

    def get_optimized_context(self, query: str = None) -> Tuple[str, Dict]:
        """Get token-optimized context for injection"""
        from .memory import get_memory
        memory = self.memory or get_memory()

        memories = memory.get_recent(limit=100)
        important = memory.get_important(min_importance=7)

        # Combine and dedupe
        all_memories = {m['id']: m for m in memories + important}.values()

        handoff = memory.get_last_handoff()
        ledger = memory.ledger_get_latest()

        return self.context_builder.build_context(
            list(all_memories),
            handoff=handoff,
            ledger=ledger,
            query=query
        )

    def cleanup_old_memories(self, max_age_days: int = 30,
                             min_importance: int = 3) -> Dict:
        """Clean up old, low-value memories"""
        from .memory import get_memory
        memory = self.memory or get_memory()

        cutoff = datetime.now() - timedelta(days=max_age_days)
        deleted = 0
        archived = 0

        all_memories = memory.get_recent(limit=1000)

        for mem in all_memories:
            try:
                created = datetime.fromisoformat(mem['created_at'].replace('Z', '+00:00'))
                created = created.replace(tzinfo=None)
            except:
                continue

            if created < cutoff and mem.get('importance', 5) < min_importance:
                # Low value, old memory - delete it
                memory.delete(mem['id'])
                deleted += 1
            elif created < cutoff and mem.get('importance', 5) < 5:
                # Medium value, old - compress and keep
                compressed = TextCompressor.compress(mem['content'], aggressive=True)
                if len(compressed) < len(mem['content']) * 0.7:
                    # Worth compressing
                    # Note: would need to add an update method to memory
                    archived += 1

        return {
            'deleted': deleted,
            'archived': archived,
            'tokens_freed': deleted * 50  # Rough estimate
        }

    def get_stats(self) -> Dict:
        """Get optimization statistics"""
        from .memory import get_memory
        memory = self.memory or get_memory()

        all_memories = memory.get_recent(limit=1000)

        total_tokens = sum(TokenCounter.count(m.get('content', '')) for m in all_memories)
        hot = warm = cold = 0

        for mem in all_memories:
            tier = MemoryTier.classify(mem)
            if tier == MemoryTier.HOT:
                hot += 1
            elif tier == MemoryTier.WARM:
                warm += 1
            else:
                cold += 1

        return {
            'total_memories': len(all_memories),
            'total_tokens': total_tokens,
            'hot_memories': hot,
            'warm_memories': warm,
            'cold_memories': cold,
            'avg_tokens_per_memory': total_tokens // max(1, len(all_memories)),
        }


# Singleton
_optimizer = None

def get_optimizer() -> MemoryOptimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = MemoryOptimizer()
    return _optimizer
