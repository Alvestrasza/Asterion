export function hasSameOrigin(request: Request) {
  const origin = request.headers.get("origin");
  if (!origin) return false;

  try {
    const originHost = new URL(origin).host.toLowerCase();
    const forwardedHost = request.headers.get("x-forwarded-host")?.split(",")[0]?.trim().toLowerCase();
    const host = request.headers.get("host")?.toLowerCase();
    return originHost === forwardedHost || originHost === host;
  } catch {
    return false;
  }
}
