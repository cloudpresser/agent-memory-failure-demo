# When Summaries Fail

**A minimal demonstration of information loss in agent memory.**

Two AI agents investigate the same bug. One compresses its context at each step. The other keeps raw evidence and retrieves on demand. The compressing agent loses a critical detail. The retrieval agent doesn't.

This isn't a cherry-picked failure — it's a **structural** failure mode. Any task where the answer depends on a low-salience detail (an exact string value, a specific line number, a precise configuration) is vulnerable to summarization loss.

## The Problem

Most agent systems manage long contexts by summarizing. After each reasoning step, the conversation is compressed into a shorter representation, and the original messages are discarded. This saves tokens and keeps the context window manageable.

The problem: summaries optimize for **salience**. High-level patterns survive compression. Low-level details don't. When the correct answer depends on a detail that looks unimportant in isolation — like whether a string is `"VIP"` or `"vip"` — summarization systematically drops it.

This demo makes that failure concrete and reproducible.

## The Task

A small TypeScript codebase has a bug: VIP users don't receive their 20% discount. The root cause is a **case-sensitivity mismatch** buried across four files:

```
getUserType("u003")  →  returns "VIP"           (user.ts)
         ↓
normalizeString("VIP")  →  returns "vip"         (utils.ts — calls .toLowerCase())
         ↓
checkout passes "vip" to calculateDiscount        (checkout.ts)
         ↓
calculateDiscount checks: userType === "VIP"      (discount.ts — uppercase!)
         ↓
"vip" !== "VIP"  →  no discount applied           ← bug
```

The codebase includes red herrings (a caching layer, auth middleware, config files, type definitions) that consume investigation time and summary budget without contributing to the solution.

## Two Agents

Both agents get the same tools (`read_file`, `search_code`, `read_logs`, `read_test_results`, `list_files`) and the same task prompt. The only difference is how they manage memory.

### Agent A: Summarizing

```
for each step:
    1. System prompt includes running_summary (starts empty)
    2. Agent reasons + calls tools
    3. Separate LLM call compresses everything into a summary
    4. Previous messages are DISCARDED
    5. Next step starts with only the summary
```

After investigating `utils.ts`, the summary might say:

> *"The normalizeString utility performs string normalization (trimming and case conversion) on user input before passing to discount calculation."*

Accurate — but it's lost the **direction** of the conversion (uppercase → lowercase) and the **exact input** (`"VIP"`). By the time the agent needs to compare values across files, that evidence is gone.

### Agent B: Retrieval

```
for each step:
    1. System prompt includes retrieved evidence from trace log
    2. Agent reasons + calls tools
    3. Raw tool outputs are APPENDED to trace log (never overwritten)
    4. Retrieval step selects relevant entries for next step
    5. Agent reasons with full evidence references
```

Nothing is ever destroyed. When the agent needs to correlate `"VIP"` from `user.ts` with `"vip"` from `utils.ts` and `"VIP"` from `discount.ts`, all three raw values are available in the trace.

## Running the Demo

### Prerequisites

- Python 3.11+
- An OpenAI API key

### Setup

```bash
git clone https://github.com/cloudpresser/agent-memory-failure-demo.git
cd agent-memory-failure-demo
python -m venv .venv
source .venv/bin/activate
pip install openai

# Set your API key
export OPENAI_API_KEY=sk-...
```

### Run

```bash
# Run both agents and compare (default: gpt-4o-mini)
python run.py

# Verbose output — see each step
python run.py --verbose

# Run a single agent
python run.py --agent a    # summarizing only
python run.py --agent b    # retrieval only

# Use a different model
MODEL=gpt-4o python run.py
```

### Expected Output

```
════════════════════════════════════════════════════════════════
  Agent Memory Failure Demo
  Task: VIP Discount Bug Investigation
  Model: gpt-4o-mini
════════════════════════════════════════════════════════════════

▸ Summarizing Agent
  Steps: 5
  Conclusion:
    CONCLUSION: The discount logic has a user type handling mismatch
    causing the VIP discount to not be applied correctly.

▸ Retrieval Agent
  Steps: 4
  Conclusion:
    CONCLUSION: Case mismatch — getUserType returns "VIP" (uppercase),
    normalizeString in utils.ts converts it to "vip" (lowercase), but
    calculateDiscount in discount.ts checks for "VIP" (uppercase).
    The === comparison fails because "vip" !== "VIP".
    DATA FLOW:
      step 1: getUserType("u003") → "VIP" (user.ts:31)
      step 2: normalizeString("VIP") → "vip" (utils.ts:12, calls .toLowerCase())
      step 3: calculateDiscount(150, "vip") — checks "vip" === "VIP" → false (discount.ts:33)
      step 4: Falls through to return price — no discount applied
    EVIDENCE: user.ts:18, utils.ts:12, checkout.ts:29, discount.ts:33

────────────────────────────────────────────────────────────────
  Comparison
────────────────────────────────────────────────────────────────

  Metric                              Summarizing     Retrieval
  ─────────────────────────────────── ─────────────── ───────────────
  Mentions case sensitivity            no              yes
  Mentions exact string values         no              yes
  Specific root cause identified       no              yes
  Vague/general conclusion             yes             no
```

*Note: LLM outputs are non-deterministic. Results vary between runs, but the structural advantage of retrieval is consistent across repeated trials.*

## Why This Matters

This isn't an academic exercise. Summarization-based memory is the default in most production agent systems — LangChain's `ConversationSummaryMemory`, AutoGPT's context compression, and countless custom implementations. They all share the same failure mode.

The failure is **systematic, not random**:
- It happens whenever the critical detail has low salience in isolation
- It gets worse as investigation length increases (more compression rounds)
- It's invisible — the summary reads as correct and complete
- Stronger models make better summaries, but the structural loss remains

The fix isn't "better summarization." It's **never destroying raw evidence**:
- Summarize for *navigation*, not for *storage*
- Keep an append-only trace log of raw observations
- Retrieve relevant entries on demand instead of compressing everything

This is the same principle behind observability in distributed systems: you don't summarize your logs and throw away the originals. You store the raw data and build views on top.

## Project Structure

```
agent-memory-failure-demo/
├── README.md
├── pyproject.toml
├── .env.example
├── run.py                   # Entry point — runs both agents, compares results
├── task/                    # The "codebase" agents investigate
│   ├── bug_report.md        # Starting prompt
│   ├── discount.ts          # Checks for "VIP" (uppercase)
│   ├── user.ts              # Returns "VIP" from database
│   ├── checkout.ts          # Calls normalizeString on user type
│   ├── utils.ts             # normalizeString → .toLowerCase()
│   ├── config.ts            # Discount rates (red herring — correct)
│   ├── cache.ts             # Caching layer (red herring — working)
│   ├── middleware.ts         # Auth middleware (red herring — fine)
│   ├── types.ts             # Type definitions (not enforced)
│   ├── logs.txt             # Application logs with buried evidence
│   └── test_results.txt     # Test output showing the failure
├── agents/
│   ├── base.py              # OpenAI client, tool schemas, shared types
│   ├── tools.py             # Tool implementations (read, search, logs)
│   ├── summarizing.py       # Agent A: compress-then-reason loop
│   └── retrieval.py         # Agent B: store-then-retrieve loop
└── results/                 # Run output (gitignored)
```

## Takeaway

> Never destroy raw evidence. Summarize for navigation, not for storage.

## Author

[Luiz Ozorio](https://github.com/cloudpresser) — building control systems for intelligent software.
