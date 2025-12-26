#!/usr/bin/env python3
"""
Cortex - AI-Powered Background Brain

Like the human brain's background processes:
- Hippocampus: Memory consolidation during "sleep"
- Prefrontal Cortex: Decision making, planning
- Amygdala: Emotional significance tagging
- Default Mode Network: Background processing when idle

This runs as a background agent that:
1. Watches conversations
2. Extracts meaning using AI
3. Consolidates memories
4. Makes connections
5. Surfaces relevant context

Uses a small/fast AI model for background processing to save tokens.
"""

import subprocess
import threading
import queue
import time
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


class CortexMode(Enum):
    """Operating modes"""
    ACTIVE = "active"      # Real-time processing
    IDLE = "idle"          # Background consolidation
    SLEEP = "sleep"        # Deep consolidation (on session end)


@dataclass
class CortexThought:
    """A thought being processed by the cortex"""
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "conversation"  # conversation, reflection, insight
    processed: bool = False
    importance: float = 0.0
    connections: List[str] = field(default_factory=list)


class Cortex:
    """
    AI-Powered Background Brain

    Runs continuously, processing thoughts in the background
    like human unconscious processing.
    """

    # AI prompt for understanding/extraction
    UNDERSTANDING_PROMPT = """You are a memory system analyzing text. Be extremely concise.

Analyze this text and respond with ONLY a JSON object (no markdown, no explanation):
{
  "importance": 0.0-1.0,
  "type": "preference|decision|problem|solution|learning|fact|instruction|other",
  "summary": "one sentence max",
  "key_points": ["point1", "point2"],
  "should_remember": true/false,
  "connections": ["related topic1", "related topic2"]
}

Text to analyze:
"""

    CONSOLIDATION_PROMPT = """You are consolidating memories like a sleeping brain.

Given these recent memories, identify:
1. Patterns or themes
2. Connections between memories
3. What's truly important vs. noise
4. A consolidated summary

Be concise. Respond with JSON only:
{
  "patterns": ["pattern1"],
  "connections": [{"from": "topic1", "to": "topic2", "relation": "why"}],
  "important": ["memory summary 1"],
  "discard": ["not important"],
  "consolidated_summary": "one paragraph"
}

Memories:
"""

    REFLECTION_PROMPT = """Reflect on this conversation context and extract insights.

What should be remembered long-term? What's the user's intent?
What decisions were made? What problems were solved?

Respond with JSON only:
{
  "insights": ["insight1"],
  "user_preferences": ["pref1"],
  "decisions_made": ["decision1"],
  "problems_solved": ["problem1"],
  "open_questions": ["question1"]
}

Context:
"""

    def __init__(self, ai_command: str = "claude"):
        self.ai_command = ai_command
        self.mode = CortexMode.IDLE
        self.thought_queue: queue.Queue = queue.Queue()
        self.processed_thoughts: List[CortexThought] = []
        self.insights: List[Dict] = []

        # Background processing
        self._processing_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_consolidation = datetime.now()

        # Rate limiting for AI calls
        self._last_ai_call = datetime.now()
        self._min_ai_interval = timedelta(seconds=2)

        # Callbacks
        self.on_insight: Optional[Callable] = None
        self.on_memory_save: Optional[Callable] = None

    def start(self):
        """Start background processing"""
        if self._processing_thread and self._processing_thread.is_alive():
            return

        self._stop_event.clear()
        self._processing_thread = threading.Thread(target=self._background_loop, daemon=True)
        self._processing_thread.start()

    def stop(self):
        """Stop background processing"""
        self._stop_event.set()
        if self._processing_thread:
            self._processing_thread.join(timeout=5)
        # Final consolidation
        self._consolidate()

    def observe(self, text: str, source: str = "conversation"):
        """Observe new text (non-blocking)"""
        thought = CortexThought(content=text, source=source)
        self.thought_queue.put(thought)

    def think(self, text: str) -> Dict:
        """Process text immediately (blocking, for important input)"""
        return self._process_with_ai(text)

    def reflect(self) -> Dict:
        """Reflect on recent context and extract insights"""
        recent = self._get_recent_context()
        if not recent:
            return {}

        return self._call_ai(self.REFLECTION_PROMPT + recent)

    def consolidate(self) -> Dict:
        """Force memory consolidation (like sleep)"""
        return self._consolidate()

    def _background_loop(self):
        """Main background processing loop"""
        while not self._stop_event.is_set():
            try:
                # Process queued thoughts
                while not self.thought_queue.empty():
                    thought = self.thought_queue.get_nowait()
                    self._process_thought(thought)

                # Periodic consolidation (every 5 minutes of idle)
                if self._should_consolidate():
                    self._consolidate()

                # Sleep to prevent busy loop
                time.sleep(1)

            except Exception as e:
                # Don't crash the background thread
                print(f"Cortex background error: {e}")
                time.sleep(5)

    def _process_thought(self, thought: CortexThought):
        """Process a single thought"""
        # Quick heuristic check first (no AI needed for trivial content)
        if not self._worth_processing(thought.content):
            return

        # Use AI for deeper understanding
        result = self._process_with_ai(thought.content)

        if result.get('should_remember', False):
            thought.importance = result.get('importance', 0.5)
            thought.connections = result.get('connections', [])
            thought.processed = True
            self.processed_thoughts.append(thought)

            # Save to memory
            self._save_to_memory(thought, result)

            # Notify if callback set
            if self.on_memory_save:
                self.on_memory_save(thought, result)

    def _process_with_ai(self, text: str) -> Dict:
        """Use AI to understand text"""
        return self._call_ai(self.UNDERSTANDING_PROMPT + text)

    def _call_ai(self, prompt: str) -> Dict:
        """Call AI with rate limiting"""
        # Rate limiting
        now = datetime.now()
        elapsed = now - self._last_ai_call
        if elapsed < self._min_ai_interval:
            time.sleep((self._min_ai_interval - elapsed).total_seconds())

        self._last_ai_call = datetime.now()

        try:
            # Try using the AI CLI in non-interactive mode
            result = subprocess.run(
                [self.ai_command, '--print', '-p', prompt],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()
            )

            output = result.stdout.strip()

            # Parse JSON response
            # Find JSON in output (might have extra text)
            json_match = self._extract_json(output)
            if json_match:
                return json.loads(json_match)

            return {'raw': output}

        except subprocess.TimeoutExpired:
            return {'error': 'timeout'}
        except json.JSONDecodeError:
            return {'error': 'invalid_json', 'raw': output if 'output' in dir() else ''}
        except Exception as e:
            return {'error': str(e)}

    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from text that might have other content"""
        import re
        # Find JSON object pattern
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        return None

    def _worth_processing(self, text: str) -> bool:
        """Quick check if text is worth AI processing"""
        # Too short
        if len(text) < 20:
            return False

        # Too long (chunk it instead)
        if len(text) > 2000:
            return True  # Will process but chunk

        # Has indicators of importance
        importance_indicators = [
            'prefer', 'always', 'never', 'must', 'important',
            'remember', 'decided', 'error', 'fix', 'solution',
            'learned', 'discovered', 'should', 'need', 'want'
        ]

        text_lower = text.lower()
        return any(ind in text_lower for ind in importance_indicators)

    def _should_consolidate(self) -> bool:
        """Check if it's time for consolidation"""
        # Consolidate every 5 minutes if there are processed thoughts
        if not self.processed_thoughts:
            return False

        elapsed = datetime.now() - self._last_consolidation
        return elapsed > timedelta(minutes=5)

    def _consolidate(self) -> Dict:
        """Consolidate recent memories (like sleep consolidation)"""
        if not self.processed_thoughts:
            return {}

        # Get recent thoughts for consolidation
        thoughts_text = "\n".join([
            f"- [{t.source}] {t.content[:200]}"
            for t in self.processed_thoughts[-20:]  # Last 20
        ])

        result = self._call_ai(self.CONSOLIDATION_PROMPT + thoughts_text)

        if result.get('patterns') or result.get('important'):
            self.insights.append({
                'timestamp': datetime.now().isoformat(),
                'consolidation': result
            })

            # Save consolidated insights to long-term memory
            if result.get('consolidated_summary'):
                self._save_insight(result['consolidated_summary'])

        self._last_consolidation = datetime.now()
        return result

    def _save_to_memory(self, thought: CortexThought, analysis: Dict):
        """Save processed thought to memory"""
        from .memory import get_memory

        memory = get_memory()

        summary = analysis.get('summary', thought.content[:200])
        mem_type = analysis.get('type', 'observation')
        importance = int(analysis.get('importance', 0.5) * 10)

        memory.save(summary, type=mem_type, importance=importance)

    def _save_insight(self, insight: str):
        """Save a consolidated insight"""
        from .memory import get_memory

        memory = get_memory()
        memory.save(insight, type='insight', importance=8)

    def _get_recent_context(self) -> str:
        """Get recent context for reflection"""
        return "\n".join([
            t.content[:300] for t in self.processed_thoughts[-10:]
        ])

    def get_state(self) -> Dict:
        """Get cortex state"""
        return {
            'mode': self.mode.value,
            'queued_thoughts': self.thought_queue.qsize(),
            'processed_thoughts': len(self.processed_thoughts),
            'insights': len(self.insights),
            'last_consolidation': self._last_consolidation.isoformat(),
        }


class CortexLite:
    """
    Lightweight cortex that works WITHOUT calling external AI.
    Uses rule-based understanding for zero-latency, zero-cost processing.

    Use this when you don't want background AI calls.
    """

    def __init__(self):
        from .understanding import get_analyzer
        self.analyzer = get_analyzer()
        self.thoughts: List[CortexThought] = []

    def observe(self, text: str, source: str = "conversation"):
        """Observe and process text using rule-based understanding"""
        from .understanding import understand

        # Analyze semantically without AI
        understanding = understand(text)

        if understanding.is_memorable:
            thought = CortexThought(
                content=text,
                source=source,
                processed=True,
                importance=understanding.memory_score,
                connections=understanding.key_concepts
            )
            self.thoughts.append(thought)

            # Save to memory
            self._save(understanding)

        return {
            'intent': understanding.intent.value,
            'emphasis': understanding.emphasis.value,
            'memorable': understanding.is_memorable,
            'score': understanding.memory_score,
            'concepts': understanding.key_concepts,
        }

    def think(self, text: str) -> Dict:
        """Same as observe for lite version"""
        return self.observe(text)

    def _save(self, understanding):
        """Save to memory"""
        from .memory import get_memory

        memory = get_memory()
        importance = int(understanding.memory_score * 10)

        memory.save(
            understanding.summary,
            type=understanding.intent.value,
            importance=importance
        )


# Factory function
_cortex = None
_use_ai = False

def get_cortex(use_ai: bool = False) -> Cortex:
    """Get cortex instance (AI-powered or lite)"""
    global _cortex, _use_ai

    if _cortex is None or use_ai != _use_ai:
        if use_ai:
            _cortex = Cortex()
            _cortex.start()
        else:
            _cortex = CortexLite()
        _use_ai = use_ai

    return _cortex
