/**
 * Cross-language parity: every canonical hard reject must also block approval.
 *
 * apply_avatar_qa_rejection_logic (Python) decides what a hard reject is.
 * avatarApprovalBlockReason (here) is the last server-side authority before a
 * face becomes the user's public profile. PR #110 closed the gap for four
 * status fields and the watermark action, but the Python function rejects on
 * twelve conditions, and the remaining seven -- childlikeRisk, identifiabilityRisk,
 * uniqueMarkCopyRisk, beautificationRisk, cropIsolationQuality,
 * backgroundLeakageRisk, secondaryFaceLeakageRisk -- were never checked here.
 *
 * The premise of every case below is deliberately a *contradictory* document:
 *
 *     previewAllowed = true
 *     rejectReasons  = []
 *     <one canonical hard-reject field set>
 *
 * A healthy worker never emits that -- it would have written the rejectReason
 * and flipped previewAllowed. Which is the point: defence in depth is for the
 * document that arrives from a partial write, a migration, an admin repair, a
 * schema drift, or a future producer regression. "The worker does not produce
 * it" is the reason this layer exists, not a reason to skip it.
 *
 * avatarQaHardRejectContract.json is the shared statement of those conditions.
 * tests/test_avatar_qa_hard_reject_parity.py executes the real Python function
 * against the same file, so a hard reject added on either side without the
 * other fails one of the two tests rather than drifting silently.
 */

import assert from "node:assert/strict";
import test from "node:test";

import contract from "./avatarQaHardRejectContract.json";
import * as avatarApprovalModule from "./avatarApproval";

type ApprovalGate = {
  canPreviewCandidate: (
    candidate: Record<string, unknown>,
    nowMs?: number,
  ) => boolean;
  avatarApprovalBlockReason: (candidate: Record<string, unknown>) => string;
};

function gate(): ApprovalGate {
  return avatarApprovalModule as unknown as ApprovalGate;
}

function candidateWith(
  overrides: Record<string, unknown>,
): Record<string, unknown> {
  return {
    status: "preview_ready",
    jobId: "job-001",
    ownerUid: "user-001",
    qa: { ...contract.healthyQa, ...overrides },
  };
}

test("the contract fixture is not vacuous", () => {
  assert.equal(contract.schemaVersion, "avatar_qa_hard_reject_parity_v1");
  assert.ok(contract.hardRejectConditions.length >= 12);
  assert.ok(contract.softValuesThatMustNotHardReject.length >= 12);
});

test("a healthy candidate is approvable", () => {
  assert.equal(gate().avatarApprovalBlockReason(candidateWith({})), "");
  assert.equal(gate().canPreviewCandidate(candidateWith({})), true);
});

// ---------------------------------------------------------------------------
// every canonical hard reject must block approval
// ---------------------------------------------------------------------------

for (const condition of contract.hardRejectConditions) {
  test(`${condition.id} blocks approval even with previewAllowed=true and no rejectReasons`, () => {
    const candidate = candidateWith({ [condition.field]: condition.value });
    const qa = candidate.qa as Record<string, unknown>;
    assert.equal(qa.previewAllowed, true, "premise: the document contradicts itself");
    assert.deepEqual(qa.rejectReasons, [], "premise: the reject reason was lost");

    const reason = gate().avatarApprovalBlockReason(candidate);
    assert.notEqual(
      reason,
      "",
      `${condition.field}=${condition.value} must block approval ` +
        `(Python rejects it as ${condition.rejectReason})`,
    );
    assert.equal(
      gate().canPreviewCandidate(candidate),
      false,
      `${condition.id}: canPreviewCandidate must fail closed`,
    );
  });
}

// ---------------------------------------------------------------------------
// the whole risk vocabulary, not just the word "high"
// ---------------------------------------------------------------------------

test("the approval gate is deliberately at least as strict as Python on risk bands", () => {
  /**
   * Python is not uniform: childlikeRisk, identifiabilityRisk,
   * uniqueMarkCopyRisk and beautificationRisk use an exact == "high", while
   * backgroundLeakageRisk and secondaryFaceLeakageRisk go through
   * _risk_is_high, which also accepts critical/fail/failed.
   *
   * The asymmetry is latent -- those four are produced by _risk_from_score,
   * whose domain is low/medium/high, so "critical" is unreachable from the
   * worker. But this gate exists for documents the worker did not write, and
   * refusing a value that says "critical" cannot be wrong at the last
   * authority before a face goes public. So the full vocabulary applies to all
   * six, on purpose.
   */
  const riskFields = contract.hardRejectConditions
    .filter((condition) => condition.band === "risk_high")
    .map((condition) => condition.field);
  assert.equal(riskFields.length, 6);

  for (const field of riskFields) {
    for (const value of contract.riskHighVocabulary) {
      assert.notEqual(
        gate().avatarApprovalBlockReason(candidateWith({ [field]: value })),
        "",
        `${field}=${value} must block approval`,
      );
    }
  }
});

// ---------------------------------------------------------------------------
// the soft-review contract must survive intact
// ---------------------------------------------------------------------------

for (const soft of contract.softValuesThatMustNotHardReject) {
  test(`${soft.field}=${soft.value} stays approvable`, () => {
    assert.equal(
      gate().avatarApprovalBlockReason(
        candidateWith({ [soft.field]: soft.value }),
      ),
      "",
      `${soft.field}=${soft.value} is not a hard reject in Python and must not ` +
        "become one here -- medium/needs_review/review are the soft-review band",
    );
  });
}

test("the real production soft-review shape stays approvable", () => {
  /**
   * Two such candidates exist in production, one already an approved avatar:
   * requiresHumanReview=true, reviewTier=soft_review, privacyQa=needs_review,
   * identifiabilityRisk=medium, rejectReasons=[]. The 2026-09-07 product
   * contract offers these deliberately.
   */
  const softReview = candidateWith({
    requiresHumanReview: true,
    reviewTier: "soft_review",
    previewTier: "soft_review",
    offeredToUser: true,
    privacyQa: "needs_review",
    identifiabilityRisk: "medium",
    reviewReasons: [
      "actual_qa_signal_review",
      "qa_model_signal_review",
      "qa_signal_uncertain",
    ],
  });
  assert.equal(gate().avatarApprovalBlockReason(softReview), "");
  assert.equal(gate().canPreviewCandidate(softReview), true);
});

// ---------------------------------------------------------------------------
// absent fields must stay backward compatible
// ---------------------------------------------------------------------------

test("a candidate that simply omits a risk field is not blocked by its absence", () => {
  /**
   * Legacy documents predate several of these fields. Absence is not evidence
   * of danger, and treating it as such would fail closed on every historical
   * candidate. A genuine failure has to be stated.
   */
  for (const condition of contract.hardRejectConditions) {
    const qa: Record<string, unknown> = { ...contract.healthyQa };
    delete qa[condition.field];
    assert.equal(
      gate().avatarApprovalBlockReason({
        status: "preview_ready",
        jobId: "job-001",
        qa,
      }),
      "",
      `omitting ${condition.field} must not block approval by itself`,
    );
  }
});

test("an empty qa map is still blocked by previewAllowed", () => {
  assert.equal(
    gate().avatarApprovalBlockReason({ status: "preview_ready", qa: {} }),
    "qa_preview_not_allowed",
  );
});
