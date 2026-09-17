# Benchmark

A small, honest benchmark run against the live Precedent contract on GenLayer Studio Next.

Five predefined dispute cases were filed with expected outcomes for **winner**, **evidence strength**, and (where applicable) **precedent consistency**. Each case was submitted to the real validator jury and finalized on chain.

**Contract:** `0x3F7EAb3Ff139BDe2005D5e38c42c8195CDb452c3`
**Network:** GenLayer studio-next (studioDevnet, chain id 61997)
**Date:** 2026-09-17

## Results

- **Finalized:** 5 / 5 — every case reached consensus on chain
- **Verdict correct:** 5 / 5 — the jury named the expected winner every time
- **Full match (winner + evidence + precedent):** 3 / 5

| # | Case | Winner (expected) | Evidence (expected) | Precedent | Cited | tx |
|---|---|---|---|---|---|---|
| 1 | Strong textual evidence, clear claim | CLAIMANT ✅ | STRONG ✅ | — | `PREC-2026-0013` | [`0xcd8e60ee…`](https://explorer-studio-dev.genlayer.com/) |
| 2 | Similar to case 1 (precedent auto-match test) | CLAIMANT ✅ | STRONG ✅ | CONSISTENT ✅ | `PREC-2026-0014` | [`0xeb23a4b7…`](https://explorer-studio-dev.genlayer.com/) |
| 3 | Clear respondent win with timestamp evidence | RESPONDENT ✅ | IRRELEVANT (expected STRONG) ⚠️ | — | none | [`0xfcb59084…`](https://explorer-studio-dev.genlayer.com/) |
| 4 | Genuinely unclear, no evidence | UNCLEAR ✅ | NONE ✅ | — | none | [`0xb83b8753…`](https://explorer-studio-dev.genlayer.com/) |
| 5 | URL as evidence (expected IRRELEVANT) | CLAIMANT ✅ | STRONG (expected IRRELEVANT) ⚠️ | CONTRADICTS | `PREC-2026-0002` | [`0x1e8f3ae8…`](https://explorer-studio-dev.genlayer.com/) |

## What this shows

- **The consensus mechanism is reliable.** All five filings finalized in round 0 with `MAJORITY_AGREE`. Independent validator models converge on the single-token questions.
- **Verdict accuracy is high.** In every case the panel correctly identified the winner (or correctly returned `UNCLEAR` for a genuinely ambiguous case).
- **Precedent auto-matching works between independent runs.** Case 2 was filed as a separate transaction from case 1, and the contract still found case 1 on its own and ruled the new case `CONSISTENT` with it.

## What the misses reveal (honest reading)

- **Case 3** — the winner was correctly `RESPONDENT`, but the evidence was rated `IRRELEVANT` rather than `STRONG`. The evidence question in this contract asks specifically *how strongly the evidence supports the claimant*. A timestamp that vindicates the respondent legitimately does not support the claimant, so `IRRELEVANT` is a defensible reading — but it is not what the benchmark expected. This shows the evidence question is doing real work, not rubber-stamping.
- **Case 5** — a bare URL was rated `STRONG` on this run. On an earlier BILD-URL test it was rated `IRRELEVANT` (that trace is what motivated the frontend hint "describe the evidence in words the jury can read"). The two runs together confirm the guidance already in the README: bare URLs are not reliably assessed, because the jury cannot actually open them — it sees only the string.

## Reproducing

The benchmark script (`bench/benchmark.mjs`) reads `PRECEDENT_PK` from the environment, files each case as a real on-chain transaction, waits for finalization, and prints the results table. Cost per run: roughly 0.5 GEN in fees, ~99% refunded after settlement.

```bash
npm install genlayer-js@rc
export PRECEDENT_PK=0x...
node bench/benchmark.mjs
```
