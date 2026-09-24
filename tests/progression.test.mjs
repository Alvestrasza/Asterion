import test from "node:test";
import assert from "node:assert/strict";

import { applyCareAction, createInitialState, grantExperience, totalXpForLevel } from "../lib/care-engine.ts";
import { DAILY_XP_LIMIT, grantCareReward, utcRewardDay } from "../lib/progression.ts";

const HOUR = 60 * 60 * 1000;
const start = Date.parse("2026-09-01T07:00:00.000Z");

function emptyLedger() {
  return { rewardDay: null, earnedToday: 0, lastFeedRewardAt: null, lastPlayRewardAt: null, lastPetRewardAt: null };
}

test("cooldowns and a UTC daily cap reject rapid and cross-midnight farming", () => {
  let ledger = emptyLedger();
  const first = grantCareReward(ledger, "pet", 16, start);
  ledger = first.ledger;
  assert.equal(first.xp, 16);
  assert.equal(grantCareReward(ledger, "pet", 16, start + 1).xp, 0);
  assert.equal(grantCareReward(ledger, "pet", 16, start - HOUR).xp, 0);
  assert.equal(grantCareReward(ledger, "sleep", 100, start + HOUR).xp, 0);
  const afterCooldown = grantCareReward(ledger, "pet", 16, start + 3 * HOUR);
  assert.equal(afterCooldown.xp, 16);
  const nearCap = { ...afterCooldown.ledger, earnedToday: 155 };
  assert.equal(grantCareReward(nearCap, "play", 23, start + 6 * HOUR).xp, 5);
  const nextDay = grantCareReward(nearCap, "pet", 16, start + 24 * HOUR);
  assert.equal(nextDay.xp, 16);
  assert.equal(nextDay.ledger.earnedToday, 16);
  assert.notEqual(nextDay.ledger.rewardDay, utcRewardDay(start));
  assert.equal(grantCareReward(nextDay.ledger, "feed", 15, start).xp, 0);
});

test("ordinary varied care reaches level five around day two and ten around week one", () => {
  let state = createInitialState(start);
  const player = { level: 1, xp: 0 };
  let ledger = emptyLedger();
  let levelFiveAt = null;
  let levelTenAt = null;
  for (let day = 0; day < 8; day += 1) {
    for (const hour of [0, 6, 12]) {
      const now = start + day * 24 * HOUR + hour * HOUR;
      if (state.sleeping) state = applyCareAction(state, "wake", now).state;
      for (const action of ["feed", "play", "pet"]) {
        const result = applyCareAction(state, action, now);
        state = result.state;
        if (!result.accepted) continue;
        const reward = grantCareReward(ledger, action, result.rewardCandidate, now);
        ledger = reward.ledger;
        grantExperience(state, reward.xp);
        grantExperience(player, reward.xp);
      }
      if (hour === 12) state = applyCareAction(state, "sleep", now + HOUR).state;
      if (state.level >= 5 && levelFiveAt === null) levelFiveAt = day + 1;
      if (state.level >= 10 && levelTenAt === null) levelTenAt = day + 1;
    }
  }
  assert.ok(levelFiveAt !== null && levelFiveAt <= 2, `level five after ${levelFiveAt} days`);
  assert.ok(levelTenAt !== null && levelTenAt <= 8 && levelTenAt >= 6, `level ten after ${levelTenAt} days; final ${state.level}/${state.xp} daily ${ledger.earnedToday}`);
  assert.equal(player.level, state.level);
  assert.ok(state.stats.energy > 20, "ordinary care should not make the pet exhausted");
  assert.ok(totalXpForLevel(99) / DAILY_XP_LIMIT > 700, "level 99 must take substantially longer");
});

test("account and pet XP diverge when caring for two companions", () => {
  const player = { level: 1, xp: 0 };
  const petOne = { level: 1, xp: 0 };
  const petTwo = { level: 1, xp: 0 };
  grantExperience(player, 80);
  grantExperience(petOne, 80);
  grantExperience(player, 80);
  grantExperience(petTwo, 80);
  assert.equal(player.level, 3);
  assert.equal(petOne.level, 2);
  assert.equal(petTwo.level, 2);
});

function simulateCare(sessionHours, days, absentDays = new Set()) {
  let state = createInitialState(start);
  let ledger = emptyLedger();
  const progress = { level: 1, xp: 0 };
  const dailyXp = [];
  for (let day = 0; day < days; day += 1) {
    if (absentDays.has(day)) {
      dailyXp.push(0);
      continue;
    }
    let awarded = 0;
    for (const hour of sessionHours) {
      const now = start + day * 24 * HOUR + hour * HOUR;
      if (state.sleeping) state = applyCareAction(state, "wake", now).state;
      for (const action of ["feed", "play", "pet"]) {
        const result = applyCareAction(state, action, now);
        state = result.state;
        if (!result.accepted) continue;
        const reward = grantCareReward(ledger, action, result.rewardCandidate, now);
        ledger = reward.ledger;
        awarded += reward.xp;
        grantExperience(state, reward.xp);
        grantExperience(progress, reward.xp);
      }
    }
    state = applyCareAction(state, "sleep", start + day * 24 * HOUR + 14 * HOUR).state;
    dailyXp.push(awarded);
  }
  return { state, progress, dailyXp };
}

test("casual, typical, intensive and absent-player simulations respect progression bounds", () => {
  const casual = simulateCare([0], 8);
  const typical = simulateCare([0, 6, 12], 8);
  const intensive = simulateCare([0, 3, 6, 9, 12], 8);
  const absent = simulateCare([0, 6, 12], 8, new Set([2, 3, 4]));

  assert.ok(casual.progress.level >= 4, `casual level ${casual.progress.level}`);
  assert.ok(typical.progress.level >= 10, `typical level ${typical.progress.level}`);
  assert.ok(intensive.progress.level >= casual.progress.level);
  assert.ok(intensive.progress.level <= typical.progress.level + 1, "extra clicks must not multiply leveling speed");
  assert.ok(absent.progress.level < typical.progress.level);
  assert.deepEqual(absent.dailyXp.slice(2, 5), [0, 0, 0]);
  for (const scenario of [casual, typical, intensive, absent]) {
    assert.ok(scenario.dailyXp.every((xp) => xp >= 0 && xp <= DAILY_XP_LIMIT));
    assert.ok(scenario.state.stats.energy > 20, `energy ${scenario.state.stats.energy}`);
  }
});
