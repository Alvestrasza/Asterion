import type { CompanionKind } from "./companions";
import type { Locale } from "./i18n";

export type Messages = {
  meta: { title: string; description: string };
  nav: {
    home: string;
    about: string;
    companions: string;
    roadmap: string;
    signIn: string;
    care: string;
    language: string;
    skip: string;
  };
  hero: {
    eyebrow: string;
    title: string;
    description: string;
    primary: string;
    secondary: string;
    note: string;
  };
  about: {
    eyebrow: string;
    title: string;
    description: string;
    careTitle: string;
    careText: string;
    devicesTitle: string;
    devicesText: string;
    paceTitle: string;
    paceText: string;
  };
  gallery: { eyebrow: string; title: string; description: string };
  companions: Record<CompanionKind, { species: string; description: string; alt: string }>;
  roadmap: {
    eyebrow: string;
    title: string;
    description: string;
    progressionTitle: string;
    progressionText: string;
    diaryTitle: string;
    diaryText: string;
    socialTitle: string;
    socialText: string;
  };
  footer: { tagline: string; status: string };
  login: {
    eyebrow: string;
    title: string;
    description: string;
    submit: string;
    register: string;
    unavailableTitle: string;
    unavailableText: string;
    denied: string;
    error: string;
    back: string;
  };
  care: { legacyLanguage: string; back: string };
  errors: { title: string; description: string; retry: string; loading: string };
};

export const MESSAGES: Record<Locale, Messages> = {
  de: {
    meta: {
      title: "Sternenfreunde · Dein virtuelles Haustier",
      description: "Wähle deinen Sternenfreund, füttere ihn und spiele mit ihm. Ein Haustierspiel im Browser für Handy, Tablet und Computer."
    },
    nav: {
      home: "Startseite",
      about: "Das Spiel",
      companions: "Sternenfreunde",
      roadmap: "Was noch kommt",
      signIn: "Anmelden",
      care: "Mein Sternenfreund",
      language: "Sprache",
      skip: "Zum Inhalt springen"
    },
    hero: {
      eyebrow: "Sternenfreunde",
      title: "Wer wird dein Sternenfreund?",
      description: "Ein Drache, ein Kaninchen oder doch ein Ork? Such dir einen Freund aus, füttere ihn, spiele mit ihm und kümmere dich um ihn.",
      primary: "Anmelden",
      secondary: "Alle Freunde ansehen",
      note: "Melde dich an oder erstelle ein Konto und wähle deinen ersten Sternenfreund."
    },
    about: {
      eyebrow: "Das Spiel",
      title: "Ein Haustier in deinem Browser",
      description: "Sternenfreunde ist ein Haustierspiel nach dem Tamagotchi-Prinzip. Du kümmerst dich um einen Begleiter und siehst, wie es ihm geht.",
      careTitle: "Füttern und spielen",
      careText: "Hat dein Freund Hunger? Möchte er spielen oder schlafen? Seine Werte zeigen dir, was er braucht.",
      devicesTitle: "Ohne Installation",
      devicesText: "Spiele auf dem Handy, Tablet oder Computer. Mit demselben Konto kannst du deinen Spielstand auf einem anderen Gerät öffnen.",
      paceTitle: "Eure letzten Aktivitäten",
      paceText: "Im Verlauf kannst du nachsehen, wann du deinen Freund gefüttert, gestreichelt oder mit ihm gespielt hast."
    },
    gallery: {
      eyebrow: "Die Figuren",
      title: "Acht Freunde zur Auswahl",
      description: "Du kümmerst dich um einen Sternenfreund. In den Einstellungen kannst du die Figur wechseln; dein Spielstand bleibt dabei erhalten."
    },
    companions: {
      asterion: {
        species: "Sternendrache",
        description: "Klein, neugierig und mit goldenen Hörnern: Das ist Asterion.",
        alt: "Asterion, ein kleiner goldener und azurblauer Sternendrache"
      },
      rabbit: {
        species: "Sternenkaninchen",
        description: "Liora hat lange Ohren und ein weiches, lavendelfarbenes Fell.",
        alt: "Liora, ein mondfarbenes und lavendelfarbenes Sternenkaninchen"
      },
      cat: {
        species: "Sternenkatze",
        description: "Nyra macht es sich am liebsten an einem warmen Platz gemütlich.",
        alt: "Nyra, eine anthrazitfarbene Sternenkatze mit grünen Augen"
      },
      orc: {
        species: "Junger Ork",
        description: "Brumo sieht in seiner Rüstung wild aus, ist aber ein freundlicher Kerl.",
        alt: "Brumo, ein freundlicher junger Ork in auberginefarbener und bronzener Rüstung"
      },
      pony: {
        species: "Sternenpony",
        description: "Caelo erkennst du an seiner himmelblauen Mähne.",
        alt: "Caelo, ein weißes Sternenpony mit himmelblauer Mähne"
      },
      fairy: {
        species: "Lichtfee",
        description: "Selya ist die kleine Fee mit rosa Haaren und zarten Flügeln.",
        alt: "Selya, eine kleine Lichtfee mit rosafarbenem Haar und zarten Flügeln"
      },
      dog: {
        species: "Sternenhund",
        description: "Fenn ist ein neugieriger Hund, der gern mit dir spielt.",
        alt: "Fenn, ein karamellfarbener Sternenhund mit blauen Augen"
      },
      elf: {
        species: "Waldelfe",
        description: "Aelira ist eine Waldelfe mit grünem Haar und spitzen Ohren.",
        alt: "Aelira, eine junge Waldelfe mit grünem Haar und amethystfarbenen Augen"
      }
    },
    roadmap: {
      eyebrow: "Geplant, noch nicht verfügbar",
      title: "Unser nächstes Kapitel",
      description: "Diese Ideen gehören zum weiteren Ausbau. Wir zeigen sie hier als Ausblick, nicht als bereits fertige Funktionen.",
      progressionTitle: "Gemeinsam wachsen",
      progressionText: "Geplant sind Level von 1 bis 99, Erfolge und nach und nach bis zu fünf eigene Sternenfreunde. Unterschiedliche Bedürfnisse, ein gemütliches Zuhause und kleine Abenteuer sollen das Zusammenleben abwechslungsreich machen.",
      diaryTitle: "Erinnerungen bewahren",
      diaryText: "Geplant ist ein Tagebuch für gemeinsame Erlebnisse und persönliche Notizen mit Verschlüsselung auf deinem Gerät. Datenschutz, Wiederherstellung und Gerätewechsel müssen vor der Freigabe sorgfältig geprüft werden.",
      socialTitle: "Freundschaften bewusst gestalten",
      socialText: "Geplant sind eine Freundesliste mit gegenseitiger Bestätigung und ein geschützter Chat. Regeln für Kontakte, Blockieren und Melden sowie das Sicherheitskonzept werden vor einer Einführung ausgearbeitet."
    },
    footer: {
      tagline: "Sternenfreunde",
      status: "Testphase"
    },
    login: {
      eyebrow: "Willkommen zurück",
      title: "Bei Sternenfreunde anmelden",
      description: "Melde dich mit deinem Konto an. Dafür öffnet sich unser Anmeldedienst; anschließend kommst du hierher zurück.",
      submit: "Anmelden",
      register: "Konto erstellen",
      unavailableTitle: "Die Anmeldung ist noch nicht verfügbar.",
      unavailableText: "In dieser Umgebung ist die Anmeldung noch nicht eingerichtet. Du kannst die Sternenfreunde auf der Startseite kennenlernen und es später erneut versuchen.",
      denied: "Die Anmeldung wurde nicht abgeschlossen. Versuche es erneut oder wende dich an einen Administrator.",
      error: "Die Anmeldung konnte nicht abgeschlossen werden. Bitte versuche es erneut.",
      back: "Zur Startseite"
    },
    care: {
      legacyLanguage: "Der Spielbereich ist derzeit nur auf Deutsch verfügbar.",
      back: "Zur Startseite"
    },
    errors: {
      title: "Das hat gerade nicht geklappt.",
      description: "Diese Seite konnte nicht geladen werden. Bitte versuche es noch einmal.",
      retry: "Erneut versuchen",
      loading: "Wird geladen …"
    }
  },
  en: {
    meta: {
      title: "Starfriends · Your virtual pet",
      description: "Choose your Starfriend, feed them and play together. A browser pet game for phones, tablets and computers."
    },
    nav: {
      home: "Home",
      about: "The game",
      companions: "Starfriends",
      roadmap: "Coming later",
      signIn: "Sign in",
      care: "My companion",
      language: "Language",
      skip: "Skip to content"
    },
    hero: {
      eyebrow: "Starfriends",
      title: "Who will be your Starfriend?",
      description: "A dragon, a rabbit or perhaps an orc? Choose a friend, feed them, play together and look after them.",
      primary: "Sign in",
      secondary: "Meet all the friends",
      note: "Sign in or create an account and choose your first Starfriend."
    },
    about: {
      eyebrow: "The game",
      title: "A pet in your browser",
      description: "Starfriends is a Tamagotchi-style pet game. Look after your companion and see how they are doing.",
      careTitle: "Feed and play",
      careText: "Is your friend hungry, ready to play or tired? Their stats show you what they need.",
      devicesTitle: "No installation",
      devicesText: "Play on your phone, tablet or computer. Sign in with the same account to open your saved game on another device.",
      paceTitle: "Recent activities",
      paceText: "Check the activity history to see when you fed, petted or played with your friend."
    },
    gallery: {
      eyebrow: "The characters",
      title: "Eight friends to choose from",
      description: "You look after one Starfriend. You can switch characters in settings without losing your progress."
    },
    companions: {
      asterion: {
        species: "Star dragon",
        description: "Small, curious and sporting golden horns: meet Asterion.",
        alt: "Asterion, a small gold and azure-blue star dragon"
      },
      rabbit: {
        species: "Star rabbit",
        description: "Liora has long ears and soft lavender fur.",
        alt: "Liora, a moon-white and lavender star rabbit"
      },
      cat: {
        species: "Star cat",
        description: "Nyra loves curling up somewhere warm.",
        alt: "Nyra, a charcoal-colored star cat with green eyes"
      },
      orc: {
        species: "Young orc",
        description: "Brumo looks fierce in his armor, but he is a friendly fellow.",
        alt: "Brumo, a friendly young orc in purple and bronze armor"
      },
      pony: {
        species: "Star pony",
        description: "You can spot Caelo by his sky-blue mane.",
        alt: "Caelo, a white star pony with a sky-blue mane"
      },
      fairy: {
        species: "Light fairy",
        description: "Selya is the little fairy with pink hair and delicate wings.",
        alt: "Selya, a small light fairy with pink hair and delicate wings"
      },
      dog: {
        species: "Star dog",
        description: "Fenn is a curious dog who loves to play with you.",
        alt: "Fenn, a caramel-colored star dog with blue eyes"
      },
      elf: {
        species: "Wood elf",
        description: "Aelira is a wood elf with green hair and pointed ears.",
        alt: "Aelira, a young wood elf with green hair and amethyst eyes"
      }
    },
    roadmap: {
      eyebrow: "Planned, not available yet",
      title: "Our next chapter",
      description: "These ideas are part of the project's future. They are a preview of work ahead, not features that are already available.",
      progressionTitle: "Growing together",
      progressionText: "Plans include levels 1 to 99, achievements and gradually unlocking up to five Starfriends of your own. Different needs, a cozy home and little adventures will bring variety to life together.",
      diaryTitle: "Keeping memories",
      diaryText: "A diary of shared moments and personal notes encrypted on your device is planned. Privacy, recovery and moving between devices must be carefully reviewed before release.",
      socialTitle: "Thoughtful friendships",
      socialText: "Plans include mutually confirmed friendships and a protected chat. Contact rules, blocking, reporting and the security design will be worked out before these features are introduced."
    },
    footer: {
      tagline: "Starfriends",
      status: "Testing"
    },
    login: {
      eyebrow: "Welcome back",
      title: "Sign in to Starfriends",
      description: "Sign in with your account. Our sign-in service will open, then return you here.",
      submit: "Sign in",
      register: "Create account",
      unavailableTitle: "Sign-in is not available yet.",
      unavailableText: "Sign-in has not been set up in this environment yet. You can meet the Starfriends on the home page and try again later.",
      denied: "Sign-in was not completed. Try again or contact an administrator.",
      error: "Sign-in could not be completed. Please try again.",
      back: "Back to home"
    },
    care: {
      legacyLanguage: "The game screen is currently only available in German.",
      back: "Back to home"
    },
    errors: {
      title: "That did not work just now.",
      description: "This page could not be loaded. Please try again.",
      retry: "Try again",
      loading: "Loading …"
    }
  },
  fr: {
    meta: {
      title: "Starfriends · Ton compagnon virtuel",
      description: "Choisis ton Starfriend, nourris-le et joue avec lui. Un jeu de compagnons dans ton navigateur, sur téléphone, tablette et ordinateur."
    },
    nav: {
      home: "Accueil",
      about: "Le jeu",
      companions: "Les Starfriends",
      roadmap: "À venir",
      signIn: "Se connecter",
      care: "Mon compagnon",
      language: "Langue",
      skip: "Aller au contenu"
    },
    hero: {
      eyebrow: "Starfriends",
      title: "Qui sera ton Starfriend ?",
      description: "Un dragon, un lapin ou plutôt un orc ? Choisis un ami, nourris-le, joue avec lui et prends soin de lui.",
      primary: "Se connecter",
      secondary: "Voir tous les amis",
      note: "Connecte-toi ou crée un compte et choisis ton premier compagnon."
    },
    about: {
      eyebrow: "Le jeu",
      title: "Un compagnon dans ton navigateur",
      description: "Starfriends est un jeu inspiré des Tamagotchi. Occupe-toi de ton compagnon et regarde comment il se porte.",
      careTitle: "Nourrir et jouer",
      careText: "Ton ami a faim, envie de jouer ou besoin de dormir ? Ses indicateurs te montrent ce dont il a besoin.",
      devicesTitle: "Sans installation",
      devicesText: "Joue sur téléphone, tablette ou ordinateur. Connecte-toi avec le même compte pour retrouver ta partie sur un autre appareil.",
      paceTitle: "Les dernières activités",
      paceText: "Consulte l'historique pour savoir quand tu as nourri ou caressé ton ami, ou joué avec lui."
    },
    gallery: {
      eyebrow: "Les personnages",
      title: "Huit amis au choix",
      description: "Tu t'occupes d'un Starfriend. Tu peux changer de personnage dans les paramètres sans perdre ta progression."
    },
    companions: {
      asterion: {
        species: "Dragon des étoiles",
        description: "Petit, curieux et coiffé de cornes dorées : voici Asterion.",
        alt: "Asterion, un petit dragon des étoiles doré et bleu azur"
      },
      rabbit: {
        species: "Lapin des étoiles",
        description: "Liora a de longues oreilles et une douce fourrure lavande.",
        alt: "Liora, un lapin des étoiles blanc lunaire et lavande"
      },
      cat: {
        species: "Chat des étoiles",
        description: "Nyra aime se blottir dans un coin bien chaud.",
        alt: "Nyra, un chat des étoiles gris anthracite aux yeux verts"
      },
      orc: {
        species: "Jeune orc",
        description: "Brumo a l'air féroce dans son armure, mais c'est un gentil compagnon.",
        alt: "Brumo, un jeune orc amical en armure aubergine et bronze"
      },
      pony: {
        species: "Poney des étoiles",
        description: "Tu reconnaîtras Caelo à sa crinière bleu ciel.",
        alt: "Caelo, un poney des étoiles blanc à la crinière bleu ciel"
      },
      fairy: {
        species: "Fée de lumière",
        description: "Selya est la petite fée aux cheveux roses et aux ailes délicates.",
        alt: "Selya, une petite fée de lumière aux cheveux roses et aux ailes délicates"
      },
      dog: {
        species: "Chien des étoiles",
        description: "Fenn est un chien curieux qui aime jouer avec toi.",
        alt: "Fenn, un chien des étoiles couleur caramel aux yeux bleus"
      },
      elf: {
        species: "Elfe des bois",
        description: "Aelira est une elfe des bois aux cheveux verts et aux oreilles pointues.",
        alt: "Aelira, une jeune elfe des bois aux cheveux verts et aux yeux améthyste"
      }
    },
    roadmap: {
      eyebrow: "Prévu, pas encore disponible",
      title: "Notre prochain chapitre",
      description: "Ces idées font partie de la suite du projet. Elles présentent le travail à venir, pas des fonctions déjà disponibles.",
      progressionTitle: "Grandir ensemble",
      progressionText: "Nous prévoyons des niveaux de 1 à 99, des succès et jusqu'à cinq Starfriends à débloquer progressivement. Des besoins différents, un foyer douillet et de petites aventures apporteront de la variété au quotidien.",
      diaryTitle: "Garder des souvenirs",
      diaryText: "Un journal des moments partagés et des notes personnelles chiffrées sur ton appareil sont prévus. La confidentialité, la récupération et le changement d'appareil devront être soigneusement étudiés avant leur mise à disposition.",
      socialTitle: "Des amitiés choisies",
      socialText: "Une liste d'amis avec confirmation mutuelle et un chat protégé sont prévus. Les règles de contact, le blocage, le signalement et la conception de la sécurité seront définis avant leur introduction."
    },
    footer: {
      tagline: "Starfriends",
      status: "Phase de test"
    },
    login: {
      eyebrow: "Heureux de te revoir",
      title: "Se connecter à Starfriends",
      description: "Connecte-toi avec ton compte. Notre service de connexion s'ouvrira, puis te ramènera ici.",
      submit: "Se connecter",
      register: "Créer un compte",
      unavailableTitle: "La connexion n'est pas encore disponible.",
      unavailableText: "La connexion n'est pas encore configurée dans cet environnement. Tu peux découvrir les Starfriends sur la page d'accueil et réessayer plus tard.",
      denied: "La connexion n'a pas abouti. Réessaie ou contacte un administrateur.",
      error: "La connexion n'a pas pu aboutir. Merci de réessayer.",
      back: "Retour à l'accueil"
    },
    care: {
      legacyLanguage: "Le jeu est actuellement disponible uniquement en allemand.",
      back: "Retour à l'accueil"
    },
    errors: {
      title: "Cela n'a pas fonctionné cette fois.",
      description: "Cette page n'a pas pu être chargée. Merci de réessayer.",
      retry: "Réessayer",
      loading: "Chargement …"
    }
  },
  es: {
    meta: {
      title: "Starfriends · Tu mascota virtual",
      description: "Elige a tu Starfriend, dale de comer y juega con él. Un juego de mascotas en el navegador para móviles, tabletas y ordenadores."
    },
    nav: {
      home: "Inicio",
      about: "El juego",
      companions: "Los Starfriends",
      roadmap: "Más adelante",
      signIn: "Iniciar sesión",
      care: "Mi compañero",
      language: "Idioma",
      skip: "Saltar al contenido"
    },
    hero: {
      eyebrow: "Starfriends",
      title: "¿Quién será tu Starfriend?",
      description: "¿Un dragón, un conejo o quizá un orco? Elige un amigo, dale de comer, juega con él y cuídalo.",
      primary: "Iniciar sesión",
      secondary: "Ver a todos los amigos",
      note: "Inicia sesión o crea una cuenta y elige a tu primer compañero."
    },
    about: {
      eyebrow: "El juego",
      title: "Una mascota en tu navegador",
      description: "Starfriends es un juego de mascotas inspirado en los Tamagotchi. Cuida de tu compañero y comprueba cómo está.",
      careTitle: "Comer y jugar",
      careText: "¿Tu amigo tiene hambre, ganas de jugar o sueño? Sus indicadores te muestran lo que necesita.",
      devicesTitle: "Sin instalación",
      devicesText: "Juega en el móvil, la tableta o el ordenador. Usa la misma cuenta para abrir tu partida en otro dispositivo.",
      paceTitle: "Últimas actividades",
      paceText: "Consulta el historial para ver cuándo diste de comer a tu amigo, lo acariciaste o jugaste con él."
    },
    gallery: {
      eyebrow: "Los personajes",
      title: "Ocho amigos para elegir",
      description: "Cuidas de un Starfriend. Puedes cambiar de personaje en los ajustes sin perder tu progreso."
    },
    companions: {
      asterion: {
        species: "Dragón de las estrellas",
        description: "Pequeño, curioso y con cuernos dorados: así es Asterion.",
        alt: "Asterion, un pequeño dragón de las estrellas dorado y azul celeste"
      },
      rabbit: {
        species: "Conejo de las estrellas",
        description: "Liora tiene orejas largas y un suave pelaje lavanda.",
        alt: "Liora, un conejo de las estrellas blanco lunar y lavanda"
      },
      cat: {
        species: "Gato de las estrellas",
        description: "A Nyra le encanta acurrucarse en un rincón cálido.",
        alt: "Nyra, un gato de las estrellas gris antracita con ojos verdes"
      },
      orc: {
        species: "Orco joven",
        description: "Brumo parece feroz con su armadura, pero es muy amistoso.",
        alt: "Brumo, un orco joven y amable con armadura color berenjena y bronce"
      },
      pony: {
        species: "Poni de las estrellas",
        description: "Reconocerás a Caelo por su crin azul cielo.",
        alt: "Caelo, un poni de las estrellas blanco con crin azul cielo"
      },
      fairy: {
        species: "Hada de luz",
        description: "Selya es la pequeña hada de pelo rosa y alas delicadas.",
        alt: "Selya, una pequeña hada de luz con pelo rosa y alas delicadas"
      },
      dog: {
        species: "Perro de las estrellas",
        description: "Fenn es un perro curioso al que le encanta jugar contigo.",
        alt: "Fenn, un perro de las estrellas color caramelo con ojos azules"
      },
      elf: {
        species: "Elfa del bosque",
        description: "Aelira es una elfa del bosque de pelo verde y orejas puntiagudas.",
        alt: "Aelira, una joven elfa del bosque con pelo verde y ojos amatista"
      }
    },
    roadmap: {
      eyebrow: "Previsto, aún no disponible",
      title: "Nuestro próximo capítulo",
      description: "Estas ideas forman parte del futuro del proyecto. Son un avance del trabajo pendiente, no funciones que ya estén disponibles.",
      progressionTitle: "Crecer juntos",
      progressionText: "Están previstos los niveles del 1 al 99, logros y hasta cinco Starfriends propios que se desbloquearán poco a poco. Distintas necesidades, un hogar acogedor y pequeñas aventuras darán variedad a la vida juntos.",
      diaryTitle: "Guardar recuerdos",
      diaryText: "Está previsto un diario de momentos compartidos y notas personales cifradas en tu dispositivo. La privacidad, la recuperación y el cambio de dispositivo deberán revisarse con cuidado antes de su lanzamiento.",
      socialTitle: "Amistades elegidas",
      socialText: "Están previstas una lista de amigos con confirmación mutua y un chat protegido. Las reglas de contacto, el bloqueo, las denuncias y el diseño de seguridad se definirán antes de su introducción."
    },
    footer: {
      tagline: "Starfriends",
      status: "Fase de pruebas"
    },
    login: {
      eyebrow: "Qué bien verte de nuevo",
      title: "Iniciar sesión en Starfriends",
      description: "Inicia sesión con tu cuenta. Se abrirá nuestro servicio de acceso y después volverás aquí.",
      submit: "Iniciar sesión",
      register: "Crear cuenta",
      unavailableTitle: "El inicio de sesión aún no está disponible.",
      unavailableText: "El inicio de sesión aún no está configurado en este entorno. Puedes conocer a los Starfriends en la página de inicio e intentarlo más tarde.",
      denied: "No se ha completado el inicio de sesión. Inténtalo de nuevo o contacta con un administrador.",
      error: "No se pudo completar el inicio de sesión. Inténtalo de nuevo.",
      back: "Volver al inicio"
    },
    care: {
      legacyLanguage: "El juego está disponible actualmente solo en alemán.",
      back: "Volver al inicio"
    },
    errors: {
      title: "Esta vez no ha funcionado.",
      description: "No se ha podido cargar esta página. Inténtalo de nuevo.",
      retry: "Volver a intentar",
      loading: "Cargando …"
    }
  }
};

export function getMessages(locale: Locale): Messages {
  return MESSAGES[locale];
}
