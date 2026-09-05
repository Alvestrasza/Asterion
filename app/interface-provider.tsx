"use client";

import { createContext, useContext } from "react";
import type { Locale } from "@/lib/i18n";
import type { Messages } from "@/lib/messages";

type InterfaceContext = { locale: Locale; errors: Messages["errors"] };
const Context = createContext<InterfaceContext | null>(null);

export function InterfaceProvider({ value, children }: { value: InterfaceContext; children: React.ReactNode }) {
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useInterface() {
  const context = useContext(Context);
  if (!context) throw new Error("InterfaceProvider is required.");
  return context;
}
