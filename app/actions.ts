"use server";

import { redirect } from "next/navigation";
import { auth, signOut } from "@/auth";
import { keycloakLogoutUrl } from "@/lib/identity-policy";

export async function logout() {
  const session = await auth();
  if (!session?.user?.id) redirect("/login");
  await signOut({ redirect: false });
  redirect(keycloakLogoutUrl() ?? "/login");
}
