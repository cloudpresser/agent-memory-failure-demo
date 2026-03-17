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

Both agents read the same 11 files in the same order — logs, bug report, then every source file. The investigation path is identical. The **only** difference is how they manage memory between reads.

### Agent A: Summarizing

```
for each file:
    1. Read the file
    2. LLM call compresses (running_summary + file content) → new summary
    3. Raw file content is DISCARDED
after all files:
    4. LLM concludes from summary alone
```

After reading `utils.ts`, the summary might say:

> *"The findings from utils.ts reveal several utility functions that handle string normalization, validation, and formatting."*

Accurate — but it's lost **what** normalization means (`toLowerCase()`), the **direction** (uppercase → lowercase), and the **exact input** (`"VIP"`). After 11 rounds of compression, the summary retains patterns but not precise values.

### Agent B: Retrieval

```
for each file:
    1. Read the file
    2. APPEND raw content to trace log (never overwrite)
after all files:
    3. LLM retrieval selects most relevant raw entries
    4. LLM concludes from raw evidence
```

Nothing is ever destroyed. When the agent needs to correlate `"VIP"` from `user.ts` with `"vip"` from `utils.ts` and `"VIP"` from `discount.ts`, all three raw values are in the trace — the retrieval step surfaces them verbatim.

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

### Actual Results (GPT-4o-mini)

Both agents read all 11 files in the same order. The only difference is memory management.

**Summarizing Agent** — concluded after 11 steps, 9,624 tokens:

```
CONCLUSION: The root cause of the issue is that the VIP discount logic is not
being triggered due to a misconfiguration in the discount application function,
which fails to recognize VIP users correctly.

DATA FLOW:
  step 1: checkout(user=u003, item_price=150)
  step 2: calculate_discount(user=u003, item_price=150)       ← wrong function name
  step 3: get_discount_rate(user.membership)                   ← hallucinated function
  step 4: apply_discount(item_price=150, discount_rate=0)      ← hallucinated function

EVIDENCE:
  - discount.ts:30 (calculate_discount function)               ← wrong line number
  - discount.ts:15 (get_discount_rate function)                ← doesn't exist
  - discount.ts:50 (apply_discount function)                   ← doesn't exist
```

After 11 rounds of summarization, the agent lost all specific details. It hallucinated function names (`get_discount_rate`, `apply_discount`) that don't exist in the codebase, cited line numbers that are wrong, and never identified case sensitivity or `normalizeString` as the mechanism.

**Retrieval Agent** — concluded after 11 steps, 726 tokens:

```
CONCLUSION: The root cause of the issue is that the user type is being normalized
to lowercase ("vip") but the discount calculation logic is not handling the
lowercase user type correctly, resulting in no discount being applied.

DATA FLOW:
  step 1: getUserType(userId="u003") returns userType="VIP"
  step 2: normalizeString(input="VIP") returns output="vip"
  step 3: calculateDiscount(price=150.00, userType="vip") is called, but the
          discount logic does not recognize "vip" as a valid user type for
          applying the 20% discount.

EVIDENCE:
  - getUserType function logs the user type as "VIP"
  - normalizeString function confirms the conversion to lowercase
  - calculateDiscount is called with userType="vip", which does not match
    the expected uppercase "VIP" for applying the discount
```

The retrieval agent preserved raw evidence from every file and produced the correct root cause with exact string values at each step in the data flow.

**Comparison:**

| Metric                         | Summarizing | Retrieval |
|--------------------------------|:-----------:|:---------:|
| Steps taken                    | 11          | 11        |
| Tokens used                    | 9,624       | 726       |
| Mentions case sensitivity      | no          | yes       |
| Mentions exact string values   | no          | yes       |
| Mentions normalizeString       | no          | yes       |
| Specific root cause identified | no          | yes       |
| Hallucinated function names    | yes         | no        |

*Note: LLM outputs are non-deterministic. Results vary between runs, but the structural advantage of retrieval is consistent across repeated trials.*

### Actual Results (GPT-4o)

Same experiment, stronger model. The failure persists.

**Summarizing Agent** — 9,808 tokens:

```
CONCLUSION: The root cause is a missing condition in the applyDiscount function
that fails to check for VIP status, resulting in no discount being applied.

DATA FLOW:
  1. checkout(userId: 'u003', itemPrice: 150) is called.
  2. getUserDetails(userId: 'u003') returns { userId: 'u003', tier: 'VIP' }  ← hallucinated
  3. calculateDiscount(userTier: 'VIP', itemPrice: 150) is called.
  4. Inside calculateDiscount, the function checks for 'Premium' and 'Standard'
     tiers but lacks a condition for 'VIP', defaulting to no discount.       ← wrong
  5. applyDiscount(itemPrice: 150, discount: 0) is called.                   ← hallucinated

EVIDENCE:
  - discount.ts:22                                                           ← wrong line
  - discount.ts:35 (applyDiscount)                                           ← doesn't exist
```

GPT-4o produced a *more confident* wrong answer. The summaries read better, but the same structural loss occurred: `normalizeString`, case sensitivity, and the exact `"VIP"` → `"vip"` transformation are all absent. It hallucinated `applyDiscount` and `getUserDetails` — functions that don't exist — and wrongly concluded that `calculateDiscount` lacks a VIP condition (it has one; the input is wrong).

**Retrieval Agent** — 886 tokens:

```
CONCLUSION: The root cause is a case mismatch in the discount calculation logic;
the userType is normalized to lowercase "vip", but the discount logic checks
for uppercase "VIP".

DATA FLOW:
  step 1: getUserType retrieves user type for userId=u003, result is "VIP" (logs.txt:20)
  step 2: normalizeString is called with input="VIP", output is "vip" (logs.txt:21, utils.ts:11-12)
  step 3: calculateDiscount is called with price=150.00 and userType="vip" (logs.txt:22)
  step 4: Discount logic checks if userType is "VIP" (discount.ts:33), but since
          userType is "vip", no discount rule matches (logs.txt:23)

EVIDENCE: logs.txt:21, utils.ts:11-12, discount.ts:33, logs.txt:23
```

Correct root cause, correct data flow, correct file:line references.

**Comparison across models:**

| Metric                         | 4o-mini Summarizing | 4o-mini Retrieval | 4o Summarizing | 4o Retrieval |
|--------------------------------|:-------------------:|:-----------------:|:--------------:|:------------:|
| Mentions case sensitivity      | no                  | yes               | no             | yes          |
| Mentions normalizeString       | no                  | yes               | no             | yes          |
| Specific root cause identified | no                  | yes               | no             | yes          |
| Hallucinated function names    | yes                 | no                | yes            | no           |
| Correct file:line references   | no                  | partial           | no             | yes          |

The stronger model made the summaries *sound* better without fixing the structural problem. Both models, under summarization, lost the same critical detail.

## Why This Matters

This isn't an academic exercise. Summarization-based memory is the default in most production agent systems — LangChain's `ConversationSummaryMemory`, AutoGPT's context compression, and countless custom implementations. They all share the same failure mode.

The failure is **systematic, not random**:
- It happens whenever the critical detail has low salience in isolation
- It gets worse as investigation length increases (more compression rounds)
- It's invisible — the summary reads as correct and complete
- Stronger models make better summaries but the structural loss remains — GPT-4o produced a more confident wrong answer than GPT-4o-mini

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
