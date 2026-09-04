import Image from "next/image";
import { redirect } from "next/navigation";
import { auth, signIn } from "@/auth";
import { isInternalTestMode } from "@/lib/current-actor";

export const dynamic = "force-dynamic";

export default async function LoginPage() {
  if (isInternalTestMode()) redirect("/");

  const session = await auth();
  if (session?.user?.id) redirect("/");

  return (
    <main className="login-shell">
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-orbit" aria-hidden="true" />
        <Image
          className="login-asterion"
          src="/assets/animations/idle.gif"
          width={192}
          height={208}
          alt="Asterion, ein kleiner goldener und azurblauer Sternendrache"
          unoptimized
          priority
        />
        <p className="eyebrow">DEIN HÜTER DER ZEIT</p>
        <h1 id="login-title">Asterion wartet auf dich.</h1>
        <p>
          Melde dich an, damit eure gemeinsame Chronik sicher gespeichert wird und Asterion dich auf jedem Gerät wiedererkennt.
        </p>
        <form
          action={async () => {
            "use server";
            await signIn("keycloak", { redirectTo: "/" });
          }}
        >
          <button className="login-button" type="submit">Bei Asterion anmelden</button>
        </form>
      </section>
    </main>
  );
}
