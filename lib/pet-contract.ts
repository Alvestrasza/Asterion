import type { CareAction, CompanionState } from "@/lib/care-engine";
import type { CompanionKind } from "@/lib/companions";

export type PetEventView = {
  id: string;
  action: string;
  message: string;
  animation: string;
  accepted: boolean;
  occurredAt: string;
};

export type PetSnapshot = Omit<CompanionState, "journal"> & {
  id: string;
  kind: CompanionKind;
  version: number;
  journal: Array<{ id: string; at: number; text: string; action: string }>;
};

export type PetCommand =
  | { requestId: string; action: CareAction }
  | { requestId: string; action: "reset" }
  | { requestId: string; action: "select"; kind: CompanionKind }
  | { requestId: string; action: "restore"; state: unknown };

export type PetCommandResponse = {
  pet: PetSnapshot;
  feedback: PetEventView;
  replayed: boolean;
};
