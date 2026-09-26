import type { Pet, PetEvent, PlayerProgress, Prisma } from "@prisma/client";
import { Prisma as PrismaRuntime } from "@prisma/client";
import {
  SCHEMA_VERSION,
  advanceState,
  applyCareAction,
  createInitialState,
  grantExperience,
  normalizeState,
  type CompanionState
} from "@/lib/care-engine";
import { companionProfile, isCompanionKind, type CompanionKind } from "@/lib/companions";
import { prisma } from "@/lib/db";
import type { PetCommand, PetCommandResponse, PetEventView, PetSnapshot } from "@/lib/pet-contract";
import { assertAccess, consumeCareBudget } from "@/lib/access-service";
import { isPublicDeployment } from "@/lib/deployment-config";
import { grantCareReward, type RewardLedger } from "@/lib/progression";
import { availableSlots } from "@/lib/companion-slots";
import {
  avoidRepeatedSpeechKey,
  careSpeechContext,
  chooseSpeechKey,
  renderPlayerLevel,
  renderSpeech,
  type SpeechContext
} from "@/lib/companion-speech";
import type { Locale } from "@/lib/i18n";

export class PetRequestError extends Error {
  constructor(readonly code: string, readonly status: number) { super(code); }
}

const MAX_TRANSACTION_ATTEMPTS = 5;
const HATCH_MESSAGE = "Asterion ist geschlüpft. Ein ruhiger Sternenfunke begleitet dich von nun an.";

class VersionConflict extends Error {}

function isRetryable(error: unknown) {
  return (
    error instanceof VersionConflict ||
    (error instanceof PrismaRuntime.PrismaClientKnownRequestError &&
      (error.code === "P2034" || error.code === "P2002"))
  );
}

async function serializable<T>(operation: (tx: Prisma.TransactionClient) => Promise<T>): Promise<T> {
  let lastError: unknown;

  for (let attempt = 0; attempt < MAX_TRANSACTION_ATTEMPTS; attempt += 1) {
    try {
      return await prisma.$transaction(operation, {
        isolationLevel: PrismaRuntime.TransactionIsolationLevel.Serializable,
        maxWait: 5_000,
        timeout: 10_000
      });
    } catch (error) {
      lastError = error;
      if (!isRetryable(error) || attempt === MAX_TRANSACTION_ATTEMPTS - 1) throw error;
    }
  }

  throw lastError;
}

function petToState(pet: Pet): CompanionState {
  return {
    schemaVersion: SCHEMA_VERSION,
    createdAt: pet.bornAt.getTime(),
    lastUpdatedAt: pet.lastAdvancedAt.getTime(),
    stats: {
      satiety: pet.satiety,
      energy: pet.energy,
      joy: pet.joy,
      bond: pet.bond
    },
    sleeping: pet.sleeping,
    level: pet.level,
    xp: pet.xp,
    interactions: pet.interactions,
    journal: []
  };
}

function stateUpdate(state: CompanionState) {
  return {
    bornAt: new Date(state.createdAt),
    lastAdvancedAt: new Date(state.lastUpdatedAt),
    satiety: state.stats.satiety,
    energy: state.stats.energy,
    joy: state.stats.joy,
    bond: state.stats.bond,
    sleeping: state.sleeping,
    level: state.level,
    xp: state.xp,
    interactions: state.interactions,
    version: { increment: 1 }
  };
}

function localizedEventMessage(event: PetEvent, locale: Locale): string {
  const raw = event.messageParams;
  const params = raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
  const level = typeof params.level === "number" ? params.level : undefined;
  const main = renderSpeech(event.messageKey, locale, { level });
  if (!main) return event.message; // Pre-v1 entries retain their original German text.
  const additions = [
    typeof params.petLevel === "number"
      ? renderSpeech(chooseSpeechKey(companionProfile(event.messageKey?.split(".")[1]).kind, "levelUp", event.requestId + ":pet"), locale, { level: params.petLevel })
      : null,
    typeof params.playerLevel === "number" ? renderPlayerLevel(locale, params.playerLevel) : null
  ].filter((part): part is string => Boolean(part));
  return [main, ...additions].join(" ");
}

function eventView(event: PetEvent, locale: Locale): PetEventView {
  return {
    id: event.id,
    action: event.action,
    message: localizedEventMessage(event, locale),
    localized: Boolean(renderSpeech(event.messageKey, locale)),
    animation: event.animation,
    accepted: event.accepted,
    xpAwarded: event.xpAwarded,
    occurredAt: event.occurredAt.toISOString()
  };
}

function snapshot(pet: Pet, progress: PlayerProgress, events: PetEvent[], locale: Locale, returnedAfterAbsence = false): PetSnapshot {
  const state = petToState(pet);
  return {
    ...state,
    id: pet.id,
    kind: isCompanionKind(pet.kind) ? pet.kind : "asterion",
    version: pet.version,
    playerLevel: progress.level,
    playerXp: progress.xp,
    returnedAfterAbsence,
    journal: events.map((event) => ({
      id: event.id,
      at: event.occurredAt.getTime(),
      text: localizedEventMessage(event, locale),
      action: event.action,
      localized: Boolean(renderSpeech(event.messageKey, locale))
    }))
  };
}

async function ensurePlayerProgress(tx: Prisma.TransactionClient, ownerId: string, pet: Pet) {
  const existing = await tx.playerProgress.findUnique({ where: { userId: ownerId } });
  if (existing) return existing;
  // Existing users retain their pet's current progress even if creation races a migration.
  return tx.playerProgress.create({ data: { userId: ownerId, level: pet.level, xp: pet.xp } });
}

function rewardLedger(progress: PlayerProgress): RewardLedger {
  return {
    rewardDay: progress.rewardDay,
    earnedToday: progress.earnedToday,
    lastFeedRewardAt: progress.lastFeedRewardAt?.getTime() ?? null,
    lastPlayRewardAt: progress.lastPlayRewardAt?.getTime() ?? null,
    lastPetRewardAt: progress.lastPetRewardAt?.getTime() ?? null
  };
}

function ledgerUpdate(ledger: RewardLedger) {
  return {
    rewardDay: ledger.rewardDay,
    earnedToday: ledger.earnedToday,
    lastFeedRewardAt: ledger.lastFeedRewardAt === null ? null : new Date(ledger.lastFeedRewardAt),
    lastPlayRewardAt: ledger.lastPlayRewardAt === null ? null : new Date(ledger.lastPlayRewardAt),
    lastPetRewardAt: ledger.lastPetRewardAt === null ? null : new Date(ledger.lastPetRewardAt)
  };
}

async function eventsForPet(tx: Prisma.TransactionClient, petId: string) {
  return tx.petEvent.findMany({
    where: { petId },
    orderBy: { occurredAt: "desc" },
    take: 10
  });
}

async function ensurePet(tx: Prisma.TransactionClient, ownerId: string, now: Date, chosenKind?: CompanionKind) {
  const existing = await tx.pet.findFirst({ where: { ownerId }, orderBy: [{ createdAt: "asc" }, { id: "asc" }] });
  if (existing) return existing;
  if (isPublicDeployment() && !chosenKind) throw new PetRequestError("companion_selection_required", 409);

  const pet = await tx.pet.create({
    data: {
      ownerId,
      kind: chosenKind ?? "asterion",
      bornAt: now,
      lastAdvancedAt: now
    }
  });

  await tx.petEvent.create({
    data: {
      petId: pet.id,
      ownerId,
      requestId: "system:hatch",
      action: "hatch",
      message: renderSpeech(chooseSpeechKey(companionProfile(pet.kind).kind, "adoption", pet.id), "de") ?? HATCH_MESSAGE,
      messageKey: chooseSpeechKey(companionProfile(pet.kind).kind, "adoption", pet.id),
      animation: "waving",
      occurredAt: now
    }
  });

  return pet;
}

export async function hasPet(ownerId: string): Promise<boolean> {
  return Boolean(await prisma.pet.findFirst({ where: { ownerId }, select: { id: true } }));
}

/** First choice is idempotent: another tab cannot replace an existing companion. */
export async function chooseFirstPet(ownerId: string, kind: CompanionKind, locale: Locale = "de"): Promise<PetSnapshot> {
  if (!isCompanionKind(kind)) throw new PetRequestError("invalid_companion", 400);
  return serializable(async (tx) => {
    if (isPublicDeployment()) await assertAccess(tx, ownerId);
    const pet = await ensurePet(tx, ownerId, new Date(), kind);
    const progress = await ensurePlayerProgress(tx, ownerId, pet);
    if (!progress.activePetId) await tx.playerProgress.update({ where: { userId: ownerId }, data: { activePetId: pet.id } });
    return snapshot(pet, progress, await eventsForPet(tx, pet.id), locale);
  });
}

export type CompanionSummary = Pick<Pet, "id" | "kind" | "level" | "xp" | "sleeping" | "satiety" | "energy" | "joy" | "bond">;

/** Every adoption uses the same account-level serializable transaction and a durable request ID. */
export async function adoptAdditionalPet(ownerId: string, kind: CompanionKind, requestId: string, locale: Locale = "de"): Promise<PetSnapshot> {
  if (!isCompanionKind(kind)) throw new PetRequestError("invalid_companion", 400);
  return serializable(async (tx) => {
    if (isPublicDeployment()) await assertAccess(tx, ownerId);
    const first = await tx.pet.findFirst({ where: { ownerId }, orderBy: [{ createdAt: "asc" }, { id: "asc" }] });
    if (!first) throw new PetRequestError("first_companion_required", 409);
    const progress = await ensurePlayerProgress(tx, ownerId, first);
    const prior = await tx.pet.findUnique({ where: { ownerId_adoptionRequestId: { ownerId, adoptionRequestId: requestId } } });
    if (prior) {
      if (prior.kind !== kind) throw new PetRequestError("adoption_request_changed", 409);
      return snapshot(prior, progress, await eventsForPet(tx, prior.id), locale);
    }
    const count = await tx.pet.count({ where: { ownerId } });
    const slots = availableSlots(progress.level, progress.unlockedSlots);
    if (count >= slots) throw new PetRequestError("companion_slots_full", 409);
    if (await tx.pet.findUnique({ where: { ownerId_kind: { ownerId, kind } } })) {
      throw new PetRequestError("companion_kind_owned", 409);
    }
    const now = new Date();
    const pet = await tx.pet.create({ data: { ownerId, kind, adoptionRequestId: requestId, bornAt: now, lastAdvancedAt: now } });
    const adoptionKey = chooseSpeechKey(kind, "adoption", pet.id);
    await tx.petEvent.create({ data: {
      petId: pet.id, ownerId, requestId: `system:hatch:${pet.id}`, action: "hatch",
      message: renderSpeech(adoptionKey, "de") ?? HATCH_MESSAGE,
      messageKey: adoptionKey,
      animation: "waving", occurredAt: now
    } });
    await tx.playerProgress.update({ where: { userId: ownerId }, data: { unlockedSlots: slots, activePetId: pet.id } });
    return snapshot(pet, progress, await eventsForPet(tx, pet.id), locale);
  });
}

export async function getPetCollection(ownerId: string) {
  return serializable(async (tx) => {
    if (isPublicDeployment()) await assertAccess(tx, ownerId);
    const pets = await tx.pet.findMany({ where: { ownerId }, orderBy: [{ createdAt: "asc" }, { id: "asc" }] });
    if (pets.length === 0) return { pets: [] as CompanionSummary[], activePetId: null as string | null, unlockedSlots: 1, playerLevel: 1 };
    const progress = await ensurePlayerProgress(tx, ownerId, pets[0]);
    const slots = availableSlots(progress.level, progress.unlockedSlots);
    const activePetId = pets.some((pet) => pet.id === progress.activePetId) ? progress.activePetId : pets[0].id;
    if (progress.unlockedSlots < slots || progress.activePetId !== activePetId) {
      await tx.playerProgress.update({ where: { userId: ownerId }, data: { unlockedSlots: slots, activePetId } });
    }
    const now = Date.now();
    return {
      pets: pets.map((pet) => {
        const advanced = advanceState(petToState(pet), now, companionProfile(pet.kind).kind);
        return { id: pet.id, kind: pet.kind, level: pet.level, xp: pet.xp, sleeping: pet.sleeping,
          satiety: advanced.stats.satiety, energy: advanced.stats.energy, joy: advanced.stats.joy, bond: advanced.stats.bond };
      }),
      activePetId, unlockedSlots: slots, playerLevel: progress.level
    };
  });
}

export async function selectOwnedPet(ownerId: string, petId: string): Promise<void> {
  await serializable(async (tx) => {
    if (isPublicDeployment()) await assertAccess(tx, ownerId);
    const pet = await tx.pet.findFirst({ where: { id: petId, ownerId } });
    if (!pet) throw new PetRequestError("companion_not_owned", 404);
    await ensurePlayerProgress(tx, ownerId, pet);
    await tx.playerProgress.update({ where: { userId: ownerId }, data: { activePetId: petId } });
  });
}

async function persistState(
  tx: Prisma.TransactionClient,
  pet: Pet,
  state: CompanionState,
  kind?: CompanionKind
) {
  const updated = await tx.pet.updateMany({
    where: { id: pet.id, version: pet.version },
    data: { ...stateUpdate(state), ...(kind ? { kind } : {}) }
  });

  if (updated.count !== 1) throw new VersionConflict("Companion changed on another node.");

  const persisted = await tx.pet.findUnique({ where: { id: pet.id } });
  if (!persisted) throw new Error("Companion disappeared while saving.");
  return persisted;
}

export async function getPetSnapshot(ownerId: string, locale: Locale = "de"): Promise<PetSnapshot> {
  return serializable(async (tx) => {
    if (isPublicDeployment()) await assertAccess(tx, ownerId);
    const now = new Date();
    const first = await ensurePet(tx, ownerId, now);
    const progress = await ensurePlayerProgress(tx, ownerId, first);
    const pet = progress.activePetId
      ? await tx.pet.findFirst({ where: { id: progress.activePetId, ownerId } }) ?? first
      : first;
    const returnedAfterAbsence = now.getTime() - pet.lastAdvancedAt.getTime() >= 6 * 60 * 60 * 1000;
    const advanced = advanceState(petToState(pet), now.getTime(), companionProfile(pet.kind).kind);
    const persisted = await persistState(tx, pet, advanced);
    const events = await eventsForPet(tx, pet.id);
    return snapshot(persisted, progress, events, locale, returnedAfterAbsence);
  });
}

export async function performPetCommand(ownerId: string, command: PetCommand, expectedPetId?: string, locale: Locale = "de"): Promise<PetCommandResponse> {
  return serializable(async (tx) => {
    if (isPublicDeployment()) {
      await assertAccess(tx, ownerId);
      if (command.action === "restore") throw new PetRequestError("restore_not_available", 403);
      if (command.action === "reset" || command.action === "select") throw new PetRequestError("companion_permanent", 403);
    }
    const now = new Date();
    if (!expectedPetId) throw new PetRequestError("companion_context_changed", 409);
    let pet = await tx.pet.findFirst({ where: { id: expectedPetId, ownerId } });
    if (!pet) throw new PetRequestError("companion_context_changed", 409);
    let progress = await ensurePlayerProgress(tx, ownerId, pet);
    const prior = await tx.petEvent.findUnique({
      where: { ownerId_requestId: { ownerId, requestId: command.requestId } }
    });

    if (prior) {
      if (prior.petId !== pet.id || prior.action !== command.action) throw new PetRequestError("companion_context_changed", 409);
      const events = await eventsForPet(tx, pet.id);
      return { pet: snapshot(pet, progress, events, locale), feedback: eventView(prior, locale), replayed: true };
    }

    // The actor lock serializes this database-backed limit across web nodes.
    if (isPublicDeployment()) {
      if (!await consumeCareBudget(tx, ownerId, now)) throw new PetRequestError("too_many_actions", 429);
    }

    let state = advanceState(petToState(pet), now.getTime(), companionProfile(pet.kind).kind);
    let message: string;
    let animation: string;
    let accepted = true;
    let xpAwarded = 0;
    let nextKind: CompanionKind | undefined;
    let speechContext: SpeechContext | undefined;
    let petLevel: number | undefined;
    let playerLevel: number | undefined;
    const currentCompanion = companionProfile(pet.kind);

    if (command.action === "select") {
      const selected = companionProfile(command.kind);
      nextKind = selected.kind;
      message = command.kind === currentCompanion.kind
        ? `${selected.name} bleibt an deiner Seite.`
        : `${selected.name} begleitet dich jetzt. Eure gemeinsamen Werte und Erinnerungen bleiben erhalten.`;
      animation = "waving";
    } else if (command.action === "reset") {
      state = createInitialState(now.getTime(), currentCompanion.name);
      message = `Ein neuer Sternenfunke ist erwacht. ${currentCompanion.name} beginnt eine neue Chronik mit dir.`;
      animation = "waving";
      await tx.petEvent.deleteMany({ where: { petId: pet.id } });
    } else if (command.action === "restore") {
      state = normalizeState(command.state, now.getTime());
      state.lastUpdatedAt = now.getTime();
      message = `${currentCompanion.name} erinnert sich wieder an eure gemeinsame Zeit.`;
      animation = "waving";
    } else {
      const result = applyCareAction(state, command.action, now.getTime(), currentCompanion.name, currentCompanion.kind);
      state = result.state;
      message = result.message;
      animation = result.animation;
      accepted = result.accepted;
      speechContext = careSpeechContext(command.action, accepted, state.sleeping);
      if (accepted) {
        const reward = grantCareReward(rewardLedger(progress), command.action, result.rewardCandidate, now.getTime());
        xpAwarded = reward.xp;
        if (xpAwarded > 0) {
          const petLeveled = grantExperience(state, xpAwarded);
          const playerValues = { level: progress.level, xp: progress.xp };
          const playerLeveled = grantExperience(playerValues, xpAwarded);
          if (petLeveled) {
            state.stats.bond = Math.min(100, state.stats.bond + 5);
            message += ` Eure Bindung erreicht Stufe ${state.level}.`;
            petLevel = state.level;
          }
          if (playerLeveled) {
            message += ` Du erreichst Stufe ${playerValues.level}.`;
            playerLevel = playerValues.level;
          }
          progress = await tx.playerProgress.update({
            where: { userId: ownerId },
            data: { ...ledgerUpdate(reward.ledger), level: playerValues.level, xp: playerValues.xp,
              unlockedSlots: availableSlots(playerValues.level, progress.unlockedSlots) }
          });
        }
      }
    }

    if (nextKind && nextKind !== pet.kind && await tx.pet.findUnique({ where: { ownerId_kind: { ownerId, kind: nextKind } } })) {
      throw new PetRequestError("companion_kind_owned", 409);
    }
    let messageKey: string | null = null;
    if (speechContext) {
      const preferred = chooseSpeechKey(currentCompanion.kind, speechContext, `${pet.id}:${command.requestId}`);
      const latest = await tx.petEvent.findFirst({
        where: { petId: pet.id }, orderBy: [{ occurredAt: "desc" }, { id: "desc" }], select: { messageKey: true }
      });
      messageKey = avoidRepeatedSpeechKey(preferred, latest?.messageKey);
      const main = renderSpeech(messageKey, "de");
      if (main) {
        const levelCopy = petLevel
          ? renderSpeech(chooseSpeechKey(currentCompanion.kind, "levelUp", command.requestId + ":pet"), "de", { level: petLevel })
          : null;
        message = [main, levelCopy, playerLevel ? renderPlayerLevel("de", playerLevel) : null].filter(Boolean).join(" ");
      }
    }
    pet = await persistState(tx, pet, state, nextKind);
    const event = await tx.petEvent.create({
      data: {
        petId: pet.id,
        ownerId,
        requestId: command.requestId,
        action: command.action,
        message,
        messageKey,
        messageParams: messageKey ? { ...(petLevel ? { petLevel } : {}), ...(playerLevel ? { playerLevel } : {}) } : undefined,
        animation,
        accepted,
        xpAwarded,
        occurredAt: now
      }
    });
    const events = await eventsForPet(tx, pet.id);

    return { pet: snapshot(pet, progress, events, locale), feedback: eventView(event, locale), replayed: false };
  });
}
