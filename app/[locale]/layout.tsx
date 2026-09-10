import { notFound } from "next/navigation";
import { LOCALES, type Locale } from "@/lib/i18n";

export default async function LocaleLayout({ children, params }: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  if (!LOCALES.includes((await params).locale as Locale)) notFound();
  return children;
}
