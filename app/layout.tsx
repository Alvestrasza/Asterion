import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Asterion — Dein Sternenbegleiter",
  description: "Asterion ist ein sanfter Sternendrachen-Begleiter, der dich auf jedem Gerät wiedererkennt.",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: "/assets/animations/idle.gif"
  }
};

export const viewport: Viewport = {
  themeColor: "#0b2844",
  colorScheme: "dark"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="de">
      <body>{children}</body>
    </html>
  );
}
