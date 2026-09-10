export type DockFriend = { id: string; username: string; status: "accepted" | "incoming" | "outgoing" | "blocked"; online: boolean | null; level: number | null };

/** One request at a time; no retained social data when the document cannot be shown. */
export function createDockPolling(options: {
  actorId: string;
  request: typeof fetch;
  publish: (friends: DockFriend[], transient?: boolean) => void;
  unread?: (counts: Record<string, number>) => void;
  unavailable: () => void;
  sessionEnded: () => void;
}) {
  // Call native browser fetch without binding it to the options object.
  const request = options.request;
  let stopped = false;
  let visible = false;
  let controller: AbortController | null = null;
  let generation = 0;
  const clear = () => {
    generation++;
    controller?.abort();
    controller = null;
    options.publish([], true);
    options.unread?.({});
  };
  const endSession = () => {
    if (stopped) return;
    stopped = true;
    clear();
    options.sessionEnded();
  };
  async function refresh() {
    if (stopped || !visible || controller) return;
    const current = new AbortController();
    controller = current;
    const currentGeneration = generation;
    const deadline = setTimeout(() => current.abort(), 10_000);
    const relevant = () => !stopped && visible && generation === currentGeneration;
    try {
      const response = await request("/api/friends", {
        method: "POST", cache: "no-store", credentials: "same-origin", signal: current.signal,
        headers: { "Content-Type": "application/json", "X-Asterion-Actor": options.actorId },
        body: JSON.stringify({ action: "list" })
      });
      if (!relevant()) return;
      if ([401, 403, 409].includes(response.status)) { endSession(); return; }
      if (!response.ok) throw new Error("unavailable");
      const data = await response.json();
      if (!relevant()) return;
      if (!Array.isArray(data.friends) || data.friends.length > 200) throw new Error("invalid_response");
      const friends: DockFriend[] = data.friends.map((friend: DockFriend) => {
        if (!friend || typeof friend.id !== "string" || typeof friend.username !== "string" ||
          !["accepted", "incoming", "outgoing", "blocked"].includes(friend.status)) throw new Error("invalid_response");
        return { id: friend.id, username: friend.username, status: friend.status,
          online: friend.status === "accepted" && typeof friend.online === "boolean" ? friend.online : null,
          level: friend.status === "accepted" && Number.isInteger(friend.level) && friend.level! >= 1 && friend.level! <= 99 ? friend.level : null };
      });
      options.publish(friends);
      if (options.unread) {
        try {
          const inbox = await request("/api/chat", {
            method: "POST", cache: "no-store", credentials: "same-origin", signal: current.signal,
            headers: { "Content-Type": "application/json", "X-Asterion-Actor": options.actorId },
            body: JSON.stringify({ action: "inbox" })
          });
          if (!relevant()) return;
          if ([401, 403, 409].includes(inbox.status)) { endSession(); return; }
          if (!inbox.ok) throw new Error("unavailable");
          const data = await inbox.json();
          if (!relevant()) return;
          if (!Array.isArray(data.unread) || data.unread.length > 200) throw new Error("invalid_response");
          const accepted = new Set(friends.filter(friend => friend.status === "accepted").map(friend => friend.id));
          const counts: Record<string, number> = Object.create(null);
          for (const entry of data.unread) {
            if (entry && accepted.has(entry.friendshipId) && Number.isSafeInteger(entry.count) && entry.count > 0) counts[entry.friendshipId] = entry.count;
          }
          options.unread(counts);
        } catch { if (relevant()) options.unread({}); }
      }
    } catch {
      if (relevant()) { options.publish([], true); options.unread?.({}); options.unavailable(); }
    } finally {
      clearTimeout(deadline);
      if (controller === current) controller = null;
    }
  }
  return {
    refresh,
    setVisible(next: boolean) {
      visible = next;
      if (!next) clear();
      else void refresh();
    },
    endSession,
    dispose() { stopped = true; clear(); }
  };
}
