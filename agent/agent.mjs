#!/usr/bin/env node
/**
 * Precedent Agent - Variant A (simulated deal watcher)
 * ------------------------------------------------------
 * This agent does NOT decide anything. It only:
 *   1. watches a small set of deals it has been told about,
 *   2. checks, on a schedule, whether each deal's deadline has passed
 *      without the deliverable being marked as received, and
 *   3. if so, files a real on-chain dispute against the Precedent
 *      contract by calling file_dispute().
 *
 * The Precedent jury (the deployed Intelligent Contract) is what actually
 * rules on the dispute. This script's only job is noticing and reporting.
 *
 * WHAT IS SIMULATED vs REAL:
 *   - The "deal" data below is a hand-authored example, not pulled from
 *     a live marketplace.
 *   - Everything from the point file_dispute() is called onward is 100%
 *     real: a real signed transaction, a real GenLayer validator jury,
 *     a real on-chain ruling, a real case_id.
 *
 * Usage:
 *   PRECEDENT_PK=0x... node agent.mjs
 *
 * Requires: npm install genlayer-js@rc  (the 2.0.0-rc line, which is the
 * only one that exports the studioDevnet chain this contract runs on)
 */

import { createClient, createAccount } from 'genlayer-js';
import { studioDevnet } from 'genlayer-js/chains';

const CONTRACT_ADDRESS = '0xd07061721Cbdc3381EdC48E5c96deF3b820D3900';

function resolveChain() {
  console.log('[agent] using official studioDevnet chain (id ' + studioDevnet.id + ')');
  return studioDevnet;
}

const DEALS = [
  {
    id: 'deal-001',
    claimant: 'Agent Client-Alpha',
    respondent: 'Agent Writer-Beta',
    summary: 'Writer-Beta was paid to deliver a 1000-word article by the deadline',
    deadline: new Date('2026-09-01T00:00:00Z'),
    delivered: false,
  },
  {
    id: 'deal-002',
    claimant: 'Agent Client-Gamma',
    respondent: 'Agent Writer-Delta',
    summary: 'Writer-Delta was paid to deliver a product description by the deadline',
    deadline: new Date('2099-01-01T00:00:00Z'),
    delivered: false,
  },
];

const alreadyFiled = new Set();

function isBreached(deal, now) {
  return !deal.delivered && now.getTime() > deal.deadline.getTime();
}

async function fileDispute(client, deal) {
  const year = String(new Date().getUTCFullYear());
  const claimantArgument =
    'The respondent was paid for: ' + deal.summary + '. ' +
    'The deadline (' + deal.deadline.toISOString() + ') has passed with no delivery recorded.';
  const respondentArgument = 'No response was received from the respondent before this filing.';

  console.log('[agent] deadline breached for ' + deal.id + ' - filing dispute...');

  try {
    const writeArgs = [
      deal.claimant,
      deal.respondent,
      deal.summary,
      claimantArgument,
      respondentArgument,
      year,
    ];

    // v0.6 requires an explicit fee distribution and feeValue on every
    // write. estimateTransactionFees builds both from the network's
    // current fee policy, per the official migration guidance: read the
    // estimate, then submit it unchanged.
    console.log('[agent] estimating transaction fees...');
    const fees = await client.estimateTransactionFees({
      address: CONTRACT_ADDRESS,
      functionName: 'file_dispute',
      args: writeArgs,
    });
    console.log('[agent] fee estimate: feeValue=' + fees.feeValue);

    const txHash = await client.writeContract({
      address: CONTRACT_ADDRESS,
      functionName: 'file_dispute',
      args: writeArgs,
      value: 0n,
      fees: fees,
    });

    console.log('[agent] transaction submitted: ' + txHash);
    console.log('[agent] waiting for the jury to finalize...');

    const receipt = await client.waitForTransactionReceipt({
      hash: txHash,
      status: 'FINALIZED',
      retries: 60,
      interval: 5000,
    });

    console.log('[agent] finalized. result:');
    console.log(receipt);
    return receipt;
  } catch (err) {
    console.log('[agent] FULL ERROR OBJECT:');
    console.log(err);
    console.log('[agent] STACK:');
    console.log(err && err.stack);
    console.log('[agent] CAUSE:');
    console.log(err && err.cause);
    throw err;
  }
}

async function watchOnce(client) {
  const now = new Date();
  console.log('[agent] checking ' + DEALS.length + ' deal(s) at ' + now.toISOString());

  for (const deal of DEALS) {
    if (alreadyFiled.has(deal.id)) continue;

    if (isBreached(deal, now)) {
      try {
        await fileDispute(client, deal);
        alreadyFiled.add(deal.id);
      } catch (err) {
        console.log('[agent] failed to file dispute for ' + deal.id);
      }
    } else {
      console.log('[agent] ' + deal.id + ': no breach (deadline ' + deal.deadline.toISOString() + ', delivered=' + deal.delivered + ')');
    }
  }
}

async function main() {
  const pk = process.env.PRECEDENT_PK;
  if (!pk) {
    console.log('Set PRECEDENT_PK to a funded test private key before running this agent.');
    process.exit(1);
  }

  const chain = resolveChain();
  const account = createAccount(pk);
  const client = createClient({ chain: chain, account: account });

  console.log('[agent] Precedent watcher starting. Contract: ' + CONTRACT_ADDRESS);
  await watchOnce(client);
  console.log('[agent] run complete.');
}

main().catch(function (err) {
  console.log('[agent] fatal error:');
  console.log(err);
  process.exit(1);
});
