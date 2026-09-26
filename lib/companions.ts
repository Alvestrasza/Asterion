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

export const CARE_PROFILE_VERSION = 1;

export type CompanionCareProfile = {
  awakeSatietyPerHour: number;
  awakeEnergyPerHour: number;
  awakeJoyPerHour: number;
  sleepSatietyPerHour: number;
  sleepJoyPerHour: number;
  sleepEnergyPerHour: number;
  feedSatietyGain: number;
  playJoyGain: number;
  petBondGain: number;
};

export type CompanionProfile = {
  kind: CompanionKind;
  name: string;
  species: string;
  tagline: string;
  introduction: string;
  ariaLabel: string;
  stillAsset: string;
  animated: boolean;
  care: CompanionCareProfile;
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
    animated: true,
    care: { awakeSatietyPerHour: 1.35, awakeEnergyPerHour: 0.45, awakeJoyPerHour: 0.4, sleepSatietyPerHour: 0.75, sleepJoyPerHour: 0.1, sleepEnergyPerHour: 9, feedSatietyGain: 22, playJoyGain: 12, petBondGain: 2.8 }
  },
  rabbit: {
    kind: "rabbit",
    name: "Liora",
    species: "Sternenkaninchen",
    tagline: "Die sanfte Finderin der Lichtpfade",
    introduction: "Leise Pfoten finden selbst im Dunkel einen Weg.",
    ariaLabel: "Liora, ein kleines mondfarbenes und lavendelfarbenes Sternenkaninchen",
    stillAsset: "/assets/companions/rabbit.png",
    animated: false,
    care: { awakeSatietyPerHour: 1.45, awakeEnergyPerHour: 0.4, awakeJoyPerHour: 0.32, sleepSatietyPerHour: 0.8, sleepJoyPerHour: 0.1, sleepEnergyPerHour: 9.5, feedSatietyGain: 23, playJoyGain: 11, petBondGain: 3.1 }
  },
  cat: {
    kind: "cat",
    name: "Nyra",
    species: "Sternenkatze",
    tagline: "Die wachsame Sammlerin stiller Momente",
    introduction: "Wo Nyra sich niederlässt, fühlt sich die Nacht geborgen an.",
    ariaLabel: "Nyra, eine kleine anthrazitfarbene Sternenkatze mit grünen Augen",
    stillAsset: "/assets/companions/cat.png",
    animated: false,
    care: { awakeSatietyPerHour: 1.25, awakeEnergyPerHour: 0.4, awakeJoyPerHour: 0.34, sleepSatietyPerHour: 0.7, sleepJoyPerHour: 0.08, sleepEnergyPerHour: 9, feedSatietyGain: 21, playJoyGain: 14, petBondGain: 2.2 }
  },
  orc: {
    kind: "orc",
    name: "Brumo",
    species: "Junger Ork",
    tagline: "Der gutherzige Wächter des Sternenfeuers",
    introduction: "Ein großes Herz braucht keine laute Stimme.",
    ariaLabel: "Brumo, ein junger freundlicher Ork in auberginefarbener und bronzener Rüstung",
    stillAsset: "/assets/companions/orc.png",
    animated: false,
    care: { awakeSatietyPerHour: 1.6, awakeEnergyPerHour: 0.5, awakeJoyPerHour: 0.3, sleepSatietyPerHour: 0.85, sleepJoyPerHour: 0.08, sleepEnergyPerHour: 9.3, feedSatietyGain: 25, playJoyGain: 13, petBondGain: 3 }
  },
  pony: {
    kind: "pony",
    name: "Caelo",
    species: "Sternenpony",
    tagline: "Der mutige Läufer zwischen den Wolken",
    introduction: "Wo Caelo seine Hufe setzt, wird der Himmel ein wenig weiter.",
    ariaLabel: "Caelo, ein kleines weißes Sternenpony mit himmelblauer Mähne",
    stillAsset: "/assets/companions/pony.png",
    animated: false,
    care: { awakeSatietyPerHour: 1.4, awakeEnergyPerHour: 0.6, awakeJoyPerHour: 0.55, sleepSatietyPerHour: 0.8, sleepJoyPerHour: 0.12, sleepEnergyPerHour: 10, feedSatietyGain: 22, playJoyGain: 16, petBondGain: 2.7 }
  },
  fairy: {
    kind: "fairy",
    name: "Selya",
    species: "Lichtfee",
    tagline: "Die heitere Hüterin kleiner Wunder",
    introduction: "Selya erinnert dich daran, dass selbst leises Licht den Weg findet.",
    ariaLabel: "Selya, eine kleine Lichtfee mit rosafarbenem Haar und zarten Flügeln",
    stillAsset: "/assets/companions/fairy.png",
    animated: false,
    care: { awakeSatietyPerHour: 1.2, awakeEnergyPerHour: 0.48, awakeJoyPerHour: 0.6, sleepSatietyPerHour: 0.7, sleepJoyPerHour: 0.14, sleepEnergyPerHour: 9.7, feedSatietyGain: 20, playJoyGain: 18, petBondGain: 2.9 }
  },
  dog: {
    kind: "dog",
    name: "Fenn",
    species: "Sternenhund",
    tagline: "Der treue Wächter deiner Wege",
    introduction: "Fenn bleibt an deiner Seite, ganz gleich wohin der Tag euch führt.",
    ariaLabel: "Fenn, ein kleiner karamellfarbener Sternenhund mit blauen Augen",
    stillAsset: "/assets/companions/dog.png",
    animated: false,
    care: { awakeSatietyPerHour: 1.45, awakeEnergyPerHour: 0.52, awakeJoyPerHour: 0.5, sleepSatietyPerHour: 0.8, sleepJoyPerHour: 0.12, sleepEnergyPerHour: 9.4, feedSatietyGain: 23, playJoyGain: 15, petBondGain: 3.5 }
  },
  elf: {
    kind: "elf",
    name: "Aelira",
    species: "Waldelfe",
    tagline: "Die stille Bewahrerin des grünen Pfades",
    introduction: "Aelira hört selbst das, was der Wald nur im Flüstern erzählt.",
    ariaLabel: "Aelira, eine junge Waldelfe mit grünem Haar und amethystfarbenen Augen",
    stillAsset: "/assets/companions/elf.png",
    animated: false,
    care: { awakeSatietyPerHour: 1.15, awakeEnergyPerHour: 0.38, awakeJoyPerHour: 0.28, sleepSatietyPerHour: 0.65, sleepJoyPerHour: 0.07, sleepEnergyPerHour: 8.5, feedSatietyGain: 21, playJoyGain: 10, petBondGain: 3.2 }
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
