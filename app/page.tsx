import Image from "next/image";
import Link from "next/link";
import { COMPANIONS, COMPANION_KINDS } from "@/lib/companions";
import { getMessages } from "@/lib/messages";
import { getRequestLocale } from "@/lib/request-locale";
import { LanguageSelector } from "./language-selector";
import { version } from "@/package.json";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const locale = await getRequestLocale();
  const t = getMessages(locale);
  return (
    <div className="public-shell">
      <a className="skip-link" href="#main-content">{t.nav.skip}</a>
      <header className="public-header">
        <Link className="public-brand" href="/" aria-label={t.nav.home}><span aria-hidden="true">✦</span> Starfriends</Link>
        <nav className="public-nav" aria-label={t.nav.home}>
          <a href="#about">{t.nav.about}</a>
          <a href="#companions">{t.nav.companions}</a>
          <a href="#roadmap">{t.nav.roadmap}</a>
          <Link href="/care" prefetch={false}>{t.nav.care}</Link>
        </nav>
        <LanguageSelector locale={locale} labels={t.nav} returnTo="/" />
      </header>
      <main id="main-content">
        <section className="public-hero" aria-labelledby="hero-title">
          <div className="public-hero-copy">
            <p className="eyebrow">{t.hero.eyebrow}</p>
            <h1 id="hero-title">{t.hero.title}</h1>
            <p className="public-lead">{t.hero.description}</p>
            <div className="public-actions">
              <Link className="public-button primary" href="/login" prefetch={false}>{t.hero.primary}<span aria-hidden="true"> →</span></Link>
              <a className="public-button secondary" href="#companions">{t.hero.secondary}</a>
            </div>
            <p className="public-note">{t.hero.note}</p>
          </div>
          <figure className="public-hero-art">
            <div className="public-orbits" aria-hidden="true"><div className="public-orbit" /></div>
            <Image src={COMPANIONS.asterion.stillAsset} alt={t.companions.asterion.alt} fill
              sizes="(max-width: 760px) 90vw, 480px" priority style={{ objectFit: "contain" }} />
            <figcaption><strong>Asterion</strong><span>{t.companions.asterion.species}</span></figcaption>
          </figure>
        </section>
        <section id="about" className="public-section" aria-labelledby="about-title">
          <p className="eyebrow">{t.about.eyebrow}</p>
          <h2 id="about-title">{t.about.title}</h2>
          <p className="public-section-intro">{t.about.description}</p>
          <div className="public-feature-grid">
            <article><span aria-hidden="true">♡</span><h3>{t.about.careTitle}</h3><p>{t.about.careText}</p></article>
            <article><span aria-hidden="true">◇</span><h3>{t.about.devicesTitle}</h3><p>{t.about.devicesText}</p></article>
            <article><span aria-hidden="true">☾</span><h3>{t.about.paceTitle}</h3><p>{t.about.paceText}</p></article>
          </div>
        </section>
        <section id="companions" className="public-section" aria-labelledby="companions-title">
          <p className="eyebrow">{t.gallery.eyebrow}</p>
          <h2 id="companions-title">{t.gallery.title}</h2>
          <p className="public-section-intro">{t.gallery.description}</p>
          <div className="public-companion-grid">
            {COMPANION_KINDS.map((kind) => (
              <article className="public-companion" key={kind}>
                <div className="public-companion-art"><Image src={COMPANIONS[kind].stillAsset} alt={t.companions[kind].alt}
                  fill sizes="(max-width: 520px) 80vw, (max-width: 900px) 42vw, 240px" style={{ objectFit: "contain" }} /></div>
                <h3>{COMPANIONS[kind].name}</h3>
                <p className="public-species">{t.companions[kind].species}</p>
                <p>{t.companions[kind].description}</p>
              </article>
            ))}
          </div>
        </section>
        <section id="roadmap" className="public-section public-roadmap" aria-labelledby="roadmap-title">
          <p className="eyebrow">{t.roadmap.eyebrow}</p>
          <h2 id="roadmap-title">{t.roadmap.title}</h2>
          <p className="public-section-intro">{t.roadmap.description}</p>
          <div className="public-feature-grid">
            <article><h3>{t.roadmap.progressionTitle}</h3><p>{t.roadmap.progressionText}</p></article>
            <article><h3>{t.roadmap.diaryTitle}</h3><p>{t.roadmap.diaryText}</p></article>
            <article><h3>{t.roadmap.socialTitle}</h3><p>{t.roadmap.socialText}</p></article>
          </div>
        </section>
      </main>
      <footer className="public-footer"><p>✦ {t.footer.tagline}</p><p>{t.footer.status} · v{version}</p></footer>
    </div>
  );
}
