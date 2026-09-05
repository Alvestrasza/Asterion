import { cache } from "react";
import { cookies, headers } from "next/headers";
import { LANGUAGE_COOKIE, resolveLocale } from "@/lib/i18n";

export const getRequestLocale = cache(async () => {
  const [cookieStore, requestHeaders] = await Promise.all([cookies(), headers()]);
  return resolveLocale(cookieStore.get(LANGUAGE_COOKIE)?.value, requestHeaders.get("accept-language"));
});
