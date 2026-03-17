# When Summaries Fail

**A minimal demonstration of how lossy memory degrades mechanistic correctness in AI agents — even when the final answer looks right.**

Two AI agents investigate the same bug. One compresses its context at each step. The other keeps raw evidence and retrieves on demand. With weaker models, the compressing agent gets the wrong answer. With stronger models, it gets the *right* answer — but with the **wrong causal explanation**, pointing to the wrong code, citing nonexistent functions, and producing an unfalsifiable narrative.

This isn't a cherry-picked failure. It's a structural property of lossy memory that becomes *harder to detect* as models improve.

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

### Actual Results (GPT-5.4)

The strongest model available. The summarizing agent finally gets the *general direction* right — but the quality gap remains.

**Summarizing Agent** — 9,936 tokens:

```
CONCLUSION: checkout.ts lowercases the user tier to "vip" before applying
a checkout-local comparison that only recognizes the uppercase string "VIP",
so user u003 is routed to the no-discount branch and charged full price.

DATA FLOW:
  step 2: checkout.ts fetches the user record for u003; the user service
          returns tier string "VIP".
  step 4: inside checkout.ts, the tier is normalized with a lowercase
          operation, producing exact string "vip".
  step 5: checkout then performs its own tier check against exact string "VIP"
          instead of using the normalized value consistently or delegating
          to calculateDiscount.                                              ← wrong
  step 6: comparison "vip" === "VIP" evaluates false.

EVIDENCE:
  - checkout.ts: the checkout path performs user-tier normalization and then
    a checkout-local VIP comparison                                          ← wrong mechanism
```

GPT-5.4 correctly identified the `"VIP"` → `"vip"` transformation and that it causes the comparison to fail. But it invented a wrong mechanism: it claims checkout.ts performs "its own tier check" and says the bug is "not calculateDiscount." In reality, checkout.ts delegates to `calculateDiscount` — the comparison happens there, not in checkout. No specific file:line references.

**Retrieval Agent** — 2,323 tokens:

```
CONCLUSION: VIP discounts fail because checkout() normalizes the database
value "VIP" to "vip", but calculateDiscount() only matches the uppercase
string "VIP", so VIP users fall through to no discount.

DATA FLOW:
  step 1:  checkout("u003", 150) is called in checkout.ts.
  step 2:  getCachedUserType("u003") returns no value / cache miss.
  step 3:  getUserType("u003") returns the exact stored type string "VIP".
  step 4:  setCachedUserType("u003", "VIP") stores the raw user type in cache.
  step 5:  normalizeString("VIP") returns "vip" because it does trim().toLowerCase().
  step 6:  calculateDiscount(150, "vip") is called.
  step 7:  inside calculateDiscount, the "premium" check fails: "vip" !== "premium".
  step 8:  inside calculateDiscount, the VIP check fails: "vip" !== "VIP".
  step 9:  calculateDiscount returns the original price 150.
  step 10: discountApplied = finalPrice < price evaluates to 150 < 150 = false.
  step 11: formatCurrency(150) produces the final price string.

EVIDENCE:
  - logs.txt:18-24 (exact runtime path for user u003)
  - checkout.ts:22-32 (checkout flow: cache → getUserType → normalizeString → calculateDiscount)
  - user.ts:26-31 (getUserType returns type string exactly as stored)
  - utils.ts:11-12 (normalizeString converts "VIP" to "vip")
  - discount.ts:29-35 (discount logic matches "premium" and uppercase "VIP" only)
  - discount.ts:43-44 (isDiscountEligible also expects uppercase "VIP")
  - config.ts:6-10 (VIP rate is correctly configured as 0.2)
```

A forensic-quality 12-step trace with every function call, exact string values, and correct file:line references across 7 files. The retrieval agent even identified the `isDiscountEligible` helper function's matching inconsistency.

**Comparison across all three models:**

| Metric                         | 4o-mini Sum | 4o-mini Ret | 4o Sum | 4o Ret | 5.4 Sum | 5.4 Ret |
|--------------------------------|:-----------:|:-----------:|:------:|:------:|:-------:|:-------:|
| Mentions case sensitivity      | no          | yes         | no     | yes    | yes     | yes     |
| Mentions normalizeString       | no          | yes         | no     | yes    | yes*    | yes     |
| Correct mechanism              | no          | yes         | no     | yes    | no      | yes     |
| Hallucinated functions         | yes         | no          | yes    | no     | no      | no      |
| Correct file:line references   | no          | partial     | no     | yes    | no      | yes     |
| Forensic data flow trace       | no          | no          | no     | no     | no      | yes     |

*\* GPT-5.4's summarizing agent mentions "lowercase operation" but attributes the comparison to checkout.ts rather than calculateDiscount — the mechanism is wrong even though the symptom is correctly identified.*

**The pattern across models:** Stronger models narrow the gap in *symptom identification* but not in *mechanistic accuracy*. GPT-5.4's summarizing agent sounds convincing — it correctly identifies the case transformation — but invents a wrong explanation for where the comparison happens. The retrieval agent, with access to raw evidence, produces a precise forensic trace every time.

## Mechanistic Fidelity vs Answer Accuracy

The GPT-5.4 result reveals a deeper failure mode than "summaries cause wrong answers."

Both agents arrive at the correct high-level diagnosis: a case mismatch between `"VIP"` and `"vip"` causes the discount to fail. But only one agent traces the *actual causal chain*. The other reconstructs a plausible story that happens to reach the right conclusion.

| Claim | Summarizing (GPT-5.4) | Retrieval (GPT-5.4) | Actual Code |
|---|---|---|---|
| Where does the comparison happen? | "checkout-local VIP comparison" | `calculateDiscount` in `discount.ts:33` | `discount.ts:33` |
| What calls what? | "instead of delegating to calculateDiscount" | `checkout` -> `normalizeString` -> `calculateDiscount` | `checkout.ts:29-31` |
| Role of calculateDiscount | "not the issue" | "the comparison `"vip" === "VIP"` fails here" | It IS where the comparison fails |
| Where would you apply the fix? | checkout.ts (wrong file) | discount.ts:33 or utils.ts:12 (correct) | discount.ts or utils.ts |

The summarizing agent would lead an engineer to "fix" the wrong file. The retrieval agent points to the exact line that needs to change.

This distinction matters because most evaluations only check **answer correctness** — did the agent identify the bug? By that metric, both agents pass with GPT-5.4. But answer correctness and **reasoning correctness** are different things:

|  | Correct answer | Correct mechanism |
|---|:-:|:-:|
| Summarizing agent | yes | no |
| Retrieval agent | yes | yes |

**As models improve, memory failures don't disappear — they become harder to detect.** Weaker models under summarization produce obviously wrong answers (hallucinated functions, wrong conclusions). Stronger models produce *right answers with wrong justifications* — plausible-sounding causal stories that are unfalsifiable without the raw evidence.

This is a more dangerous failure mode:
- Harder to catch in evaluation (the answer looks correct)
- Harder to debug (the reasoning sounds plausible)
- Leads to wrong actions (fixing the wrong code, changing the wrong config)
- Erodes trust invisibly (the system appears reliable until it isn't)

## Why This Matters

This isn't an academic exercise. Summarization-based memory is the default in most production agent systems — LangChain's `ConversationSummaryMemory`, AutoGPT's context compression, and countless custom implementations. They all share the same failure mode.

The failure is **systematic, not random**:
- It happens whenever the critical detail has low salience in isolation
- It gets worse as investigation length increases (more compression rounds)
- It's invisible — the summary reads as correct and complete
- Stronger models don't fix the problem — they mask it. Better priors produce better-sounding confabulations, not better reasoning

In practice, the summarizing agent:
- "fixes" the wrong code (checkout.ts instead of discount.ts)
- introduces regressions from changes based on incorrect causal models
- cannot justify its decisions when asked for evidence

The retrieval agent's output is:
- **debuggable** — every claim maps to a file:line reference
- **auditable** — the evidence chain can be independently verified
- **actionable** — it points to the exact line that needs to change

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

> Lossy memory does not always degrade final answers, but it systematically degrades causal fidelity and verifiability. As models improve, this failure becomes harder to detect — incorrect reasoning produces correct answers.

## Author

[Luiz Ozorio](https://github.com/cloudpresser) — building control systems for intelligent software.
