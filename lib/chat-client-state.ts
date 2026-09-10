import type { ChatEnvelope } from "./chat-crypto";
export type DisplayMessage = { id: string; sequence: string; senderId: string; text: string };
export type StoredEnvelope = ChatEnvelope & { sequence: string; createdAt: string };

/** A latest page with no overlap cannot be joined to an older window without losing pagination access to the gap. */
export function hasChatHistoryGap(previous: DisplayMessage[], incoming: DisplayMessage[], hasMore: boolean): boolean {
  if (!hasMore || !previous.length || !incoming.length) return false;
  const newest = previous.reduce((value, message) => BigInt(message.sequence) > value ? BigInt(message.sequence) : value, 0n);
  const oldest = incoming.reduce((value, message) => BigInt(message.sequence) < value ? BigInt(message.sequence) : value, BigInt(incoming[0].sequence));
  return newest < oldest;
}

export function mergeChatMessages(previous: DisplayMessage[], incoming: DisplayMessage[]): DisplayMessage[] {
  const messages = new Map(previous.map(message => [message.id, message]));
  for (const message of incoming) {
    if (!/^[1-9][0-9]{0,18}$/.test(message.sequence) || BigInt(message.sequence) > 9223372036854775807n) throw new Error("invalid_message");
    const existing = messages.get(message.id);
    if (existing && (existing.sequence !== message.sequence || existing.senderId !== message.senderId || existing.text !== message.text)) throw new Error("message_conflict");
    messages.set(message.id, message);
  }
  return [...messages.values()].sort((a, b) => BigInt(a.sequence) < BigInt(b.sequence) ? -1 : 1).slice(-200);
}

/** Only already authenticated and decrypted incoming messages may advance the read cursor. */
export function lastReceivedMessage(messages: DisplayMessage[], actorId: string): DisplayMessage | undefined {
  return messages.filter(message => message.senderId !== actorId).reduce<DisplayMessage | undefined>((last, message) =>
    !last || BigInt(message.sequence) > BigInt(last.sequence) ? message : last, undefined);
}
