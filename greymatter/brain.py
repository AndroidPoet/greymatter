#!/usr/bin/env python3
"""
Brain - Human-Like Memory System

Works like a real human brain:
1. PERCEPTION → Sensory input analyzed for meaning
2. ATTENTION → Important things get more focus
3. ENCODING → Meaningful info stored to memory
4. CONSOLIDATION → Background processing (like sleep)
5. RETRIEVAL → Relevant memories surface automatically
6. FORGETTING → Unimportant things fade

Two modes:
- CortexLite (default): Fast, rule-based, no external AI calls
- Cortex: Background AI processing (optional, uses tokens)

NO MANUAL COMMANDS - Everything is automatic!
"""

import re
import threading
import time
import heapq
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


class MemoryType:
    """Types of memory (like human memory systems)"""
    SENSORY = "sensory"        # Brief, mostly filtered out
    WORKING = "working"        # Short-term, limited capacity
    EPISODIC = "episodic"      # Events, experiences
    SEMANTIC = "semantic"      # Facts, knowledge
    PROCEDURAL = "procedural"  # How-to, skills


@dataclass
class Thought:
    """A thought in working memory"""
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    importance: float = 0.5
    intent: str = "unknown"
    concepts: List[str] = field(default_factory=list)

    def __lt__(self, other):
        """For heapq - lower importance = smaller (gets evicted first)"""
        return self.importance < other.importance


class Brain:
    """
    Human-Like Memory System

    Just use:
    - brain.perceive(text) → Process any input
    - brain.recall(query) → Get relevant context
    - brain.sleep() → Consolidate memories

    Everything else is automatic!
    """

    # Working memory limit (Miller's Law: 7±2)
    WORKING_MEMORY_LIMIT = 7

    def __init__(self, use_ai_cortex: bool = False):
        """
        Initialize brain.

        Args:
            use_ai_cortex: If True, uses background AI for deeper understanding.
                          If False (default), uses fast rule-based processing.
        """
        from .memory import get_memory
        from .smart import get_optimizer
        from .understanding import get_analyzer

        self.memory = get_memory()
        self.optimizer = get_optimizer()
        self.analyzer = get_analyzer()

        # Working memory (like human short-term memory)
        self.working_memory: List[Thought] = []

        # Background processing
        self.use_ai_cortex = use_ai_cortex
        if use_ai_cortex:
            from .cortex import get_cortex
            self.cortex = get_cortex(use_ai=True)
        else:
            self.cortex = None

        # Consolidation thread
        self._consolidation_thread = None
        self._stop_event = threading.Event()
        self._start_background()

    def perceive(self, text: str) -> Dict:
        """
        Perceive new information - main entry point.

        Like human perception:
        1. Sensory filter (ignore noise)
        2. Attention (focus on important)
        3. Understanding (extract meaning)
        4. Encoding (store if important)

        Returns what was understood and remembered.
        """
        from .understanding import understand

        result = {
            'processed': True,
            'understood': False,
            'remembered': False,
            'importance': 0.0,
            'intent': 'unknown',
            'concepts': [],
        }

        # 1. SENSORY FILTER - Ignore trivial input
        if not self._passes_sensory_filter(text):
            return result

        # 2. UNDERSTANDING - Analyze meaning (not just keywords!)
        understanding = understand(text)

        result['understood'] = True
        result['importance'] = understanding.memory_score
        result['intent'] = understanding.intent.value
        result['concepts'] = understanding.key_concepts

        # 3. ATTENTION - Add to working memory
        thought = Thought(
            content=text[:500],
            importance=understanding.memory_score,
            intent=understanding.intent.value,
            concepts=understanding.key_concepts
        )
        self._add_to_working_memory(thought)

        # 4. ENCODING - Store if memorable
        if understanding.is_memorable:
            self._encode_to_long_term(understanding.summary, understanding)
            result['remembered'] = True

        # 5. BACKGROUND PROCESSING - If AI cortex enabled
        if self.cortex and self.use_ai_cortex:
            self.cortex.observe(text)

        return result

    def recall(self, query: str = None, limit: int = 5) -> str:
        """
        Recall relevant memories.

        Like human recall:
        - Recent things are easier to remember
        - Important things surface first
        - Related concepts trigger associations
        """
        context_parts = []

        # 1. Working memory (immediate context)
        if self.working_memory:
            recent = [t.content[:100] for t in self.working_memory[-3:]]
            context_parts.append("Recent:\n" + "\n".join(f"• {r}" for r in recent))

        # 2. Long-term memory (optimized retrieval)
        lt_context, stats = self.optimizer.get_optimized_context(query=query)
        if lt_context:
            context_parts.append(lt_context)

        # 3. Query-specific recall
        if query:
            matches = self.memory.search(query, limit=limit)
            if matches:
                match_text = "\n".join(f"• {m['content'][:80]}" for m in matches)
                context_parts.append(f"Related:\n{match_text}")

        return "\n\n".join(context_parts)

    def sleep(self) -> Dict:
        """
        Memory consolidation (like sleep).

        - Moves important working memory to long-term
        - Compresses old memories
        - Removes duplicates
        - Strengthens frequently accessed memories
        """
        result = {
            'consolidated': 0,
            'compressed': 0,
            'forgotten': 0,
        }

        # 1. Consolidate working memory
        for thought in self.working_memory:
            if thought.importance >= 0.5:
                from .understanding import Understanding, Intent, Emphasis

                # Create a minimal understanding for encoding
                self._encode_to_long_term(thought.content[:200], None, thought.importance)
                result['consolidated'] += 1

        # Clear working memory
        self.working_memory = []

        # 2. Clean up old memories
        cleanup = self.optimizer.cleanup_old_memories(max_age_days=14, min_importance=4)
        result['forgotten'] = cleanup.get('deleted', 0)

        # 3. Cortex consolidation if enabled
        if self.cortex and hasattr(self.cortex, 'consolidate'):
            self.cortex.consolidate()

        return result

    def forget(self, query: str) -> int:
        """Actively forget something (like suppression)"""
        matches = self.memory.search(query, limit=10)
        count = 0
        for m in matches:
            self.memory.delete(m['id'])
            count += 1
        return count

    def get_state(self) -> Dict:
        """Get brain state summary"""
        stats = self.optimizer.get_stats()

        # Extract recent learnings from working memory
        recent_learnings = [
            t.content[:100] for t in self.working_memory
            if t.importance >= 0.5 and t.intent in ('learning', 'decision', 'preference', 'solution')
        ]

        # Also get recent important memories
        recent_memories = self.memory.get_recent(limit=10)
        for mem in recent_memories:
            if mem.get('importance', 0) >= 7:
                if mem['content'][:100] not in recent_learnings:
                    recent_learnings.append(mem['content'][:100])

        return {
            'working_memory': len(self.working_memory),
            'long_term_memories': stats['total_memories'],
            'total_tokens': stats['total_tokens'],
            'memory_health': {
                'active': stats['hot_memories'],
                'fading': stats['warm_memories'],
                'old': stats['cold_memories'],
            },
            'cortex_mode': 'ai' if self.use_ai_cortex else 'lite',
            'recent_learnings': recent_learnings[:10],  # Limit to 10
        }

    def _passes_sensory_filter(self, text: str) -> bool:
        """Filter out noise (like sensory gating)"""
        # Too short
        if len(text.strip()) < 10:
            return False

        # Just whitespace or punctuation
        if not re.search(r'[a-zA-Z]{3,}', text):
            return False

        return True

    def _add_to_working_memory(self, thought: Thought):
        """Add to working memory with capacity limit using heapq for O(log n)"""
        if len(self.working_memory) < self.WORKING_MEMORY_LIMIT:
            # Room available - just push
            heapq.heappush(self.working_memory, thought)
        else:
            # At capacity - push and pop lowest importance (O(log n))
            removed = heapq.heappushpop(self.working_memory, thought)

            # If removed was important, encode to long-term
            if removed.importance >= 0.5:
                self._encode_to_long_term(removed.content, None, removed.importance)

    def _encode_to_long_term(self, content: str, understanding=None, importance: float = 0.5):
        """Encode to long-term memory"""
        from .smart import TextCompressor, SimilarityDetector

        # Compress before storing
        compressed = TextCompressor.compress(content)

        # Check for duplicates
        recent = self.memory.get_recent(limit=30)
        for mem in recent:
            if SimilarityDetector.are_similar(compressed, mem.get('content', '')):
                return None  # Skip duplicate

        # Determine type
        if understanding:
            mem_type = understanding.intent.value
        else:
            mem_type = 'observation'

        # Convert importance (0-1) to (1-10)
        importance_int = max(1, min(10, int(importance * 10)))

        return self.memory.save(compressed, type=mem_type, importance=importance_int)

    def _start_background(self):
        """Start background consolidation"""
        def consolidation_loop():
            while not self._stop_event.is_set():
                time.sleep(300)  # Every 5 minutes
                if not self._stop_event.is_set() and self.working_memory:
                    self.sleep()

        self._consolidation_thread = threading.Thread(target=consolidation_loop, daemon=True)
        self._consolidation_thread.start()

    def stop(self):
        """Stop brain (cleanup)"""
        self._stop_event.set()
        self.sleep()  # Final consolidation
        if self.cortex and hasattr(self.cortex, 'stop'):
            self.cortex.stop()


# === Convenience functions ===

_brain = None

def get_brain(use_ai: bool = False) -> Brain:
    """Get brain instance"""
    global _brain
    if _brain is None:
        _brain = Brain(use_ai_cortex=use_ai)
    return _brain


def perceive(text: str) -> Dict:
    """Process text through brain"""
    return get_brain().perceive(text)


def recall(query: str = None) -> str:
    """Recall relevant context"""
    return get_brain().recall(query)


def sleep() -> Dict:
    """Consolidate memories"""
    return get_brain().sleep()


# Aliases for more natural usage
think = perceive
remember = recall
dream = sleep
