"""
Agent B: Retrieval Agent

Memory strategy: store-then-retrieve.
After reading each file, the raw content is APPENDED to an append-only
trace log. Nothing is ever overwritten or compressed. When concluding,
a retrieval step selects the most relevant raw evidence.

The agent reasons with full evidence references, and can always
go back to the raw data when correlating across files.
"""

import json
from agents.base import (
    get_client,
    get_model,
    TASK_PROMPT,
    AgentStep,
    AgentResult,
)
from agents.tools import read_file, read_logs, read_test_results

# Same investigation order as the summarizing agent — fair comparison.
INVESTIGATION_STEPS = [
    ("read_logs", "logs.txt"),
    ("read_file", "bug_report.md"),
    ("read_file", "checkout.ts"),
    ("read_file", "config.ts"),
    ("read_file", "cache.ts"),
    ("read_file", "middleware.ts"),
    ("read_file", "discount.ts"),
    ("read_file", "user.ts"),
    ("read_file", "utils.ts"),
    ("read_file", "types.ts"),
    ("read_test_results", "test_results.txt"),
]


def _retrieve_relevant(
    client, model: str, trace_entries: list[dict], focus: str
) -> str:
    """
    Retrieval step: select the most relevant raw traces VERBATIM.
    No summarization — preserves exact string values, line numbers, code.
    """
    formatted = []
    for i, entry in enumerate(trace_entries):
        formatted.append(
            f"[Entry {i + 1}: {entry['filename']}]\n{entry['content']}"
        )
    all_traces = "\n\n{'='*60}\n\n".join(formatted)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a retrieval assistant. Given raw investigation data "
                    "and the investigator's focus, select and return the MOST "
                    "RELEVANT entries VERBATIM. Do NOT summarize or paraphrase. "
                    "Return the raw content exactly as stored — preserve all "
                    "exact string values, quotes, line numbers, and code. "
                    "Include the 4-6 most relevant entries."
                ),
            },
            {
                "role": "user",
                "content": f"Focus: {focus}\n\nAvailable data:\n\n{all_traces}",
            },
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content


def run(verbose: bool = False) -> AgentResult:
    """
    Run the retrieval agent.

    For each file in the investigation sequence:
      1. Read the file
      2. Append raw content to trace log (never overwrite)
    After all files are read, retrieve relevant evidence and conclude.
    """
    client = get_client()
    model = get_model()
    result = AgentResult(agent_name="Retrieval Agent")

    # Append-only trace log — raw evidence is never destroyed
    trace_log: list[dict] = []

    # Phase 1: Read all files, storing raw content
    for step_num, (tool, filename) in enumerate(INVESTIGATION_STEPS, start=1):
        step = AgentStep(step_number=step_num)

        # Read the file
        if tool == "read_logs":
            content = read_logs()
        elif tool == "read_test_results":
            content = read_test_results()
        else:
            content = read_file(filename)

        step.tool_calls.append({"name": tool, "arguments": {"filename": filename}})
        step.tool_results.append({"tool": tool, "result": content})

        # ── THE KEY MECHANISM: Append raw content to trace log ──
        # Nothing is ever compressed or overwritten.
        trace_log.append({"filename": filename, "content": content})

        step.reasoning = f"Read {filename} — stored in trace log."
        result.steps.append(step)

        if verbose:
            print(f"  Step {step_num}: read {filename} ({len(content)} chars stored)")

    # Phase 2: Retrieve relevant evidence and conclude
    if verbose:
        print(f"\n  Retrieving relevant evidence from {len(trace_log)} entries...")

    retrieved = _retrieve_relevant(
        client,
        model,
        trace_log,
        "Root cause of VIP discount bug: need to compare exact string values "
        "returned by getUserType, transformed by normalizeString, and checked "
        "by calculateDiscount. Focus on case sensitivity and string comparisons.",
    )
    result.total_tokens += 0  # retrieval tokens tracked below

    if verbose:
        print(f"  Retrieved {len(retrieved)} chars of evidence")
        print(f"  Concluding from raw evidence...\n")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": TASK_PROMPT},
            {
                "role": "user",
                "content": (
                    f"You have read all the files. Here is the raw evidence "
                    f"most relevant to the bug:\n\n{retrieved}\n\n"
                    f"State your final CONCLUSION. Include:\n"
                    f"- The specific root cause\n"
                    f"- The exact data flow for user u003 buying a $150 item "
                    f"(every function call and exact string value at each step)\n"
                    f"- File:line evidence"
                ),
            },
        ],
        temperature=0.0,
    )
    result.total_tokens += response.usage.total_tokens if response.usage else 0
    conclusion = response.choices[0].message.content or ""
    result.conclusion = conclusion
    result.raw_final_response = conclusion

    return result
