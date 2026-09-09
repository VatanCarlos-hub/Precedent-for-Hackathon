# v0.3.0
# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }

import genlayer as gl
from genlayer.types import *

import json
import typing


# ── Deterministic helpers ────────────────────────────────────
# Run identically on every validator, so they never cause disagreement.

_STOP = {
    "the", "a", "an", "was", "were", "is", "are", "be", "been", "to", "of",
    "and", "or", "for", "in", "on", "at", "by", "with", "as", "that", "this",
    "it", "but", "not", "no", "paid", "agent", "delivered", "delivery",
}


def _norm(text: str) -> str:
    try:
        return str(text).strip()
    except Exception:
        return ""


def _pick(text: str, options: list) -> str:
    """Reduce a model answer to one allowed option. Returns '' if none match."""
    try:
        t = str(text).strip().upper()
    except Exception:
        return ""
    for opt in options:
        if opt.upper() == t:
            return opt
    for opt in options:
        if opt.upper() in t:
            return opt
    return ""


def _keywords(text: str) -> set:
    """Lowercased content words of a summary, minus stopwords. Deterministic."""
    out = set()
    try:
        cur = ""
        for ch in str(text).lower():
            if ("a" <= ch <= "z") or ("0" <= ch <= "9"):
                cur += ch
            else:
                if len(cur) >= 3 and cur not in _STOP:
                    out.add(cur)
                cur = ""
        if len(cur) >= 3 and cur not in _STOP:
            out.add(cur)
    except Exception:
        pass
    return out


def _similarity(a: set, b: set) -> float:
    """Jaccard overlap of two keyword sets. Deterministic, 0..1."""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    if union == 0:
        return 0.0
    return inter / union


class Precedent(gl.contract.Contract):
    # A court for AI agents that builds its own case law.
    #
    # When a dispute is filed, the contract itself searches the existing cases
    # (deterministically, by keyword overlap) for the most similar prior ruling.
    # No one has to know or cite a case number. The jury then answers two
    # single-word questions: who is right, and whether the new ruling stays
    # consistent with that automatically-found precedent. Single tokens are what
    # let independent validator models reach consensus.
    #
    # Storage:
    #   cases : case_id (str) -> JSON string of the full case record
    #   index : JSON string {"count": n, "ids": [...], "sums": {id: summary}}
    cases: gl.storage.TreeMap[str, str]
    index: str

    def __init__(self):
        self.index = ""

    def _load_index(self) -> dict:
        try:
            if self.index:
                obj = json.loads(self.index)
                if isinstance(obj, dict):
                    if "ids" not in obj:
                        obj["ids"] = []
                    if "sums" not in obj:
                        obj["sums"] = {}
                    if "count" not in obj:
                        obj["count"] = 0
                    return obj
        except Exception:
            pass
        return {"count": 0, "ids": [], "sums": {}}

    def _find_precedent(self, summary: str, idx: dict) -> str:
        """Return the case_id of the most similar prior case, or '' if none."""
        kw_new = _keywords(summary)
        best_id = ""
        best_score = 0.0
        sums = idx.get("sums", {})
        if not isinstance(sums, dict):
            return ""
        for cid, csum in sums.items():
            score = _similarity(kw_new, _keywords(csum))
            if score > best_score:
                best_score = score
                best_id = cid
        # Require a minimal overlap so unrelated cases are not linked.
        if best_score >= 0.20:
            return best_id
        return ""

    @gl.public.write
    def file_dispute(
        self,
        claimant: str,
        respondent: str,
        summary: str,
        claimant_argument: str,
        respondent_argument: str,
        year: str,
    ) -> str:
        claimant_l = _norm(claimant)
        respondent_l = _norm(respondent)
        summary_l = _norm(summary)
        arg_c = _norm(claimant_argument)
        arg_r = _norm(respondent_argument)
        # Year is passed in, never read from a clock: a contract has no
        # consensus-safe wall clock, so validators must all receive the same
        # value from the caller.
        year_l = _norm(year)
        if len(year_l) != 4 or not year_l.isdigit():
            year_l = "0000"

        idx = self._load_index()
        new_num = int(idx.get("count", 0)) + 1
        # Continuous docket numbering, court-style: PREC-2026-0001
        case_id = "PREC-" + year_l + "-" + str(new_num).rjust(4, "0")

        # The contract finds the most relevant precedent by itself.
        cited = self._find_precedent(summary_l, idx)

        precedent_text = ""
        precedent_found = False
        if cited:
            try:
                raw_prev = self.cases[cited]
                if raw_prev:
                    prev = json.loads(raw_prev)
                    if isinstance(prev, dict):
                        precedent_text = (
                            "Prior case " + cited + ": "
                            + str(prev.get("summary", "")) + " | Ruling: winner="
                            + str(prev.get("winner", "")) + "; reasoning: "
                            + str(prev.get("reasoning", ""))
                        )
                        precedent_found = True
            except Exception:
                precedent_found = False

        # ── Jury question 1: who is right (ONE token) ───────
        def judge_winner() -> str:
            prompt = (
                "You are one juror on a panel resolving a dispute between two "
                "parties. Read the summary and both arguments and decide who is "
                "in the right.\n\n"
                "Summary: " + summary_l + "\n\n"
                "CLAIMANT (" + claimant_l + ") argues: " + arg_c + "\n\n"
                "RESPONDENT (" + respondent_l + ") argues: " + arg_r + "\n\n"
                "Reply with EXACTLY ONE word in capitals and nothing else: "
                "CLAIMANT or RESPONDENT or UNCLEAR"
            )
            raw = gl.nondet.exec_prompt(prompt)
            picked = _pick(raw, ["CLAIMANT", "RESPONDENT", "UNCLEAR"])
            return picked if picked else "UNCLEAR"

        winner = gl.eq_principle.strict_eq(judge_winner)

        # ── Jury question 2: consistency with precedent (ONE token) ──
        consistent = "NA"
        if precedent_found:
            wnr = winner

            def judge_consistency() -> str:
                prompt = (
                    "You are one juror ensuring rulings stay consistent with "
                    "established case law, like a court bound by precedent.\n\n"
                    "The precedent:\n" + precedent_text + "\n\n"
                    "The current dispute summary: " + summary_l + "\n"
                    "The proposed ruling for the current dispute: winner is "
                    + wnr + ".\n\n"
                    "Question: does the proposed ruling CONTRADICT the precedent "
                    "on the same kind of question?\n"
                    "Reply with EXACTLY ONE word in capitals and nothing else: "
                    "CONSISTENT or CONTRADICTS"
                )
                raw = gl.nondet.exec_prompt(prompt)
                picked = _pick(raw, ["CONSISTENT", "CONTRADICTS"])
                return picked if picked else "CONSISTENT"

            consistent = gl.eq_principle.strict_eq(judge_consistency)

        # ── Deterministic assembly ──────────────────────────
        if winner == "CLAIMANT":
            reasoning = "The panel found the claimant's position better supported."
        elif winner == "RESPONDENT":
            reasoning = "The panel found the respondent's position better supported."
        else:
            reasoning = "The panel could not establish a clear winner on the arguments given."

        flag = ""
        if consistent == "CONTRADICTS":
            flag = ("Diverges from precedent " + cited
                    + "; recorded as a distinguishing case.")
        elif consistent == "CONSISTENT":
            flag = "Consistent with precedent " + cited + " (auto-matched)."
        elif not precedent_found:
            flag = "No prior precedent on this matter; this case sets it."

        record = {
            "case_id": case_id,
            "claimant": claimant_l,
            "respondent": respondent_l,
            "summary": summary_l,
            "winner": winner,
            "reasoning": reasoning,
            "cited_case_id": cited if precedent_found else "",
            "precedent_consistency": consistent,
            "precedent_note": flag,
        }

        self.cases[case_id] = json.dumps(record)

        # Update index (count, id list, and id->summary map for future search).
        idx["count"] = new_num
        ids = idx.get("ids", [])
        if not isinstance(ids, list):
            ids = []
        ids.append(case_id)
        idx["ids"] = ids
        sums = idx.get("sums", {})
        if not isinstance(sums, dict):
            sums = {}
        sums[case_id] = summary_l
        idx["sums"] = sums
        self.index = json.dumps(idx)

        return json.dumps(record)

    @gl.public.view
    def get_case(self, case_id: str) -> str:
        try:
            raw = self.cases[_norm(case_id)]
            return raw if raw else ""
        except Exception:
            return ""

    @gl.public.view
    def list_cases(self) -> str:
        return self.index if self.index else json.dumps({"count": 0, "ids": [], "sums": {}})

    @gl.public.view
    def case_count(self) -> int:
        idx = self._load_index()
        return int(idx.get("count", 0))
