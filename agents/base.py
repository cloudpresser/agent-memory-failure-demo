"""
Shared configuration for both agents.

OpenAI client setup, tool schemas, and common types.
"""

import os
import json
from dataclasses import dataclass, field
from openai import OpenAI


def get_client() -> OpenAI:
    """Create an OpenAI client from environment."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not set. Copy .env.example to .env and add your key."
        )
    return OpenAI(api_key=api_key)


def get_model() -> str:
    """Get the model to use, defaulting to gpt-4o-mini."""
    return os.environ.get("MODEL", "gpt-4o-mini")


# ── Tool schemas for OpenAI function calling ──────────────────────────

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List all files available in the task directory.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file in the task directory. Returns the file with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The filename to read, e.g. 'checkout.ts' or 'config.ts'",
                    }
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a string pattern across all TypeScript source files. Case-insensitive. Returns matching lines with file and line number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search string to look for",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_logs",
            "description": "Read the application runtime logs (logs.txt).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_test_results",
            "description": "Read the test suite output (test_results.txt).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


# ── Shared system prompt (task description) ───────────────────────────

TASK_PROMPT = """You are a senior software engineer debugging a production issue.

BUG REPORT:
VIP users are not receiving their 20% discount during checkout.
User u003 (Carol Davis) is a VIP member but consistently pays full price.
Premium discounts work correctly. Standard users correctly pay full price.
The issue is specific to VIP-tier users.
Cache has been cleared and the issue persists — it's not a stale cache problem.
Config values for discount rates have been verified as correct.

YOUR TASK:
1. Start by reading the application logs — they show the exact runtime values.
2. Read each source file in the checkout flow to trace how values are transformed.
   When a file imports a function from another module, READ that module too.
3. Once identified, trace the EXACT data flow for user u003 purchasing a $150 item.
   List every function call and the exact string values at each step.
4. State your conclusion with the specific root cause and evidence.

You have tools: list_files, read_file, search_code, read_logs, read_test_results.
Investigate systematically — read logs first, then trace the code path file by file.
Do not conclude until you have read ALL files in the import chain.

When ready, respond with your final conclusion in this format:

CONCLUSION: <one-sentence root cause>
DATA FLOW:
  step 1: <function call and exact values>
  step 2: ...
EVIDENCE: <file:line references that support your conclusion>
"""


# ── Result types ──────────────────────────────────────────────────────


@dataclass
class AgentStep:
    """A single step in the agent's investigation."""

    step_number: int
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class AgentResult:
    """The final result from an agent run."""

    agent_name: str
    conclusion: str = ""
    steps: list[AgentStep] = field(default_factory=list)
    total_tokens: int = 0
    raw_final_response: str = ""


def parse_tool_calls(response_message) -> list[dict]:
    """Extract tool calls from an OpenAI response message."""
    if not response_message.tool_calls:
        return []
    calls = []
    for tc in response_message.tool_calls:
        calls.append(
            {
                "id": tc.id,
                "name": tc.function.name,
                "arguments": json.loads(tc.function.arguments),
            }
        )
    return calls
