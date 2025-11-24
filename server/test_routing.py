#!/usr/bin/env python3
"""
Quick test script to verify routing agent behavior with example queries.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.routing_agent import RoutingAgent
from openai import OpenAI


def test_routing():
    """Test routing agent with example queries."""

    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set. LLM fallback will not work.")
        print("   Testing with keyword-based routing only.\n")
        client = None
    else:
        client = OpenAI(api_key=api_key)

    # Initialize routing agent
    router = RoutingAgent(openai_client=client)

    # Test cases
    # Both LLM and rule-based routing return "qna" for Q&A queries (normalized from "q&a")
    test_cases = [
        # Should route to SCHEDULING (symptoms/health problems)
        ("I have a headache", "scheduling"),
        ("My back hurts", "scheduling"),
        ("I'm feeling sick", "scheduling"),
        ("I have chest pain", "scheduling"),
        ("I need to see a doctor", "scheduling"),
        ("Book an appointment", "scheduling"),
        ("I have fever and cough", "scheduling"),

        # Should route to Q&A (information queries)
        # Both LLM and rule-based return "qna"
        ("Can I take antibiotic with alcohol?", "qna"),
        ("What are the side effects of aspirin?", "qna"),
        ("What are your operating hours?", "qna"),
        ("How much does a visit cost?", "qna"),  # Currently fails due to "visit" keyword
        ("Can I mix ibuprofen and acetaminophen?", "qna"),
        ("What is the dosage for this medication?", "qna"),
        ("Do you accept my insurance?", "qna"),
    ]

    print("=" * 80)
    print("ROUTING AGENT TEST RESULTS")
    print("=" * 80)
    print()

    correct = 0
    total = len(test_cases)

    for query, expected_intent in test_cases:
        result = router.hybrid_decision(query)
        actual_intent = result.intent

        is_correct = actual_intent == expected_intent
        if is_correct:
            correct += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"

        print(f"{status} | Expected: {expected_intent:12} | Got: {actual_intent:15} | Confidence: {result.confidence:.2f}")
        print(f"       Query: \"{query}\"")
        print(f"       Rationale: {result.rationale}")
        print(f"       Source: {result.source}")
        print(f"       Counts: Scheduling={result.counts.get('scheduling', 0)}, Q&A={result.counts.get('qna', 0)}")
        print()

    print("=" * 80)
    print(f"RESULTS: {correct}/{total} correct ({100*correct/total:.1f}%)")
    print("=" * 80)

    if correct == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {total - correct} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(test_routing())
