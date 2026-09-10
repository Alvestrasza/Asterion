import type { Pet, PetEvent, Prisma } from "@prisma/client";
import { Prisma as PrismaRuntime } from "@prisma/client";
import {
  SCHEMA_VERSION,
  advanceState,
  applyCareAction,
  createInitialState,
  normalizeState,
  type CompanionState
} from "@/lib/care-engine";
import { companionProfile, isCompanionKind, type CompanionKind } from "@/lib/companions";
import { prisma } from "@/lib/db";
import type { PetCommand, PetCommandResponse, PetEventView, PetSnapshot } from "@/lib/pet-contract";
import { assertAccess, consumeCareBudget } from "@/lib/access-service";
import { isPublicDeployment } from "@/lib/deployment-config";

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

function eventView(event: PetEvent): PetEventView {
  return {
    id: event.id,
    action: event.action,
    message: event.message,
    animation: event.animation,
    accepted: event.accepted,
    occurredAt: event.occurredAt.toISOString()
  };
}

function snapshot(pet: Pet, events: PetEvent[]): PetSnapshot {
  const state = petToState(pet);
  return {
    ...state,
    id: pet.id,
    kind: isCompanionKind(pet.kind) ? pet.kind : "asterion",
    version: pet.version,
    journal: events.map((event) => ({
      id: event.id,
      at: event.occurredAt.getTime(),
      text: event.message,
      action: event.action
    }))
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
  const existing = await tx.pet.findUnique({ where: { ownerId } });
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
      requestId: "system:hatch",
      action: "hatch",
      message: chosenKind ? `${companionProfile(chosenKind).name} ist jetzt dein Sternenfreund.` : HATCH_MESSAGE,
      animation: "waving",
      occurredAt: now
    }
  });

  return pet;
}

export async function hasPet(ownerId: string): Promise<boolean> {
  return Boolean(await prisma.pet.findUnique({ where: { ownerId }, select: { id: true } }));
}

/** First choice is idempotent: another tab cannot replace an existing companion. */
export async function chooseFirstPet(ownerId: string, kind: CompanionKind): Promise<PetSnapshot> {
  if (!isCompanionKind(kind)) throw new PetRequestError("invalid_companion", 400);
  return serializable(async (tx) => {
    if (isPublicDeployment()) await assertAccess(tx, ownerId);
    const pet = await ensurePet(tx, ownerId, new Date(), kind);
    return snapshot(pet, await eventsForPet(tx, pet.id));
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

export async function getPetSnapshot(ownerId: string): Promise<PetSnapshot> {
  return serializable(async (tx) => {
    if (isPublicDeployment()) await assertAccess(tx, ownerId);
    const now = new Date();
    const pet = await ensurePet(tx, ownerId, now);
    const advanced = advanceState(petToState(pet), now.getTime());
    const persisted = await persistState(tx, pet, advanced);
    const events = await eventsForPet(tx, pet.id);
    return snapshot(persisted, events);
  });
}

export async function performPetCommand(ownerId: string, command: PetCommand, expectedPetId?: string): Promise<PetCommandResponse> {
  return serializable(async (tx) => {
    if (isPublicDeployment()) {
      await assertAccess(tx, ownerId);
      if (command.action === "restore") throw new PetRequestError("restore_not_available", 403);
    }
    const now = new Date();
    let pet = await ensurePet(tx, ownerId, now);
    if (!expectedPetId || pet.id !== expectedPetId) throw new PetRequestError("companion_context_changed", 409);
    const prior = await tx.petEvent.findUnique({
      where: { petId_requestId: { petId: pet.id, requestId: command.requestId } }
    });

    if (prior) {
      const events = await eventsForPet(tx, pet.id);
      return { pet: snapshot(pet, events), feedback: eventView(prior), replayed: true };
    }

    // The actor lock serializes this database-backed limit across web nodes.
    if (isPublicDeployment()) {
      if (!await consumeCareBudget(tx, ownerId, now)) throw new PetRequestError("too_many_actions", 429);
    }

    let state = advanceState(petToState(pet), now.getTime());
    let message: string;
    let animation: string;
    let accepted = true;
    let nextKind: CompanionKind | undefined;
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
      const result = applyCareAction(state, command.action, now.getTime(), currentCompanion.name);
      state = result.state;
      message = result.message;
      animation = result.animation;
      accepted = result.accepted;
    }

    pet = await persistState(tx, pet, state, nextKind);
    const event = await tx.petEvent.create({
      data: {
        petId: pet.id,
        requestId: command.requestId,
        action: command.action,
        message,
        animation,
        accepted,
        occurredAt: now
      }
    });
    const events = await eventsForPet(tx, pet.id);

    return { pet: snapshot(pet, events), feedback: eventView(event), replayed: false };
  });
}
