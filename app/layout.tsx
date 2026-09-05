import type { Metadata, Viewport } from "next";
import { getRequestLocale } from "@/lib/request-locale";
import { getMessages } from "@/lib/messages";
import { InterfaceProvider } from "./interface-provider";
import "./globals.css";
import "./public.css";

export async function generateMetadata(): Promise<Metadata> {
  const t = getMessages(await getRequestLocale());
  return {
    title: t.meta.title,
    description: t.meta.description,
    manifest: "/manifest.webmanifest",
    icons: { icon: "/assets/companions/asterion.png" }
  };
}

export const viewport: Viewport = {
  themeColor: "#0b2844",
  colorScheme: "dark"
};

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const locale = await getRequestLocale();
  const t = getMessages(locale);
  return (
    <html lang={locale}>
      <body><InterfaceProvider value={{ locale, errors: t.errors }}>{children}</InterfaceProvider></body>
    </html>
  );
}
