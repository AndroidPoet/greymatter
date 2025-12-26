#!/usr/bin/env python3
"""
Understanding Module - Semantic understanding beyond keywords

Human memory doesn't just match words - it understands:
- Intent (what the person means)
- Context (surrounding information)
- Emphasis (how strongly something is stated)
- Relationships (how things connect)
- Patterns (recurring themes)
- Emotion (positive/negative sentiment)

This module provides semantic understanding WITHOUT external dependencies.
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class Intent(Enum):
    """What is the speaker trying to do?"""
    INFORM = "inform"           # Sharing information
    REQUEST = "request"         # Asking for something
    PREFERENCE = "preference"   # Expressing preference
    DECISION = "decision"       # Making a choice
    PROBLEM = "problem"         # Describing an issue
    SOLUTION = "solution"       # Providing a fix
    LEARNING = "learning"       # Sharing knowledge gained
    INSTRUCTION = "instruction" # Giving directions
    QUESTION = "question"       # Asking something
    EMOTION = "emotion"         # Expressing feeling
    UNKNOWN = "unknown"


class Emphasis(Enum):
    """How strongly is something stated?"""
    VERY_STRONG = 5   # "ALWAYS", "NEVER", "MUST"
    STRONG = 4        # "definitely", "certainly"
    MODERATE = 3      # "should", "prefer"
    WEAK = 2          # "maybe", "might"
    VERY_WEAK = 1     # "just", "only"


@dataclass
class Understanding:
    """Result of understanding analysis"""
    intent: Intent
    emphasis: Emphasis
    sentiment: float  # -1 to 1
    key_concepts: List[str]
    relationships: List[Tuple[str, str, str]]  # (subject, relation, object)
    is_memorable: bool
    memory_score: float  # 0 to 1
    summary: str


class SemanticAnalyzer:
    """
    Analyze text for meaning, not just keywords.
    Uses linguistic patterns and heuristics.
    """

    # Intent detection patterns (more flexible than exact words)
    INTENT_PATTERNS = {
        Intent.PREFERENCE: [
            r"(?:i|we|user)?\s*(?:prefer|like|love|enjoy|want|favor)",
            r"(?:better|best|favorite|ideal)\s+(?:to|for|is|would be)",
            r"(?:rather|instead)\s+(?:have|use|do)",
            r"(?:my|our)\s+(?:choice|preference|favorite)",
            r"(?:should|would)\s+(?:use|go with|pick|choose)",
        ],
        Intent.DECISION: [
            r"(?:i|we)\s*(?:decided|chose|selected|picked|went with)",
            r"(?:let's|going to|will)\s+(?:use|go with|do|implement)",
            r"(?:the|our)\s+(?:decision|choice)\s+(?:is|was)",
            r"(?:settled on|opted for|committed to)",
        ],
        Intent.PROBLEM: [
            r"(?:error|bug|issue|problem|broken|failing|crashed)",
            r"(?:doesn't|does not|isn't|won't|can't)\s+(?:work|run|compile|load)",
            r"(?:something|it)\s+(?:is|went)\s+wrong",
            r"(?:stuck|blocked|confused)\s+(?:on|with|by)",
            r"(?:help|fix|debug|solve)",
        ],
        Intent.SOLUTION: [
            r"(?:fixed|solved|resolved|working now)",
            r"(?:the|a)\s+(?:solution|fix|answer)\s+(?:is|was)",
            r"(?:this|that)\s+(?:fixes|solves|resolves)",
            r"(?:it works|problem solved|issue resolved)",
            r"(?:found|discovered)\s+(?:the|a)\s+(?:fix|solution|way)",
        ],
        Intent.LEARNING: [
            r"(?:learned|discovered|realized|understood|figured out)",
            r"(?:now|finally)\s+(?:know|understand|get)",
            r"(?:the|a)\s+(?:key|important)\s+(?:thing|insight|lesson)",
            r"(?:turns out|apparently|it seems)",
            r"(?:TIL|today i learned|good to know)",
        ],
        Intent.INSTRUCTION: [
            r"(?:always|never|make sure|ensure|remember to)",
            r"(?:you should|you must|you need to|don't forget)",
            r"(?:the way to|how to|steps to)",
            r"(?:first|then|next|finally|after that)",
            r"(?:do|don't|avoid|use|try)",
        ],
        Intent.QUESTION: [
            r"\?$",
            r"(?:what|why|how|when|where|who|which)\s+",
            r"(?:do you|can you|could you|would you)",
            r"(?:is it|are there|does it|will it)",
        ],
    }

    # Emphasis patterns
    EMPHASIS_PATTERNS = {
        Emphasis.VERY_STRONG: [
            r"\b(?:ALWAYS|NEVER|MUST|ABSOLUTELY|DEFINITELY|CRITICAL|ESSENTIAL)\b",
            r"\b(?:always|never|must|absolutely|definitely|critical|essential)\b",
            r"!{2,}",  # Multiple exclamation marks
            r"\b(?:DO NOT|DON'T EVER|MAKE SURE)\b",
        ],
        Emphasis.STRONG: [
            r"\b(?:very|really|highly|strongly|certainly|surely)\b",
            r"\b(?:important|significant|crucial|vital)\b",
            r"!$",  # Single exclamation
        ],
        Emphasis.MODERATE: [
            r"\b(?:should|prefer|recommend|suggest|better)\b",
            r"\b(?:usually|typically|generally|often)\b",
        ],
        Emphasis.WEAK: [
            r"\b(?:maybe|perhaps|might|could|possibly)\b",
            r"\b(?:sometimes|occasionally|rarely)\b",
        ],
        Emphasis.VERY_WEAK: [
            r"\b(?:just|only|simply|merely|kinda|sorta)\b",
            r"\b(?:i guess|i think|not sure|probably)\b",
        ],
    }

    # Sentiment indicators
    POSITIVE_PATTERNS = [
        r"\b(?:good|great|excellent|perfect|awesome|love|like|works|success|solved|fixed)\b",
        r"\b(?:happy|glad|excited|pleased|satisfied)\b",
        r"\b(?:thanks|thank you|appreciate)\b",
        r":[\)\]D]|👍|✅|🎉",
    ]

    NEGATIVE_PATTERNS = [
        r"\b(?:bad|terrible|awful|hate|broken|error|bug|fail|wrong|issue|problem)\b",
        r"\b(?:frustrated|annoyed|confused|stuck|blocked)\b",
        r"\b(?:doesn't work|can't|won't|unable)\b",
        r":[\(\[]|👎|❌|😢",
    ]

    # Concept extraction patterns
    CONCEPT_PATTERNS = [
        # Technical terms (CamelCase, snake_case, etc.)
        r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b",  # CamelCase
        r"\b([a-z]+_[a-z_]+)\b",                # snake_case
        r"\b([a-z]+-[a-z-]+)\b",                # kebab-case

        # Quoted terms
        r'"([^"]+)"',
        r"'([^']+)'",
        r"`([^`]+)`",

        # Technical keywords
        r"\b(API|SDK|CLI|GUI|REST|GraphQL|SQL|NoSQL)\b",
        r"\b(React|Vue|Angular|Node|Python|TypeScript|JavaScript)\b",
        r"\b(Docker|Kubernetes|AWS|GCP|Azure)\b",
    ]

    # Relationship patterns (subject, relation, object)
    RELATIONSHIP_PATTERNS = [
        (r"(\w+)\s+(?:is|are)\s+(?:a|an)\s+(\w+)", "is_a"),
        (r"(\w+)\s+(?:uses?|requires?)\s+(\w+)", "uses"),
        (r"(\w+)\s+(?:depends? on|needs?)\s+(\w+)", "depends_on"),
        (r"(\w+)\s+(?:contains?|has|have)\s+(\w+)", "contains"),
        (r"(\w+)\s+(?:connects? to|calls?)\s+(\w+)", "connects_to"),
        (r"(\w+)\s+(?:should|must)\s+(\w+)", "should"),
    ]

    def analyze(self, text: str) -> Understanding:
        """Perform full semantic analysis"""
        intent = self._detect_intent(text)
        emphasis = self._detect_emphasis(text)
        sentiment = self._analyze_sentiment(text)
        concepts = self._extract_concepts(text)
        relationships = self._extract_relationships(text)

        # Calculate memory score based on all factors
        memory_score = self._calculate_memory_score(
            intent, emphasis, sentiment, concepts, relationships, text
        )

        # Generate summary
        summary = self._generate_summary(text, concepts)

        return Understanding(
            intent=intent,
            emphasis=emphasis,
            sentiment=sentiment,
            key_concepts=concepts,
            relationships=relationships,
            is_memorable=memory_score >= 0.5,
            memory_score=memory_score,
            summary=summary
        )

    def _detect_intent(self, text: str) -> Intent:
        """Detect the intent behind the text"""
        text_lower = text.lower()

        intent_scores = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower))
                score += matches
            intent_scores[intent] = score

        # Get highest scoring intent
        if max(intent_scores.values()) > 0:
            return max(intent_scores, key=intent_scores.get)

        return Intent.INFORM  # Default to inform

    def _detect_emphasis(self, text: str) -> Emphasis:
        """Detect how strongly something is stated"""
        for emphasis, patterns in self.EMPHASIS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return emphasis

        return Emphasis.MODERATE  # Default

    def _analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment (-1 to 1)"""
        text_lower = text.lower()

        positive = sum(
            len(re.findall(p, text_lower))
            for p in self.POSITIVE_PATTERNS
        )
        negative = sum(
            len(re.findall(p, text_lower))
            for p in self.NEGATIVE_PATTERNS
        )

        total = positive + negative
        if total == 0:
            return 0.0

        return (positive - negative) / total

    def _extract_concepts(self, text: str) -> List[str]:
        """Extract key concepts from text"""
        concepts = set()

        for pattern in self.CONCEPT_PATTERNS:
            matches = re.findall(pattern, text)
            concepts.update(matches)

        # Also extract significant nouns (capitalized words not at start)
        words = text.split()
        for i, word in enumerate(words):
            if i > 0 and word[0].isupper() and word.isalpha():
                concepts.add(word)

        return list(concepts)[:10]  # Limit

    def _extract_relationships(self, text: str) -> List[Tuple[str, str, str]]:
        """Extract relationships between entities"""
        relationships = []
        text_lower = text.lower()

        for pattern, relation_type in self.RELATIONSHIP_PATTERNS:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    relationships.append((match[0], relation_type, match[1]))

        return relationships[:5]  # Limit

    def _calculate_memory_score(self, intent: Intent, emphasis: Emphasis,
                                sentiment: float, concepts: List[str],
                                relationships: List, text: str) -> float:
        """Calculate how memorable this text is"""
        score = 0.0

        # Intent contribution (0-0.4) - MORE AGGRESSIVE
        memorable_intents = {
            Intent.PREFERENCE: 0.4,
            Intent.DECISION: 0.4,
            Intent.SOLUTION: 0.4,
            Intent.LEARNING: 0.4,
            Intent.PROBLEM: 0.35,
            Intent.INSTRUCTION: 0.35,
            Intent.INFORM: 0.15,
            Intent.QUESTION: 0.1,
            Intent.EMOTION: 0.15,
        }
        score += memorable_intents.get(intent, 0.15)

        # Emphasis contribution (0-0.25)
        emphasis_scores = {
            Emphasis.VERY_STRONG: 0.25,
            Emphasis.STRONG: 0.2,
            Emphasis.MODERATE: 0.1,
            Emphasis.WEAK: 0.05,
            Emphasis.VERY_WEAK: 0.0,
        }
        score += emphasis_scores.get(emphasis, 0.1)

        # Sentiment contribution (0-0.1) - strong emotions are memorable
        score += abs(sentiment) * 0.1

        # Concepts contribution (0-0.2)
        concept_score = min(len(concepts) / 5, 1.0) * 0.2
        score += concept_score

        # Relationships contribution (0-0.15)
        relationship_score = min(len(relationships) / 3, 1.0) * 0.15
        score += relationship_score

        # Length penalty (very short or very long)
        word_count = len(text.split())
        if word_count < 5:
            score *= 0.5
        elif word_count > 500:
            score *= 0.7

        return min(1.0, score)

    def _generate_summary(self, text: str, concepts: List[str]) -> str:
        """Generate a brief summary"""
        # Take first sentence or first 100 chars
        first_sentence = re.split(r'[.!?]', text)[0]
        summary = first_sentence[:100]

        if concepts:
            summary += f" [Topics: {', '.join(concepts[:3])}]"

        return summary


class PatternLearner:
    """
    Learn what's important over time (like human memory consolidation).
    Tracks what gets referenced again and strengthens those patterns.
    """

    def __init__(self):
        self.concept_frequency: Dict[str, int] = {}
        self.intent_importance: Dict[Intent, float] = {}
        self.recalled_memories: List[int] = []

    def record_concept(self, concept: str):
        """Record that a concept was mentioned"""
        self.concept_frequency[concept] = self.concept_frequency.get(concept, 0) + 1

    def record_recall(self, memory_id: int):
        """Record that a memory was recalled (strengthens it)"""
        self.recalled_memories.append(memory_id)

    def get_concept_importance(self, concept: str) -> float:
        """Get learned importance of a concept"""
        freq = self.concept_frequency.get(concept, 0)
        # Log scale importance
        if freq == 0:
            return 0.0
        return min(1.0, 0.1 + 0.1 * (freq ** 0.5))

    def get_frequently_recalled(self) -> List[int]:
        """Get IDs of frequently recalled memories"""
        from collections import Counter
        counts = Counter(self.recalled_memories)
        return [id for id, count in counts.most_common(20) if count >= 2]


# Singleton analyzer
_analyzer = None

def get_analyzer() -> SemanticAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SemanticAnalyzer()
    return _analyzer


def understand(text: str) -> Understanding:
    """Analyze text for semantic understanding"""
    return get_analyzer().analyze(text)
