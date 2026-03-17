"""
Agent A: Summarizing Agent

Memory strategy: compress-then-reason.
After each investigation step, the full conversation is summarized
by a separate LLM call, and previous messages are discarded.
The agent continues with only the compressed summary as context.

This simulates how many production agents manage long contexts —
compressing state to save tokens. The failure mode is systematic:
low-salience details (like exact string values) are dropped during
summarization, even when they're critical to the solution.
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


def _summarize_conversation(client, model: str, messages: list[dict]) -> str:
    """
    Separate LLM call to compress the conversation into a running summary.
    This is where information loss happens — the summarizer captures the
    gist but drops exact values, specific line numbers, and precise strings.
    """
    # Build a transcript of the conversation for the summarizer
    transcript_parts = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if role == "assistant" and not content:
            # Tool call message — skip raw representation
            continue
        if role == "tool":
            transcript_parts.append(f"[Tool result for {msg.get('name', '?')}]: {content[:500]}")
        elif content:
            transcript_parts.append(f"[{role}]: {content[:500]}")

    transcript = "\n".join(transcript_parts)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a summarization assistant. Compress the following "
                    "investigation transcript into a concise running summary. "
                    "Capture the key findings, what has been investigated, and "
                    "what remains to be checked. Be concise — aim for 3-5 sentences. "
                    "Focus on high-level findings and patterns, not raw data."
                ),
            },
            {"role": "user", "content": transcript},
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content


def run(verbose: bool = False) -> AgentResult:
    """
    Run the summarizing agent.

    Loop:
      1. System prompt includes running_summary (starts empty)
      2. Agent reasons and calls tools
      3. Separate LLM call summarizes the full conversation
      4. Previous messages are DISCARDED
      5. Next step uses only the summary as context
    """
    client = get_client()
    model = get_model()
    result = AgentResult(agent_name="Summarizing Agent")

    running_summary = ""

    for step_num in range(1, MAX_STEPS + 1):
        step = AgentStep(step_number=step_num)

        # Build messages for this step — fresh each time
        system_content = TASK_PROMPT
        if running_summary:
            system_content += (
                f"\n\nYOU HAVE ALREADY INVESTIGATED. Here is your running summary "
                f"of findings so far:\n\n{running_summary}\n\n"
                f"Continue your investigation from where you left off. "
                f"Do NOT re-read files you have already reviewed."
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
        while tool_round < 3:  # max 3 tool-calling rounds per step
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOL_SCHEMAS,
                temperature=0.0,
            )
            result.total_tokens += response.usage.total_tokens if response.usage else 0
            msg = response.choices[0].message

            # Check if agent wants to call tools
            tool_calls = parse_tool_calls(msg)
            if not tool_calls:
                # Agent is done with this step (text response)
                step.reasoning = msg.content or ""
                break

            # Execute tool calls
            messages.append(msg)  # append assistant message with tool_calls
            step.tool_calls.extend(tool_calls)

            for tc in tool_calls:
                tool_result = execute_tool(tc["name"], tc["arguments"])
                step.tool_results.append({"tool": tc["name"], "result": tool_result})
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
            # Hit tool round limit — get a final text response
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,
            )
            result.total_tokens += response.usage.total_tokens if response.usage else 0
            step.reasoning = response.choices[0].message.content or ""

        result.steps.append(step)

        if verbose:
            print(f"  Step {step_num}: {len(step.tool_calls)} tool calls")
            if step.reasoning:
                preview = step.reasoning[:120].replace("\n", " ")
                print(f"    Reasoning: {preview}...")

        # Check if agent reached a conclusion
        if "CONCLUSION:" in step.reasoning:
            result.conclusion = step.reasoning
            result.raw_final_response = step.reasoning
            break

        # ── THE KEY MECHANISM: Summarize and discard ──
        # This is where information loss happens.
        running_summary = _summarize_conversation(client, model, messages)

        if verbose:
            print(f"    Summary: {running_summary[:120]}...")

    else:
        # Exhausted all steps without conclusion — final attempt
        messages = [
            {"role": "system", "content": TASK_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Based on your investigation summary:\n\n{running_summary}\n\n"
                    "State your final CONCLUSION now with the root cause and data flow."
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
