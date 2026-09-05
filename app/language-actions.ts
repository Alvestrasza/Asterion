"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { LANGUAGE_COOKIE, languageCookieOptions, languageReturnPath, normalizeLocale } from "@/lib/i18n";

export async function changeLanguage(formData: FormData) {
  const locale = normalizeLocale(formData.get("locale"));
  if (locale) {
    const cookieStore = await cookies();
    cookieStore.set(LANGUAGE_COOKIE, locale, languageCookieOptions(
      process.env.NODE_ENV === "production",
      process.env.ASTERION_INTERNAL_TEST_MODE?.trim().toLowerCase() === "true"
    ));
  }
  redirect(languageReturnPath(formData.get("returnTo")));
}
