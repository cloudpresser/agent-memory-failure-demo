"""
Agent A: Summarizing Agent

Memory strategy: compress-then-reason.
After reading each file, the conversation is summarized by a separate
LLM call and previous context is discarded. The agent builds its
understanding from compressed summaries only.

This simulates how many production agents manage long contexts —
compressing state to save tokens. The failure mode is systematic:
low-salience details (like exact string values) are dropped during
summarization, even when they're critical to the solution.
"""

from agents.base import (
    get_client,
    get_model,
    TASK_PROMPT,
    AgentStep,
    AgentResult,
)
from agents.tools import read_file, read_logs, read_test_results

# Fixed investigation order — both agents read the same files in the same order.
# This eliminates planning variance and isolates memory as the only variable.
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


def _summarize(client, model: str, running_summary: str, new_content: str) -> str:
    """
    Compress the running summary + new file content into an updated summary.
    This is where information loss happens — the summarizer captures the
    gist but drops exact values, line numbers, and precise strings.
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a summarization assistant helping a debugger track "
                    "their investigation. Update the running summary with the new "
                    "findings from the file just read. Be concise — keep the total "
                    "summary to 3-5 sentences. Focus on what was found and what "
                    "it means for the investigation, not on raw data."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"CURRENT SUMMARY:\n{running_summary or '(Starting investigation)'}\n\n"
                    f"NEW FILE CONTENT:\n{new_content}"
                ),
            },
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content


def run(verbose: bool = False) -> AgentResult:
    """
    Run the summarizing agent.

    For each file in the investigation sequence:
      1. Read the file
      2. Summarize: compress running_summary + file content → new summary
      3. Discard the raw file content
    After all files are read, ask the agent to conclude from the summary.
    """
    client = get_client()
    model = get_model()
    result = AgentResult(agent_name="Summarizing Agent")
    running_summary = ""

    # Phase 1: Read all files, summarizing after each one
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

        if verbose:
            print(f"  Step {step_num}: read {filename}")

        # ── THE KEY MECHANISM: Summarize and discard ──
        # The raw file content is compressed into the running summary.
        # Exact string values, line numbers, and code details are lost.
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a summarization assistant helping a debugger track "
                        "their investigation. Update the running summary with the new "
                        "findings from the file just read. Be concise — keep the total "
                        "summary to 3-5 sentences. Focus on what was found and what "
                        "it means for the investigation, not on raw data."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"CURRENT SUMMARY:\n{running_summary or '(Starting investigation)'}\n\n"
                        f"NEW FILE JUST READ ({filename}):\n{content}"
                    ),
                },
            ],
            temperature=0.0,
        )
        result.total_tokens += response.usage.total_tokens if response.usage else 0
        running_summary = response.choices[0].message.content
        step.reasoning = f"Summary after reading {filename}: {running_summary}"

        result.steps.append(step)

        if verbose:
            print(f"    Summary: {running_summary[:100]}...")

    # Phase 2: Conclude from the summary alone
    if verbose:
        print(f"\n  Concluding from summary ({len(running_summary)} chars)...")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": TASK_PROMPT},
            {
                "role": "user",
                "content": (
                    f"You have read all the files in the codebase. Here is your "
                    f"investigation summary:\n\n{running_summary}\n\n"
                    f"State your final CONCLUSION. Include:\n"
                    f"- The specific root cause\n"
                    f"- The exact data flow for user u003 buying a $150 item "
                    f"(every function call and exact string value)\n"
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

    if verbose:
        print(f"  Done.\n")

    return result
