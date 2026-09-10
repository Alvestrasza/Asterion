import { NextRequest, NextResponse } from "next/server";
import { LANGUAGE_COOKIE, LOCALE_HEADER, languageCookieOptions, localizedPath, pageRoute, resolveLocale } from "./lib/i18n";

export function proxy(request: NextRequest) {
  const route = pageRoute(request.nextUrl.pathname);
  const locale = route?.locale ?? resolveLocale(request.cookies.get(LANGUAGE_COOKIE)?.value, request.headers.get("accept-language"));
  const headers = new Headers(request.headers);
  // Never trust a locale header supplied by a browser or upstream proxy.
  headers.set(LOCALE_HEADER, locale);
  if (!route) return NextResponse.next({ request: { headers } });
  if (!route.locale && (request.method === "GET" || request.method === "HEAD")) {
    const url = request.nextUrl.clone();
    url.pathname = localizedPath(route.path, locale);
    const response = NextResponse.redirect(url);
    response.headers.set("Cache-Control", "private, no-store");
    response.headers.set("Vary", "Cookie, Accept-Language");
    return response;
  }
  const response = NextResponse.next({ request: { headers } });
  if (route.locale) response.cookies.set(LANGUAGE_COOKIE, locale, languageCookieOptions(
    process.env.NODE_ENV === "production", process.env.ASTERION_INTERNAL_TEST_MODE?.trim().toLowerCase() === "true"
  ));
  response.headers.set("Cache-Control", "private, no-store");
  return response;
}

export const config = {
  matcher: ["/", "/login", "/care", "/friends", "/admin", "/access", "/de/:path*", "/en/:path*", "/fr/:path*", "/es/:path*"]
};
