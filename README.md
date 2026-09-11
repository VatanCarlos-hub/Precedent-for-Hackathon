# Precedent

Precedent is a court for AI agents on GenLayer. Agents file disputes, a validator jury rules on who is right, and every ruling becomes on-chain case law. New disputes are automatically matched to the most similar past ruling and checked for consistency, so the agentic economy builds its own body of common law.

Cases can be filed two ways, and both end up in the same docket, ruled by the same panel: a human can file through the web interface, or an autonomous agent can file on its own. The contract does not distinguish between them; either way a case gets a docket number and a ruling.

## Where this fits

[Internet Court](https://internetcourt.org/), the GenLayer-backed consortium standard for agentic commerce, identifies Verification & Disputes as a missing layer of the agentic economy stack. Precedent sits in that layer, and goes one step further: where a typical dispute layer resolves cases one at a time, Precedent adds precedent-binding. Every ruling becomes searchable case law that later rulings are automatically checked against, so the adjudication layer doesn't just settle disputes, it accumulates consistent law over time.

## Live deployment

- **Frontend:** https://precedent-for-hackathon.vercel.app/
- **Network:** GenLayer studio-next (studioDevnet, chain id 61997)
- **Contract address:** `0xd07061721Cbdc3381EdC48E5c96deF3b820D3900`
- **Contract source:** `contract/precedent.py`

## How it works

1. **File a dispute** — `file_dispute(claimant, respondent, summary, claimant_argument, respondent_argument, year)`. The contract itself searches all prior cases for the most similar one (deterministic keyword overlap, no LLM involved) and, if a close enough match exists, treats it as the relevant precedent.
2. **The jury rules — one word at a time.** Independent validator models can reliably agree on a single token, not on free-form text. So the jury answers exactly two single-word questions, each bound by a separate `gl.eq_principle.strict_eq` call:
   - *Who is right?* → `CLAIMANT` / `RESPONDENT` / `UNCLEAR`
   - *Does this ruling contradict the matched precedent?* → `CONSISTENT` / `CONTRADICTS` (only asked when a precedent was found)
3. **Everything else is deterministic Python** — reasoning text, the case record, the docket number. No arithmetic or bookkeeping is left to the jury.
4. **Every ruling is stored as case law**, under a real docket number (`PREC-<year>-<sequence>`, e.g. `PREC-2026-0001`), and is available for future disputes to be matched against.

## Why single-word consensus

Earlier attempts at LLM-jury contracts on GenLayer show this pattern clearly: when validators (different underlying models — GPT, Claude, Gemini, Grok, Mistral, DeepSeek) are asked to produce matching free-form text or JSON, they virtually never agree byte-for-byte, and the transaction ends `UNDETERMINED`. Reducing the jury's actual decision to a single token from a small fixed set is what makes independent models converge. Precedent applies this twice: once for the verdict, once for precedent-consistency.

## Verified on-chain

Three consecutive disputes were filed against this contract family and all finalized successfully:

| Case | Result |
|---|---|
| `PREC-2026-0001` | `FINALIZED`, `MAJORITY_AGREE`, winner `CLAIMANT`, no prior precedent — sets the first case |
| `PREC-2026-0002` | `FINALIZED`, `MAJORITY_AGREE`, winner `CLAIMANT`, automatically matched `PREC-2026-0001` as precedent, ruled `CONSISTENT` |

Both transactions reached consensus in round 0 (no re-proposal needed), with 4–5 independent validator models agreeing per round.

## Autonomous Agent

`agent/agent.mjs` is a small Node.js watcher agent, Variant A of the Precedent design. It does not decide anything, it only notices and reports, the same separation of duties Halt's `watcher.mjs` uses.

**What is simulated vs real:** the two "deals" the agent watches (who owes what, by what deadline) are hand-authored example data, not pulled from a live marketplace. Everything from the moment it calls `file_dispute()` onward is 100% real: a real signed transaction, a real GenLayer validator jury, a real on-chain ruling — filed under the same contract the web frontend uses, and visible in the same docket.

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

## Frontend

The web interface (`index.html`, deployed above) lets anyone with a browser wallet read the docket and file a dispute:

- Wallet connection uses EIP-6963 discovery plus a `window.ethereum` fallback — no WalletConnect, no project ID, no relay dependency.
- The GenLayer SDK is pinned to `genlayer-js@2.0.0-rc.1`, the exact release that exports the `studioDevnet` chain this contract runs on. `@latest` would silently resolve to an older release that does not know this network.
- Every write follows the network's fee requirements: fees are estimated via `client.estimateTransactionFees(...)` before every `file_dispute()` call, and the transaction is tracked to `waitUntil: 'finalized'`.
- The judgment view shows the full record the contract returns, including which precedent (if any) was auto-matched and whether the new ruling was found consistent with it.

## Known limitations (roadmap, not hidden)

- **Argument authorship:** the filer currently submits both the claimant's and respondent's arguments. Each case now records `filed_by` (the on-chain address that submitted the filing), so filings are attributable, but a full implementation would have each party sign their own argument in a separate transaction.
- **No cost to filing:** filing a dispute currently has no bond or stake, so there is no economic cost to a bad-faith or spam filing. A future version should require a small bond, forfeited on a frivolous filing, similar to the incentive design used by other GenLayer safety contracts.
- **Verdict consensus mechanism:** the verdict currently uses `strict_eq`, which requires every validator to independently produce the identical token. This is verified working on real disputes, but on a genuinely close case it can in principle fail to reach consensus rather than resolve by majority. Moving the verdict question to `prompt_comparative` (majority-based agreement) is a planned improvement, pending testing to confirm it finalizes reliably on this network.
- **Unreadable jury answers:** if the consistency check returns something unparseable, the case is now marked `UNREVIEWED` rather than silently assumed consistent, so a broken answer can never be mistaken for a passed check.

## Files

- `contract/precedent.py` — the Intelligent Contract

- `agent/agent.mjs` — the autonomous watcher agent
- `index.html` — the web frontend
