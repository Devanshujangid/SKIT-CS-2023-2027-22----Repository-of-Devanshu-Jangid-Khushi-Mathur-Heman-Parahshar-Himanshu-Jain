"""
Deterministic Academic Scope & Guardrail Service for Module 2 AI Academic Assistant.

Enforces strict academic boundaries by:
1. Detecting non-academic query domains (e.g., recipes/cooking, entertainment/movies, sports trivia, celebrity gossip, personal chit-chat).
2. Protecting specialized academic terminology containing common words (e.g., Lamport's Bakery Algorithm, Dining Philosophers, Pancake Sorting).
3. Cross-referencing queries against enrolled subjects, engineering terminology, and student study telemetry.
4. Generating structured refusal responses that politely decline non-academic queries and redirect the student to their syllabus and weak topics.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Set, Tuple


# ===========================================================================
# 1. Non-Academic Domain Keyword Patterns (High Precision)
# ===========================================================================

# High-precision non-academic keywords/phrases
NON_ACADEMIC_DOMAIN_PATTERNS = [
    # Cooking / Food Recipes
    r"\b(recipe|bake|baking|cook|cooking|ingredients|flavor|tasty|delicious|dessert|kitchen|oven)\b",
    r"\b(cake|cookies|pancake|pasta|pizza|soup|stew|salad|cocktail|sandwich|curry|sauce|pastry|pie|brownies|cupcake|lasagna)\b",
    # Entertainment / Media / Pop Culture
    r"\b(movie|cinema|actor|actress|box office|netflix|hollywood|bollywood|tv show|season finale)\b",
    r"\b(pop song|rap song|lyrics|music video|album|chords|guitar tab|celebrity|gossip|dating|romantic advice|love poem)\b",
    # Sports & Games (Non-algorithmic)
    r"\b(sports?|sporting|cricket match|football score|premier league|fifa world cup|nba playoffs|ipl score|champions league|tennis match|world cup final|olympics|scorecard)\b",
    # Lifestyle, Commerce, & Automotive/DIY
    r"\b(horoscope|astrology|zodiac|buy a car|used car|real estate|mortgage rate|fashion|makeup|skincare)\b",
    r"\b(change the oil|oil change|fix my car|car engine repair|car maintenance)\b",
    # Creative / Informal non-study
    r"\b(love letter|flirt|joke of the day|riddle me this|bedtime story|fairy tale)\b",
]

# Legitimate Academic Keywords that specifically overlap with food, entertainment, or everyday terms
# (e.g. "Bakery algorithm", "Dining philosophers", "Cookie/Session management", "Pancake sorting", "Fork/Pipe")
ACADEMIC_EXEMPTION_PATTERNS = [
    r"\bbakery algorithm\b",
    r"\blamport('?s)? bakery\b",
    r"\bdining philosophers?\b",
    r"\bpancake sort(ing)?\b",
    r"\bspaghetti code\b",
    r"\bhttp cookies?\b",
    r"\bsession (cookie|management|token)\b",
    r"\b(browser cookie|tracking cookie)\b",
    r"\bdining cryptographers\b",
    r"\bsleeping barber\b",
    r"\bcigarette smokers?\b",
    r"\bsanta claus problem\b",
    r"\b(sandwich theorem|squeeze theorem)\b",
    r"\b(fork-exec|fork system call|forkbomb)\b",
]

# Academic intent and syllabus indicators (evaluated after non-academic domain checks)
ACADEMIC_INTENT_PATTERNS = [
    r"\b(explain|understand|prove|derive|analyze|solve|implement|trace|compare)\b",
    r"\b(study|revision|review|schedule|priority|today|tomorrow|hours|deadline)\b",
    r"\b(quiz|test|mcq|practice|formula|theorem|definition|pseudocode)\b",
    r"\b(gate|mid-term|end-term|semester|cgpa|syllabus|curriculum|assignment)\b",
    r"\b(algorithm|data structure|complexity|big o|graph|dynamic programming)\b",
    r"\b(semaphore|mutex|spinlock|deadlock|starvation|paging|thrashing)\b",
    r"\b(tcp|udp|ip|dns|dhcp|bgp|ospf|subnet|socket)\b",
    r"\b(sql|acid|normalization|relational|btree|hash index|transaction)\b",
]


@dataclass
class GuardrailCheckResult:
    """
    Structured outcome of an academic guardrail evaluation.
    """
    is_academic: bool
    query: str
    detected_category: str
    matched_patterns: List[str] = field(default_factory=list)
    refusal_reason: Optional[str] = None
    refusal_message: Optional[str] = None
    suggested_academic_topics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_academic": self.is_academic,
            "query": self.query,
            "detected_category": self.detected_category,
            "matched_patterns": self.matched_patterns,
            "refusal_reason": self.refusal_reason,
            "refusal_message": self.refusal_message,
            "suggested_academic_topics": self.suggested_academic_topics,
        }


def check_academic_scope(
    query: str,
    enrolled_subjects: Optional[List[str]] = None,
    active_weak_topics: Optional[List[str]] = None,
) -> GuardrailCheckResult:
    """
    Evaluates whether a student query is within academic syllabus scope
    or should be refused as a non-academic query (e.g. recipe, entertainment, sports).

    Evaluation Pipeline:
    1. Empty / whitespace query check.
    2. Academic Exemption check (e.g. Lamport's Bakery Algorithm, Dining Philosophers).
       Takes top priority to protect specialized CS terminology overlapping with food/common items.
    3. Non-Academic Domain pattern check (recipes, cinema, sports, lifestyle, creative writing).
       Triggers refusal even if a student prefixes the query with an enrolled subject (anti-jailbreak).
    4. Enrolled Subject cross-reference check.
    5. Active Weak Topic cross-reference check.
    6. General academic and syllabus intent heuristic.

    Args:
        query: User input prompt string.
        enrolled_subjects: Optional list of student's enrolled courses.
        active_weak_topics: Optional list of active weak topics.

    Returns:
        GuardrailCheckResult indicating pass/refusal with structured reasoning.
    """
    clean_query = query.strip()
    lower_query = clean_query.lower()

    if not clean_query:
        return GuardrailCheckResult(
            is_academic=False,
            query=clean_query,
            detected_category="empty_query",
            refusal_reason="empty_query",
            refusal_message="Please enter an academic question or study topic.",
            suggested_academic_topics=enrolled_subjects or ["Operating Systems", "Computer Networks"],
        )

    # 1. Check for Academic Exemption Patterns (e.g. "Bakery algorithm", "Dining philosophers", "HTTP cookies")
    # This prevents false positives when legitimate CS topics contain culinary or everyday metaphors.
    matched_exemptions = []
    for pattern in ACADEMIC_EXEMPTION_PATTERNS:
        if re.search(pattern, lower_query):
            matched_exemptions.append(pattern)

    if matched_exemptions:
        return GuardrailCheckResult(
            is_academic=True,
            query=clean_query,
            detected_category="academic_computer_science",
            matched_patterns=matched_exemptions,
        )

    # 2. Check for Non-Academic Domain Keywords (e.g. recipes, cinema, sports, gossip)
    # Prioritized over enrolled subjects to prevent prefix jailbreaks like:
    # "For Operating Systems, write me a recipe for chocolate cake"
    matched_non_academic = []
    for pattern in NON_ACADEMIC_DOMAIN_PATTERNS:
        match = re.search(pattern, lower_query)
        if match:
            matched_non_academic.append(match.group(0))

    if matched_non_academic:
        # Construct helpful academic redirect suggestions
        suggestions = []
        if active_weak_topics:
            suggestions.extend([f"Review {t}" for t in active_weak_topics[:2]])
        if enrolled_subjects:
            suggestions.extend([f"Practice {s}" for s in enrolled_subjects[:2]])
        if not suggestions:
            suggestions = [
                "Explain Peterson's Algorithm",
                "What is my study priority today?",
                "Generate a quiz on Operating Systems"
            ]

        subjects_mention = ""
        if enrolled_subjects:
            subj_list_str = ", ".join(enrolled_subjects[:3])
            subjects_mention = f" ({subj_list_str})"

        refusal_message = (
            f"I am your dedicated AI Academic Assistant, focused strictly on your engineering coursework, "
            f"enrolled subjects{subjects_mention}, and study timetable. "
            f"I cannot assist with non-academic requests such as recipes, entertainment, or general trivia. "
            f"Let's get back to your studies! Would you like help with one of your active courses or weak topics instead?"
        )

        return GuardrailCheckResult(
            is_academic=False,
            query=clean_query,
            detected_category="non_academic_refusal",
            matched_patterns=matched_non_academic,
            refusal_reason="non_academic_domain",
            refusal_message=refusal_message,
            suggested_academic_topics=suggestions[:3],
        )

    # 3. Check for Enrolled Subject Matches
    if enrolled_subjects:
        for subj in enrolled_subjects:
            if subj.lower() in lower_query:
                return GuardrailCheckResult(
                    is_academic=True,
                    query=clean_query,
                    detected_category="enrolled_subject_match",
                    matched_patterns=[subj],
                )

    # 4. Check for Active Weak Topic Matches
    if active_weak_topics:
        for wt in active_weak_topics:
            if wt.lower() in lower_query:
                return GuardrailCheckResult(
                    is_academic=True,
                    query=clean_query,
                    detected_category="weak_topic_match",
                    matched_patterns=[wt],
                )

    # 5. Check for Academic Intent Indicators
    has_academic_intent = any(re.search(p, lower_query) for p in ACADEMIC_INTENT_PATTERNS)

    if has_academic_intent or len(clean_query.split()) >= 2:
        return GuardrailCheckResult(
            is_academic=True,
            query=clean_query,
            detected_category="general_academic_query",
        )

    # Fallback refusal for completely ambiguous single-word non-academic slang
    return GuardrailCheckResult(
        is_academic=False,
        query=clean_query,
        detected_category="out_of_scope_query",
        refusal_reason="ambiguous_non_academic",
        refusal_message="I'm here to help you study and prepare for your exams. Please ask a question related to your syllabus or study plan.",
        suggested_academic_topics=enrolled_subjects or ["Operating Systems", "Computer Networks"],
    )
