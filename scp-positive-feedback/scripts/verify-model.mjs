import assert from "node:assert/strict";

function clamp(n, min = 0, max = 100) {
  return Math.min(max, Math.max(min, n));
}

function deriveState(barrier, differentiation, reinvestment, momentum = 0) {
  const structure = clamp(0.55 * barrier + 0.35 * differentiation + 0.1 * momentum);
  const conduct = clamp(0.45 * structure + 0.4 * reinvestment + 0.15 * differentiation);
  const performance = clamp(0.5 * conduct + 0.25 * structure + 0.25 * reinvestment);
  const nextMomentum = clamp(momentum * 0.72 + performance * 0.28);
  return { structure, conduct, performance, momentum: nextMomentum };
}

function stepTurn(prev) {
  const feedback = (prev.performance - 50) * 0.12 + prev.momentum * 0.04;
  const barrier = clamp(prev.barrier + feedback * 0.55);
  const differentiation = clamp(prev.differentiation + feedback * 0.35);
  const reinvestment = clamp(prev.reinvestment + (prev.performance > 60 ? 1.2 : -0.6));
  const derived = deriveState(barrier, differentiation, reinvestment, prev.momentum);
  return {
    ...derived,
    barrier,
    differentiation,
    reinvestment,
    turn: prev.turn + 1,
    feedback,
  };
}

const base = {
  ...deriveState(70, 65, 80, 0),
  barrier: 70,
  differentiation: 65,
  reinvestment: 80,
  turn: 0,
};

assert.ok(base.structure > 60, "high levers should yield strong structure");
assert.ok(base.performance > 55, "high levers should yield solid performance");

let state = base;
for (let i = 0; i < 5; i += 1) {
  state = stepTurn(state);
}

assert.ok(state.momentum > base.momentum, "positive loop should raise momentum");
assert.ok(state.barrier >= base.barrier, "strong performance should not erode barriers");

const weak = {
  ...deriveState(20, 20, 15, 0),
  barrier: 20,
  differentiation: 20,
  reinvestment: 15,
  turn: 0,
};
const afterWeak = stepTurn(weak);
assert.ok(afterWeak.feedback < 0, "weak performance should produce negative feedback");

console.log("verify-model: ok");
console.log(
  JSON.stringify(
    {
      basePerformance: Math.round(base.performance),
      after5Momentum: Math.round(state.momentum),
      weakFeedback: Number(afterWeak.feedback.toFixed(2)),
    },
    null,
    2,
  ),
);
