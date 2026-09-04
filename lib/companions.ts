export const COMPANION_KINDS = [
  "asterion",
  "rabbit",
  "cat",
  "orc",
  "pony",
  "fairy",
  "dog",
  "elf"
] as const;

export type CompanionKind = (typeof COMPANION_KINDS)[number];

export type CompanionProfile = {
  kind: CompanionKind;
  name: string;
  species: string;
  tagline: string;
  introduction: string;
  ariaLabel: string;
  stillAsset: string;
  animated: boolean;
};

export const COMPANIONS: Record<CompanionKind, CompanionProfile> = {
  asterion: {
    kind: "asterion",
    name: "Asterion",
    species: "Sternendrache",
    tagline: "Der kleine Hüter der Zeit",
    introduction: "Ein ruhiger Stern bleibt bei dir.",
    ariaLabel: "Asterion, ein kleiner goldener und azurblauer Sternendrache",
    stillAsset: "/assets/companions/asterion.png",
    animated: true
  },
  rabbit: {
    kind: "rabbit",
    name: "Liora",
    species: "Sternenkaninchen",
    tagline: "Die sanfte Finderin der Lichtpfade",
    introduction: "Leise Pfoten finden selbst im Dunkel einen Weg.",
    ariaLabel: "Liora, ein kleines mondfarbenes und lavendelfarbenes Sternenkaninchen",
    stillAsset: "/assets/companions/rabbit.png",
    animated: false
  },
  cat: {
    kind: "cat",
    name: "Nyra",
    species: "Sternenkatze",
    tagline: "Die wachsame Sammlerin stiller Momente",
    introduction: "Wo Nyra sich niederlässt, fühlt sich die Nacht geborgen an.",
    ariaLabel: "Nyra, eine kleine anthrazitfarbene Sternenkatze mit grünen Augen",
    stillAsset: "/assets/companions/cat.png",
    animated: false
  },
  orc: {
    kind: "orc",
    name: "Brumo",
    species: "Junger Ork",
    tagline: "Der gutherzige Wächter des Sternenfeuers",
    introduction: "Ein großes Herz braucht keine laute Stimme.",
    ariaLabel: "Brumo, ein junger freundlicher Ork in auberginefarbener und bronzener Rüstung",
    stillAsset: "/assets/companions/orc.png",
    animated: false
  },
  pony: {
    kind: "pony",
    name: "Caelo",
    species: "Sternenpony",
    tagline: "Der mutige Läufer zwischen den Wolken",
    introduction: "Wo Caelo seine Hufe setzt, wird der Himmel ein wenig weiter.",
    ariaLabel: "Caelo, ein kleines weißes Sternenpony mit himmelblauer Mähne",
    stillAsset: "/assets/companions/pony.png",
    animated: false
  },
  fairy: {
    kind: "fairy",
    name: "Selya",
    species: "Lichtfee",
    tagline: "Die heitere Hüterin kleiner Wunder",
    introduction: "Selya erinnert dich daran, dass selbst leises Licht den Weg findet.",
    ariaLabel: "Selya, eine kleine Lichtfee mit rosafarbenem Haar und zarten Flügeln",
    stillAsset: "/assets/companions/fairy.png",
    animated: false
  },
  dog: {
    kind: "dog",
    name: "Fenn",
    species: "Sternenhund",
    tagline: "Der treue Wächter deiner Wege",
    introduction: "Fenn bleibt an deiner Seite, ganz gleich wohin der Tag euch führt.",
    ariaLabel: "Fenn, ein kleiner karamellfarbener Sternenhund mit blauen Augen",
    stillAsset: "/assets/companions/dog.png",
    animated: false
  },
  elf: {
    kind: "elf",
    name: "Aelira",
    species: "Waldelfe",
    tagline: "Die stille Bewahrerin des grünen Pfades",
    introduction: "Aelira hört selbst das, was der Wald nur im Flüstern erzählt.",
    ariaLabel: "Aelira, eine junge Waldelfe mit grünem Haar und amethystfarbenen Augen",
    stillAsset: "/assets/companions/elf.png",
    animated: false
  }
};

export function isCompanionKind(value: unknown): value is CompanionKind {
  return typeof value === "string" && COMPANION_KINDS.includes(value as CompanionKind);
}

export function companionProfile(value: unknown): CompanionProfile {
  return COMPANIONS[isCompanionKind(value) ? value : "asterion"];
}

export function companionAnimationAsset(kind: CompanionKind, animation: string, reducedMotion: boolean) {
  const companion = COMPANIONS[kind];
  if (!companion.animated || reducedMotion) return companion.stillAsset;
  return `/assets/animations/${animation}.gif`;
}
