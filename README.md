# Precedent-for-Hackathon

Precedent is a court for AI agents on GenLayer. Agents file disputes, a validator jury rules on who is right, and every ruling becomes on-chain case law. New disputes are automatically matched to the most similar past ruling and checked for consistency, so the agentic economy builds its own body of common law.

## Autonomous Agent

`agent/agent.mjs` is a small Node.js watcher agent, Variant A of the Precedent design. It does not decide anything, it only notices and reports, the same separation of duties Halt's `watcher.mjs` uses.

**What is simulated vs real:** the two "deals" the agent watches (who owes what, by what deadline) are hand-authored example data, not pulled from a live marketplace. Everything from the moment it calls `file_dispute()` onward is 100% real: a real signed transaction, a real GenLayer validator jury, a real on-chain ruling.

**How it works:** on each run, the agent checks its deal list against the current time. If a deadline has passed with no delivery recorded, it estimates the required v0.6 transaction fees via `client.estimateTransactionFees(...)`, then submits `file_dispute()` to the Precedent contract and waits for the jury's ruling.

**Verified live run** (2026-09-10, tx `0x4b4af7b4077322fb5f0d9a18067f148c033c9a289a67eae8e27caf026a755603`):

- `status_name: "FINALIZED"`, `result_name: "MAJORITY_AGREE"`, `lifecycle: { state: "finalized", outcome: "accepted" }`
- Reached consensus in round 0, no re-proposal needed
- 3 of 5 validators voted `AGREE` before quorum was reached
- Fee deposit ~0.1 GEN, ~99.9% automatically refunded after settlement

**Run it yourself:**

```bash
npm install genlayer-js@rc
export PRECEDENT_PK=0x... # a funded studio-next test private key
node agent/agent.mjs
```
