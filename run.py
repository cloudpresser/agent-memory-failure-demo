#!/usr/bin/env python3
"""
Agent Memory Failure Demo
═════════════════════════

Runs two agents against the same debugging task and compares results.

Agent A (Summarizing): compresses context each step — loses details.
Agent B (Retrieval):   keeps raw trace log — retrieves on demand.

Usage:
    python run.py              # default: both agents
    python run.py --verbose    # show step-by-step progress
    python run.py --agent a    # run only the summarizing agent
    python run.py --agent b    # run only the retrieval agent
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent))

from agents import summarizing, retrieval
from agents.base import AgentResult


HEADER = """
════════════════════════════════════════════════════════════════
  Agent Memory Failure Demo
  Task: VIP Discount Bug Investigation
  Model: {model}
════════════════════════════════════════════════════════════════
"""

SEPARATOR = "────────────────────────────────────────────────────────────────"


def print_agent_result(result: AgentResult, verbose: bool = False) -> None:
    """Print an agent's result in a clean format."""
    print(f"\n▸ {result.agent_name}")
    print(f"  Steps: {len(result.steps)}")
    print(f"  Tokens used: {result.total_tokens:,}")

    # Show tool usage summary
    all_tools = []
    for step in result.steps:
        for tc in step.tool_calls:
            all_tools.append(tc["name"])
    if all_tools:
        print(f"  Tools called: {len(all_tools)} ({', '.join(set(all_tools))})")

    print()

    if verbose:
        print("  Step-by-step:")
        for step in result.steps:
            tools_desc = ", ".join(
                f"{tc['name']}({json.dumps(tc.get('arguments', {}))})"
                for tc in step.tool_calls
            )
            print(f"    Step {step.step_number}: {tools_desc or 'reasoning only'}")
        print()

    # Print conclusion
    print("  Conclusion:")
    for line in result.conclusion.splitlines():
        print(f"    {line}")
    print()


def assess_conclusion(conclusion: str) -> dict:
    """
    Simple heuristic assessment of whether the conclusion
    identifies the specific case-sensitivity root cause.
    """
    text = conclusion.lower()
    has_case_mention = any(
        term in text
        for term in ["case", "lowercase", "lower case", "tolowercase", "uppercas"]
    )
    has_exact_values = '"vip"' in text or "'vip'" in text
    has_normalize = "normalize" in text or "normalizestring" in text
    has_specific_flow = has_case_mention and (has_exact_values or has_normalize)
    has_vague = any(
        term in text
        for term in ["mismatch", "inconsisten", "not matching", "type issue"]
    )

    return {
        "mentions_case_sensitivity": has_case_mention,
        "mentions_exact_values": has_exact_values,
        "mentions_normalization": has_normalize,
        "specific_root_cause": has_specific_flow,
        "vague_conclusion": has_vague and not has_specific_flow,
    }


def print_comparison(result_a: AgentResult, result_b: AgentResult) -> None:
    """Print side-by-side comparison."""
    print(SEPARATOR)
    print("  Comparison")
    print(SEPARATOR)

    assess_a = assess_conclusion(result_a.conclusion)
    assess_b = assess_conclusion(result_b.conclusion)

    mark = lambda v: "yes" if v else "no"

    print()
    print(f"  {'Metric':<35} {'Summarizing':<15} {'Retrieval':<15}")
    print(f"  {'─' * 35} {'─' * 15} {'─' * 15}")
    print(f"  {'Steps taken':<35} {len(result_a.steps):<15} {len(result_b.steps):<15}")
    print(f"  {'Tokens used':<35} {result_a.total_tokens:<15,} {result_b.total_tokens:<15,}")
    print(f"  {'Mentions case sensitivity':<35} {mark(assess_a['mentions_case_sensitivity']):<15} {mark(assess_b['mentions_case_sensitivity']):<15}")
    print(f"  {'Mentions exact string values':<35} {mark(assess_a['mentions_exact_values']):<15} {mark(assess_b['mentions_exact_values']):<15}")
    print(f"  {'Mentions normalizeString':<35} {mark(assess_a['mentions_normalization']):<15} {mark(assess_b['mentions_normalization']):<15}")
    print(f"  {'Specific root cause identified':<35} {mark(assess_a['specific_root_cause']):<15} {mark(assess_b['specific_root_cause']):<15}")
    print(f"  {'Vague/general conclusion':<35} {mark(assess_a['vague_conclusion']):<15} {mark(assess_b['vague_conclusion']):<15}")
    print()

    if assess_a["specific_root_cause"] and assess_b["specific_root_cause"]:
        print("  Both agents identified the specific root cause.")
        print("  (Try running again — LLM outputs are non-deterministic.)")
    elif not assess_a["specific_root_cause"] and assess_b["specific_root_cause"]:
        print("  The summarizing agent lost critical detail during compression.")
        print("  The retrieval agent preserved raw evidence and identified the exact cause.")
    elif assess_a["specific_root_cause"] and not assess_b["specific_root_cause"]:
        print("  Unexpected: summarizing agent was more specific. Try running again.")
    else:
        print("  Neither agent fully identified the root cause. Try with a stronger model:")
        print("  MODEL=gpt-4o python run.py")
    print()


def save_results(
    result_a: AgentResult | None,
    result_b: AgentResult | None,
) -> str:
    """Save detailed results to a JSON file."""
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filepath = results_dir / f"run_{timestamp}.json"

    def serialize(r: AgentResult) -> dict:
        return {
            "agent_name": r.agent_name,
            "steps": len(r.steps),
            "total_tokens": r.total_tokens,
            "conclusion": r.conclusion,
            "tool_calls": [
                tc for step in r.steps for tc in step.tool_calls
            ],
        }

    data: dict = {
        "timestamp": timestamp,
        "model": os.environ.get("MODEL", "gpt-4o-mini"),
    }
    if result_a:
        data["summarizing_agent"] = serialize(result_a)
    if result_b:
        data["retrieval_agent"] = serialize(result_b)

    filepath.write_text(json.dumps(data, indent=2))
    return str(filepath)


def main():
    parser = argparse.ArgumentParser(
        description="Agent Memory Failure Demo — comparing summarization vs retrieval memory"
    )
    parser.add_argument(
        "--agent",
        choices=["a", "b", "both"],
        default="both",
        help="Which agent to run: a=summarizing, b=retrieval, both=compare (default: both)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed step-by-step output",
    )
    args = parser.parse_args()

    model = os.environ.get("MODEL", "gpt-4o-mini")
    print(HEADER.format(model=model))

    result_a = None
    result_b = None

    if args.agent in ("a", "both"):
        print(f"▸ Running Summarizing Agent...")
        t0 = time.time()
        result_a = summarizing.run(verbose=args.verbose)
        elapsed_a = time.time() - t0
        print_agent_result(result_a, verbose=args.verbose)
        print(f"  (completed in {elapsed_a:.1f}s)")

    if args.agent in ("b", "both"):
        print(f"\n▸ Running Retrieval Agent...")
        t0 = time.time()
        result_b = retrieval.run(verbose=args.verbose)
        elapsed_b = time.time() - t0
        print_agent_result(result_b, verbose=args.verbose)
        print(f"  (completed in {elapsed_b:.1f}s)")

    if result_a and result_b:
        print_comparison(result_a, result_b)

    # Save results
    filepath = save_results(result_a, result_b)
    print(f"  Detailed results saved to: {filepath}")
    print()


if __name__ == "__main__":
    main()
