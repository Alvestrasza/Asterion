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
    apply: string;
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
      title: "Sternenfreunde · Kleine Freunde, gemeinsame Geschichten",
      description: "Lerne Asterion und die Sternenfreunde kennen: ein liebevoll gestaltetes Projekt rund um virtuelle Begleiter, kleine Pflegemomente und gemeinsame Geschichten."
    },
    nav: {
      home: "Startseite",
      about: "Die Idee",
      companions: "Sternenfreunde",
      roadmap: "Was noch kommt",
      signIn: "Anmelden",
      care: "Mein Sternenfreund",
      language: "Sprache",
      apply: "Übernehmen",
      skip: "Zum Inhalt springen"
    },
    hero: {
      eyebrow: "Willkommen bei den Sternenfreunden",
      title: "Ein kleiner Freund. Eure eigene Geschichte.",
      description: "Ein ruhiger Moment, ein neugieriger Blick und ein bisschen Zeit füreinander. Entdecke Asterion und seine Freunde in einem liebevoll gezeichneten kleinen Universum.",
      primary: "Anmelden und ausprobieren",
      secondary: "Die Freunde kennenlernen",
      note: "Das Projekt wächst noch. Der Pflege-Prototyp ist für freigeschaltete Testkonten verfügbar."
    },
    about: {
      eyebrow: "Die Idee",
      title: "Kleine gemeinsame Momente zählen.",
      description: "Sternenfreunde ist ein Tamagotchi-inspiriertes Webprojekt für Kinder und Familien. Wir entwickeln einen gemütlichen Ort zum Spielen, Kümmern und Entdecken.",
      careTitle: "Zeit füreinander",
      careText: "Im aktuellen Prototyp kannst du deinen ausgewählten Begleiter füttern, mit ihm spielen und ihn ausruhen lassen.",
      devicesTitle: "Im Browser zu Hause",
      devicesText: "Du brauchst keine Spielinstallation. Die Website ist für Handy, Tablet und Computer gedacht; der Spielstand wird auf dem Server gespeichert.",
      paceTitle: "Freude statt Pflicht",
      paceText: "Unser Ziel ist ein freundlicher Alltag mit deinem Begleiter. Ruhepausen und ein entspannter Wiedereinstieg gehören zu den geplanten Erweiterungen."
    },
    gallery: {
      eyebrow: "Acht kleine Persönlichkeiten",
      title: "Wer begleitet dich?",
      description: "Lerne die acht gezeichneten Figuren kennen. Im aktuellen Pflege-Prototyp kümmerst du dich um einen ausgewählten Begleiter; individuellere Bedürfnisse und gemeinsame Abenteuer sind geplant."
    },
    companions: {
      asterion: {
        species: "Sternendrache",
        description: "Ein ruhiger kleiner Hüter mit einem wachsamen Blick und einem warmen Herzen.",
        alt: "Asterion, ein kleiner goldener und azurblauer Sternendrache"
      },
      rabbit: {
        species: "Sternenkaninchen",
        description: "Liora entdeckt mit sanften Pfoten die kleinen Wunder am Wegesrand.",
        alt: "Liora, ein mondfarbenes und lavendelfarbenes Sternenkaninchen"
      },
      cat: {
        species: "Sternenkatze",
        description: "Nyra beobachtet aufmerksam und findet die gemütlichsten Plätze für stille Momente.",
        alt: "Nyra, eine anthrazitfarbene Sternenkatze mit grünen Augen"
      },
      orc: {
        species: "Junger Ork",
        description: "Brumo hat ein großes Herz und Freude an kleinen gemeinsamen Abenteuern.",
        alt: "Brumo, ein freundlicher junger Ork in auberginefarbener und bronzener Rüstung"
      },
      pony: {
        species: "Sternenpony",
        description: "Caelo schaut neugierig hinter die nächste Wolke und bringt ein wenig Abenteuer mit.",
        alt: "Caelo, ein weißes Sternenpony mit himmelblauer Mähne"
      },
      fairy: {
        species: "Lichtfee",
        description: "Selya entdeckt selbst im kleinsten Licht einen Grund zum Staunen.",
        alt: "Selya, eine kleine Lichtfee mit rosafarbenem Haar und zarten Flügeln"
      },
      dog: {
        species: "Sternenhund",
        description: "Fenn ist gern an deiner Seite und freut sich auf jeden gemeinsamen Weg.",
        alt: "Fenn, ein karamellfarbener Sternenhund mit blauen Augen"
      },
      elf: {
        species: "Waldelfe",
        description: "Aelira lauscht geduldig dem Wald und entdeckt, was andere leicht übersehen.",
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
      tagline: "Sternenfreunde · Kleine Freunde, gemeinsame Geschichten.",
      status: "In Entwicklung · Pflege-Prototyp für freigeschaltete Testkonten"
    },
    login: {
      eyebrow: "Willkommen zurück",
      title: "Dein Sternenfreund wartet auf einen gemeinsamen Moment.",
      description: "Melde dich mit deinem freigeschalteten Konto an, um den Pflege-Prototyp auszuprobieren. Für die Anmeldung wirst du zu unserem Anmeldedienst weitergeleitet.",
      submit: "Mit meinem Konto anmelden",
      unavailableTitle: "Die Anmeldung ist noch nicht verfügbar.",
      unavailableText: "In dieser Umgebung ist die Anmeldung noch nicht eingerichtet. Du kannst die Sternenfreunde auf der Startseite kennenlernen und es später erneut versuchen.",
      denied: "Dein Konto hat noch keinen Zugang zum Pflege-Prototyp. Bitte frage den Projektverantwortlichen nach einer Freischaltung.",
      error: "Die Anmeldung konnte nicht abgeschlossen werden. Bitte versuche es erneut.",
      back: "Zur Startseite"
    },
    care: {
      legacyLanguage: "Der Pflegebereich ist derzeit auf Deutsch. Die Übersetzung seiner Aktionen, Sprechblasen und des Verlaufs folgt in einem weiteren Schritt.",
      back: "Zur Startseite"
    },
    errors: {
      title: "Das hat gerade nicht geklappt.",
      description: "Diese Seite konnte nicht geladen werden. Bitte versuche es noch einmal.",
      retry: "Erneut versuchen",
      loading: "Ein kleiner Moment …"
    }
  },
  en: {
    meta: {
      title: "Starfriends · Little friends, shared stories",
      description: "Meet Asterion and the Starfriends: a lovingly illustrated project about virtual companions, small moments of care and shared stories."
    },
    nav: {
      home: "Home",
      about: "The idea",
      companions: "Starfriends",
      roadmap: "Coming later",
      signIn: "Sign in",
      care: "My companion",
      language: "Language",
      apply: "Apply",
      skip: "Skip to content"
    },
    hero: {
      eyebrow: "Welcome to Starfriends",
      title: "A little friend. A story of your own.",
      description: "A quiet moment, a curious glance and a little time together. Discover Asterion and friends in a small, lovingly illustrated universe.",
      primary: "Sign in and try it",
      secondary: "Meet the friends",
      note: "The project is still growing. The care prototype is available to approved test accounts."
    },
    about: {
      eyebrow: "The idea",
      title: "Little moments together matter.",
      description: "Starfriends is a Tamagotchi-inspired web project for children and families. We are creating a cozy place to play, care and discover.",
      careTitle: "Time for each other",
      careText: "In the current prototype, you can feed your chosen companion, play together and let them rest.",
      devicesTitle: "At home in your browser",
      devicesText: "No game installation is needed. The website is designed for phones, tablets and computers, with game progress stored on the server.",
      paceTitle: "Joy, not chores",
      paceText: "Our aim is a friendly daily rhythm with your companion. Rest breaks and a gentle return after time away are among the planned additions."
    },
    gallery: {
      eyebrow: "Eight little personalities",
      title: "Who will join you?",
      description: "Meet the eight illustrated characters. In the current care prototype, you look after one chosen companion; more individual needs and shared adventures are planned."
    },
    companions: {
      asterion: {
        species: "Star dragon",
        description: "A calm little guardian with a watchful gaze and a warm heart.",
        alt: "Asterion, a small gold and azure-blue star dragon"
      },
      rabbit: {
        species: "Star rabbit",
        description: "With gentle paws, Liora discovers little wonders along the path.",
        alt: "Liora, a moon-white and lavender star rabbit"
      },
      cat: {
        species: "Star cat",
        description: "Nyra watches closely and finds the coziest places for quiet moments.",
        alt: "Nyra, a charcoal-colored star cat with green eyes"
      },
      orc: {
        species: "Young orc",
        description: "Brumo has a big heart and enjoys little adventures together.",
        alt: "Brumo, a friendly young orc in purple and bronze armor"
      },
      pony: {
        species: "Star pony",
        description: "Caelo peeks curiously beyond the next cloud and brings a little adventure along.",
        alt: "Caelo, a white star pony with a sky-blue mane"
      },
      fairy: {
        species: "Light fairy",
        description: "Selya finds a reason for wonder in even the smallest spark of light.",
        alt: "Selya, a small light fairy with pink hair and delicate wings"
      },
      dog: {
        species: "Star dog",
        description: "Fenn loves being by your side and looks forward to every path you share.",
        alt: "Fenn, a caramel-colored star dog with blue eyes"
      },
      elf: {
        species: "Wood elf",
        description: "Aelira listens patiently to the forest and notices what others might miss.",
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
      tagline: "Starfriends · Little friends, shared stories.",
      status: "In development · Care prototype for approved test accounts"
    },
    login: {
      eyebrow: "Welcome back",
      title: "Share a little moment with your Starfriend.",
      description: "Sign in with your approved account to try the care prototype. You will be taken to our sign-in service to log in.",
      submit: "Sign in with my account",
      unavailableTitle: "Sign-in is not available yet.",
      unavailableText: "Sign-in has not been set up in this environment yet. You can meet the Starfriends on the home page and try again later.",
      denied: "Your account does not have access to the care prototype yet. Please ask the project administrator about access.",
      error: "Sign-in could not be completed. Please try again.",
      back: "Back to home"
    },
    care: {
      legacyLanguage: "The care screen is currently in German. Its actions, speech bubbles and history will be translated in a later step.",
      back: "Back to home"
    },
    errors: {
      title: "That did not work just now.",
      description: "This page could not be loaded. Please try again.",
      retry: "Try again",
      loading: "Just a little moment …"
    }
  },
  fr: {
    meta: {
      title: "Starfriends · Petits amis, histoires partagées",
      description: "Découvre Asterion et les Starfriends : un projet illustré avec soin, autour de compagnons virtuels, de petits moments d'attention et d'histoires partagées."
    },
    nav: {
      home: "Accueil",
      about: "L'idée",
      companions: "Les Starfriends",
      roadmap: "À venir",
      signIn: "Se connecter",
      care: "Mon compagnon",
      language: "Langue",
      apply: "Appliquer",
      skip: "Aller au contenu"
    },
    hero: {
      eyebrow: "Bienvenue chez les Starfriends",
      title: "Un petit compagnon. Ta propre histoire.",
      description: "Un moment de calme, un regard curieux et un peu de temps ensemble. Découvre Asterion et ses amis dans un petit univers dessiné avec tendresse.",
      primary: "Se connecter et essayer",
      secondary: "Rencontrer les amis",
      note: "Le projet grandit encore. Le prototype de soin est accessible aux comptes de test autorisés."
    },
    about: {
      eyebrow: "L'idée",
      title: "Les petits moments ensemble comptent.",
      description: "Starfriends est un projet web inspiré des Tamagotchi, pour les enfants et les familles. Nous créons un lieu douillet pour jouer, prendre soin et découvrir.",
      careTitle: "Du temps ensemble",
      careText: "Dans le prototype actuel, tu peux nourrir le compagnon de ton choix, jouer avec lui et le laisser se reposer.",
      devicesTitle: "Chez toi, dans ton navigateur",
      devicesText: "Pas besoin d'installer un jeu. Le site est conçu pour les téléphones, tablettes et ordinateurs ; la progression est enregistrée sur le serveur.",
      paceTitle: "Du plaisir, pas des corvées",
      paceText: "Nous souhaitons un quotidien agréable avec ton compagnon. Des pauses et un retour en douceur après une absence font partie des ajouts prévus."
    },
    gallery: {
      eyebrow: "Huit petites personnalités",
      title: "Qui t'accompagnera ?",
      description: "Découvre les huit personnages illustrés. Dans le prototype actuel, tu prends soin d'un compagnon choisi ; des besoins plus individuels et des aventures partagées sont prévus."
    },
    companions: {
      asterion: {
        species: "Dragon des étoiles",
        description: "Un petit gardien paisible au regard attentif et au grand cœur.",
        alt: "Asterion, un petit dragon des étoiles doré et bleu azur"
      },
      rabbit: {
        species: "Lapin des étoiles",
        description: "De ses pattes légères, Liora découvre les petites merveilles du chemin.",
        alt: "Liora, un lapin des étoiles blanc lunaire et lavande"
      },
      cat: {
        species: "Chat des étoiles",
        description: "Nyra observe avec attention et trouve les coins les plus douillets pour les moments calmes.",
        alt: "Nyra, un chat des étoiles gris anthracite aux yeux verts"
      },
      orc: {
        species: "Jeune orc",
        description: "Brumo a un grand cœur et aime les petites aventures à partager.",
        alt: "Brumo, un jeune orc amical en armure aubergine et bronze"
      },
      pony: {
        species: "Poney des étoiles",
        description: "Caelo regarde avec curiosité derrière le prochain nuage et apporte un peu d'aventure.",
        alt: "Caelo, un poney des étoiles blanc à la crinière bleu ciel"
      },
      fairy: {
        species: "Fée de lumière",
        description: "Selya trouve une raison de s'émerveiller dans la plus petite lueur.",
        alt: "Selya, une petite fée de lumière aux cheveux roses et aux ailes délicates"
      },
      dog: {
        species: "Chien des étoiles",
        description: "Fenn aime rester à tes côtés et se réjouit de chaque chemin parcouru ensemble.",
        alt: "Fenn, un chien des étoiles couleur caramel aux yeux bleus"
      },
      elf: {
        species: "Elfe des bois",
        description: "Aelira écoute patiemment la forêt et remarque ce qui échappe aux autres.",
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
      tagline: "Starfriends · Petits amis, histoires partagées.",
      status: "En développement · Prototype de soin pour les comptes de test autorisés"
    },
    login: {
      eyebrow: "Heureux de te revoir",
      title: "Partage un petit moment avec ton Starfriend.",
      description: "Connecte-toi avec ton compte autorisé pour essayer le prototype de soin. Tu seras redirigé vers notre service de connexion.",
      submit: "Me connecter avec mon compte",
      unavailableTitle: "La connexion n'est pas encore disponible.",
      unavailableText: "La connexion n'est pas encore configurée dans cet environnement. Tu peux découvrir les Starfriends sur la page d'accueil et réessayer plus tard.",
      denied: "Ton compte n'a pas encore accès au prototype de soin. Demande l'accès au responsable du projet.",
      error: "La connexion n'a pas pu aboutir. Merci de réessayer.",
      back: "Retour à l'accueil"
    },
    care: {
      legacyLanguage: "L'espace de soin est actuellement en allemand. Ses actions, bulles de dialogue et son historique seront traduits lors d'une prochaine étape.",
      back: "Retour à l'accueil"
    },
    errors: {
      title: "Cela n'a pas fonctionné cette fois.",
      description: "Cette page n'a pas pu être chargée. Merci de réessayer.",
      retry: "Réessayer",
      loading: "Un petit instant …"
    }
  },
  es: {
    meta: {
      title: "Starfriends · Pequeños amigos, historias compartidas",
      description: "Conoce a Asterion y los Starfriends: un proyecto ilustrado con cariño sobre compañeros virtuales, pequeños momentos de cuidado e historias compartidas."
    },
    nav: {
      home: "Inicio",
      about: "La idea",
      companions: "Los Starfriends",
      roadmap: "Más adelante",
      signIn: "Iniciar sesión",
      care: "Mi compañero",
      language: "Idioma",
      apply: "Aplicar",
      skip: "Saltar al contenido"
    },
    hero: {
      eyebrow: "Te damos la bienvenida a Starfriends",
      title: "Un pequeño amigo. Tu propia historia.",
      description: "Un momento tranquilo, una mirada curiosa y un poco de tiempo juntos. Descubre a Asterion y sus amigos en un pequeño universo dibujado con cariño.",
      primary: "Iniciar sesión y probar",
      secondary: "Conocer a los amigos",
      note: "El proyecto sigue creciendo. El prototipo de cuidado está disponible para cuentas de prueba autorizadas."
    },
    about: {
      eyebrow: "La idea",
      title: "Los pequeños momentos juntos importan.",
      description: "Starfriends es un proyecto web inspirado en los Tamagotchi para niños y familias. Estamos creando un lugar acogedor para jugar, cuidar y descubrir.",
      careTitle: "Tiempo para estar juntos",
      careText: "En el prototipo actual puedes alimentar al compañero que elijas, jugar con él y dejarlo descansar.",
      devicesTitle: "En casa, en tu navegador",
      devicesText: "No necesitas instalar ningún juego. La web está pensada para móviles, tabletas y ordenadores; el progreso se guarda en el servidor.",
      paceTitle: "Diversión, no obligaciones",
      paceText: "Queremos un día a día agradable con tu compañero. Las pausas y una vuelta tranquila después de un tiempo fuera forman parte de las mejoras previstas."
    },
    gallery: {
      eyebrow: "Ocho pequeñas personalidades",
      title: "¿Quién te acompañará?",
      description: "Conoce a los ocho personajes ilustrados. En el prototipo actual cuidas de un compañero elegido; más necesidades individuales y aventuras compartidas están previstas para más adelante."
    },
    companions: {
      asterion: {
        species: "Dragón de las estrellas",
        description: "Un pequeño guardián tranquilo, de mirada atenta y corazón cálido.",
        alt: "Asterion, un pequeño dragón de las estrellas dorado y azul celeste"
      },
      rabbit: {
        species: "Conejo de las estrellas",
        description: "Con sus suaves patitas, Liora descubre pequeñas maravillas junto al camino.",
        alt: "Liora, un conejo de las estrellas blanco lunar y lavanda"
      },
      cat: {
        species: "Gato de las estrellas",
        description: "Nyra observa con atención y encuentra los rincones más acogedores para los momentos tranquilos.",
        alt: "Nyra, un gato de las estrellas gris antracita con ojos verdes"
      },
      orc: {
        species: "Orco joven",
        description: "Brumo tiene un gran corazón y disfruta de las pequeñas aventuras en compañía.",
        alt: "Brumo, un orco joven y amable con armadura color berenjena y bronce"
      },
      pony: {
        species: "Poni de las estrellas",
        description: "Caelo mira con curiosidad detrás de la siguiente nube y trae un poquito de aventura.",
        alt: "Caelo, un poni de las estrellas blanco con crin azul cielo"
      },
      fairy: {
        species: "Hada de luz",
        description: "Selya encuentra una razón para maravillarse incluso en la luz más pequeña.",
        alt: "Selya, una pequeña hada de luz con pelo rosa y alas delicadas"
      },
      dog: {
        species: "Perro de las estrellas",
        description: "A Fenn le encanta estar a tu lado y espera con ilusión cada camino compartido.",
        alt: "Fenn, un perro de las estrellas color caramelo con ojos azules"
      },
      elf: {
        species: "Elfa del bosque",
        description: "Aelira escucha al bosque con paciencia y descubre lo que otros pasan por alto.",
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
      tagline: "Starfriends · Pequeños amigos, historias compartidas.",
      status: "En desarrollo · Prototipo de cuidado para cuentas de prueba autorizadas"
    },
    login: {
      eyebrow: "Qué bien verte de nuevo",
      title: "Comparte un pequeño momento con tu Starfriend.",
      description: "Inicia sesión con tu cuenta autorizada para probar el prototipo de cuidado. Te llevaremos a nuestro servicio de inicio de sesión.",
      submit: "Iniciar sesión con mi cuenta",
      unavailableTitle: "El inicio de sesión aún no está disponible.",
      unavailableText: "El inicio de sesión aún no está configurado en este entorno. Puedes conocer a los Starfriends en la página de inicio e intentarlo más tarde.",
      denied: "Tu cuenta aún no tiene acceso al prototipo de cuidado. Pide acceso al responsable del proyecto.",
      error: "No se pudo completar el inicio de sesión. Inténtalo de nuevo.",
      back: "Volver al inicio"
    },
    care: {
      legacyLanguage: "La pantalla de cuidado está actualmente en alemán. Sus acciones, bocadillos de diálogo e historial se traducirán en un próximo paso.",
      back: "Volver al inicio"
    },
    errors: {
      title: "Esta vez no ha funcionado.",
      description: "No se ha podido cargar esta página. Inténtalo de nuevo.",
      retry: "Volver a intentar",
      loading: "Un pequeño momento …"
    }
  }
};

export function getMessages(locale: Locale): Messages {
  return MESSAGES[locale];
}
