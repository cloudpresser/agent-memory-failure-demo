"""
Agent B: Retrieval Agent

Memory strategy: store-then-retrieve.
After each investigation step, raw tool outputs and reasoning are
APPENDED to an append-only trace log. Nothing is ever overwritten.
Before each step, a retrieval call selects the most relevant trace
entries for the current question.

The agent reasons with full evidence references, and can always
go back to the raw data when correlating across files.
"""

import json
from agents.base import (
    get_client,
    get_model,
    TOOL_SCHEMAS,
    TASK_PROMPT,
    AgentStep,
    AgentResult,
    parse_tool_calls,
)
from agents.tools import execute_tool

MAX_STEPS = 6


def _retrieve_relevant(
    client, model: str, trace_entries: list[dict], current_question: str
) -> str:
    """
    Retrieval step: given the full trace log and the current focus,
    select and return the most relevant entries.
    This keeps context manageable without destroying evidence.
    """
    if not trace_entries:
        return "No previous investigation data."

    # Format trace entries for the retriever
    formatted = []
    for entry in trace_entries:
        formatted.append(
            f"[Step {entry['step']}, Tool: {entry['tool']}]\n{entry['result']}"
        )
    all_traces = "\n\n---\n\n".join(formatted)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a retrieval assistant. Given a collection of investigation "
                    "traces (tool outputs from previous steps) and the investigator's "
                    "current focus, select and return the MOST RELEVANT traces verbatim. "
                    "Do not summarize — return the raw content exactly as stored. "
                    "Include 2-4 of the most relevant entries. If the investigator needs "
                    "to compare specific string values across files, include ALL entries "
                    "that contain those values."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Current focus: {current_question}\n\n"
                    f"Available traces:\n\n{all_traces}"
                ),
            },
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content


def run(verbose: bool = False) -> AgentResult:
    """
    Run the retrieval agent.

    Loop:
      1. System prompt includes retrieved relevant trace entries
      2. Agent reasons and calls tools
      3. Raw tool outputs are APPENDED to trace log (never overwritten)
      4. Before next step, retrieval selects relevant entries
      5. Agent reasons with evidence references
    """
    client = get_client()
    model = get_model()
    result = AgentResult(agent_name="Retrieval Agent")

    # Append-only trace log — raw evidence is never destroyed
    trace_log: list[dict] = []

    # Retrieved context for current step
    retrieved_context = ""

    for step_num in range(1, MAX_STEPS + 1):
        step = AgentStep(step_number=step_num)

        # Build messages — includes retrieved evidence, not summaries
        system_content = TASK_PROMPT
        if retrieved_context:
            system_content += (
                f"\n\nRELEVANT EVIDENCE FROM YOUR PREVIOUS INVESTIGATION:\n\n"
                f"{retrieved_context}\n\n"
                f"Use this evidence to continue. You can read additional files "
                f"or search for more information. When you have enough evidence "
                f"to identify the root cause, state your CONCLUSION with exact "
                f"string values and file:line references."
            )

        messages = [
            {"role": "system", "content": system_content},
            {
                "role": "user",
                "content": (
                    f"Step {step_num}/{MAX_STEPS}. "
                    "Investigate the bug. Use tools to examine the codebase. "
                    "When you have enough evidence, state your final CONCLUSION."
                ),
            },
        ]

        # Agent turn — may involve multiple tool calls
        tool_round = 0
        while tool_round < 3:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOL_SCHEMAS,
                temperature=0.0,
            )
            result.total_tokens += response.usage.total_tokens if response.usage else 0
            msg = response.choices[0].message

            tool_calls = parse_tool_calls(msg)
            if not tool_calls:
                step.reasoning = msg.content or ""
                break

            messages.append(msg)
            step.tool_calls.extend(tool_calls)

            for tc in tool_calls:
                tool_result = execute_tool(tc["name"], tc["arguments"])
                step.tool_results.append({"tool": tc["name"], "result": tool_result})

                # ── THE KEY MECHANISM: Append to trace log ──
                # Raw evidence is preserved forever, never compressed.
                trace_log.append(
                    {
                        "step": step_num,
                        "tool": tc["name"],
                        "args": tc["arguments"],
                        "result": tool_result,
                    }
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": tool_result,
                    }
                )
                if verbose:
                    print(f"    [{tc['name']}] {json.dumps(tc['arguments'])}")

            tool_round += 1
        else:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,
            )
            result.total_tokens += response.usage.total_tokens if response.usage else 0
            step.reasoning = response.choices[0].message.content or ""

        result.steps.append(step)

        if verbose:
            print(f"  Step {step_num}: {len(step.tool_calls)} tool calls, {len(trace_log)} trace entries")
            if step.reasoning:
                preview = step.reasoning[:120].replace("\n", " ")
                print(f"    Reasoning: {preview}...")

        # Check if agent reached a conclusion
        if "CONCLUSION:" in step.reasoning:
            result.conclusion = step.reasoning
            result.raw_final_response = step.reasoning
            break

        # ── Retrieve relevant evidence for next step ──
        # Determine what the agent is currently focused on
        current_focus = step.reasoning[:200] if step.reasoning else "VIP discount not applied"
        retrieved_context = _retrieve_relevant(
            client, model, trace_log, current_focus
        )

        if verbose:
            print(f"    Retrieved: {len(retrieved_context)} chars of evidence")

    else:
        # Exhausted all steps — final attempt with all evidence
        final_retrieval = _retrieve_relevant(
            client, model, trace_log, "root cause of VIP discount bug with exact string values"
        )
        messages = [
            {"role": "system", "content": TASK_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Here is ALL the evidence from your investigation:\n\n"
                    f"{final_retrieval}\n\n"
                    "State your final CONCLUSION now with the root cause, "
                    "exact data flow, and file:line evidence."
                ),
            },
        ]
        response = client.chat.completions.create(
            model=model, messages=messages, temperature=0.0
        )
        result.total_tokens += response.usage.total_tokens if response.usage else 0
        final = response.choices[0].message.content or ""
        result.conclusion = final
        result.raw_final_response = final

    return result
