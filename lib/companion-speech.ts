// Version 1 is an editorial draft. Persist keys and typed parameters, never rendered locale text as the authority.
import { companionProfile, isCompanionKind, type CompanionKind } from "./companions.ts";
import { LOCALES, type Locale } from "./i18n.ts";
import type { CareAction, Mood } from "./care-engine.ts";

export const SPEECH_VERSION = 1;
export const SPEECH_CONTEXTS = [
  "greeting", "hungry", "tired", "joy", "lonely", "feed", "play", "pet",
  "resting", "satisfied", "sleep", "wake", "return", "levelUp",
  "achievement", "adoption", "alreadyAwake"
] as const;
export type SpeechContext = (typeof SPEECH_CONTEXTS)[number];
type VoiceContext = "greeting" | "hungry" | "tired" | "joy" | "lonely" | "feed" | "play" | "pet" | "sleep" | "wake" | "return" | "adoption";
export type SpeechParams = { level?: number };

const COMMON: Record<Locale, Record<SpeechContext, string>> = {
  de: {
    greeting: "Ein ruhiger Augenblick mit {name} tut gut.",
    hungry: "Eine Sternenbeere wäre für {name} jetzt willkommen.",
    tired: "{name} könnte sich eine Weile ausruhen.",
    joy: "{name} genießt diesen Augenblick.",
    lonely: "{name} freut sich über ein wenig Gesellschaft.",
    feed: "{name} hat die Sternenbeere genossen.",
    play: "{name} hatte Freude am gemeinsamen Spiel.",
    pet: "{name} genießt deine sanfte Berührung.",
    resting: "{name} ruht sich gerade aus. Später ist wieder Zeit.",
    satisfied: "{name} ist zufrieden und hebt sich das für später auf.",
    sleep: "{name} findet ruhig in den Schlaf.",
    wake: "{name} wird sanft wach.",
    return: "{name} freut sich, dich wiederzusehen.",
    levelUp: "{name} hat Stufe {level} erreicht.",
    achievement: "{name} hat einen neuen Erfolg erreicht.",
    adoption: "Mit {name} beginnt eine neue gemeinsame Geschichte.",
    alreadyAwake: "{name} ist schon wach."
  },
  en: {
    greeting: "A quiet moment with {name} feels good.",
    hungry: "A star berry would suit {name} now.",
    tired: "{name} could rest for a while.",
    joy: "{name} is enjoying this moment.",
    lonely: "{name} welcomes a little company.",
    feed: "{name} enjoyed the star berry.",
    play: "{name} had fun playing together.",
    pet: "{name} enjoys your gentle touch.",
    resting: "{name} is resting now. There will be time later.",
    satisfied: "{name} is content and can save this for later.",
    sleep: "{name} settles into peaceful sleep.",
    wake: "{name} wakes gently.",
    return: "{name} is glad to see you again.",
    levelUp: "{name} reached level {level}.",
    achievement: "{name} has earned a new achievement.",
    adoption: "A new story begins with {name}.",
    alreadyAwake: "{name} is already awake."
  },
  fr: {
    greeting: "Un moment de calme avec {name} fait du bien.",
    hungry: "Une baie étoilée ferait plaisir à {name}.",
    tired: "{name} pourrait se reposer un moment.",
    joy: "{name} savoure cet instant.",
    lonely: "{name} apprécie un peu de compagnie.",
    feed: "{name} a aimé la baie étoilée.",
    play: "{name} a pris plaisir à jouer avec toi.",
    pet: "{name} apprécie ta caresse délicate.",
    resting: "{name} se repose. Vous aurez du temps plus tard.",
    satisfied: "Pour {name}, c'est assez; on gardera cela pour plus tard.",
    sleep: "{name} s'endort paisiblement.",
    wake: "{name} se réveille doucement.",
    return: "Quel plaisir de revoir {name} !",
    levelUp: "{name} a atteint le niveau {level}.",
    achievement: "{name} a obtenu un nouveau succès.",
    adoption: "Une nouvelle histoire commence avec {name}.",
    alreadyAwake: "Une nouvelle journée a déjà commencé pour {name}."
  },
  es: {
    greeting: "Un momento tranquilo con {name} sienta bien.",
    hungry: "A {name} le vendría bien una baya estelar.",
    tired: "{name} podría descansar un rato.",
    joy: "{name} disfruta de este momento.",
    lonely: "{name} agradece un poco de compañía.",
    feed: "{name} disfrutó de la baya estelar.",
    play: "{name} disfrutó jugando contigo.",
    pet: "{name} disfruta de tu caricia suave.",
    resting: "{name} está descansando. Habrá tiempo después.",
    satisfied: "Por ahora, {name} ya tiene suficiente; lo guardaremos.",
    sleep: "{name} se duerme con calma.",
    wake: "{name} despierta suavemente.",
    return: "{name} se alegra de volver a verte.",
    levelUp: "{name} alcanzó el nivel {level}.",
    achievement: "{name} consiguió un nuevo logro.",
    adoption: "Comienza una nueva historia con {name}.",
    alreadyAwake: "El nuevo día ya ha comenzado para {name}."
  }
};

type SharedOnlyContext = "resting" | "satisfied" | "levelUp" | "achievement" | "alreadyAwake";
const COMMON_ALT: Record<Locale, Record<SharedOnlyContext, string>> = {
  de: {
    resting: "Eine Pause tut {name} gerade gut.",
    satisfied: "Für {name} ist das im Moment genug.",
    levelUp: "Ein neuer Stern: {name} ist nun auf Stufe {level}.",
    achievement: "Ein weiterer kleiner Erfolg für {name}.",
    alreadyAwake: "Der neue Tag hat für {name} schon begonnen."
  },
  en: {
    resting: "A little rest is good for {name} now.",
    satisfied: "That is enough for {name} right now.",
    levelUp: "A new star: {name} is now level {level}.",
    achievement: "Another little achievement for {name}.",
    alreadyAwake: "The new day has already begun for {name}."
  },
  fr: {
    resting: "Un peu de repos fera du bien à {name}.",
    satisfied: "Pour le moment, {name} n'en a pas besoin davantage.",
    levelUp: "Une nouvelle étoile : {name} passe au niveau {level}.",
    achievement: "Un petit succès de plus pour {name}.",
    alreadyAwake: "La journée a déjà commencé pour {name}."
  },
  es: {
    resting: "Un poco de descanso le sentará bien a {name}.",
    satisfied: "Por ahora, {name} no necesita más.",
    levelUp: "Una estrella nueva: {name} ya está en el nivel {level}.",
    achievement: "Un pequeño logro más para {name}.",
    alreadyAwake: "El día ya ha empezado para {name}."
  }
};

const VOICES: Record<Locale, Record<CompanionKind, Record<VoiceContext, string>>> = {
  de: {
    asterion: {
      greeting: "Asterion hält einen stillen Sternenplatz für dich frei.",
      hungry: "Asterion betrachtet die Sternenbeeren mit ruhigem Interesse.",
      tired: "Asterion lässt die Flügel sinken und sucht einen ruhigen Platz.",
      joy: "Asterion leuchtet warm, als wäre alles für einen Moment in Ordnung.",
      lonely: "Asterion rückt behutsam näher und wartet auf gemeinsame Zeit.",
      feed: "Asterion nimmt die Sternenbeere und nickt dir zufrieden zu.",
      play: "Asterion folgt dem Lichtfunken und behält dich dabei im Blick.",
      pet: "Asterion lehnt sich an deine Hand; sein Sternenglanz wird wärmer.",
      sleep: "Asterion faltet die Flügel und wacht nun im Traum über die Sterne.",
      wake: "Asterion öffnet die Augen und begrüßt dich mit leisem Funkeln.",
      return: "Asterion erkennt dich wieder und macht dir still einen Platz.",
      adoption: "Asterion beginnt eure gemeinsame Chronik mit einem ruhigen Licht."
    },
    rabbit: {
      greeting: "Liora hebt neugierig die Ohren und lauscht deinem Schritt.",
      hungry: "Liora schnuppert vorsichtig nach einer Sternenbeere.",
      tired: "Liora legt die Ohren an und sucht ein weiches Plätzchen.",
      joy: "Liora hüpft leichtfüßig über einen kleinen Lichtpfad.",
      lonely: "Liora schaut neugierig zu dir und bleibt in deiner Nähe.",
      feed: "Liora knabbert behutsam und schaut dann zufrieden auf.",
      play: "Liora entdeckt hinter jedem Lichtfunken einen neuen Weg.",
      pet: "Liora hält still und genießt deine behutsame Hand.",
      sleep: "Liora kuschelt sich ein und träumt von hellen Pfaden.",
      wake: "Liora streckt sich und hebt neugierig die Ohren.",
      return: "Liora erkennt deinen Schritt und hoppelt dir entgegen.",
      adoption: "Liora folgt einem neuen Lichtpfad an deine Seite."
    },
    cat: {
      greeting: "Nyra beobachtet dich erst, dann blinzelt sie vertraut.",
      hungry: "Nyra mustert die Sternenbeere mit prüfendem Blick.",
      tired: "Nyra sucht sich selbst einen stillen Platz zum Ausruhen.",
      joy: "Nyra lässt einen zufriedenen Blick durch die Sterne wandern.",
      lonely: "Nyra bleibt in deiner Nähe, ohne ihren eigenen Platz aufzugeben.",
      feed: "Nyra prüft die Sternenbeere und nimmt sie dann zufrieden an.",
      play: "Nyra fängt den Lichtfunken mit einem überraschend schnellen Satz.",
      pet: "Nyra erlaubt eine sanfte Berührung und schnurrt ganz leise.",
      sleep: "Nyra wählt ihren Lieblingsplatz und schließt die Augen.",
      wake: "Nyra blinzelt und betrachtet den neuen Tag ganz genau.",
      return: "Nyra sieht dich kommen; ihr vertrautes Blinzeln sagt genug.",
      adoption: "Nyra wählt einen Platz in deiner Nähe und bleibt."
    },
    orc: {
      greeting: "Brumo winkt dir mit einem großen, freundlichen Lächeln.",
      hungry: "Brumo freut sich sichtbar über den Gedanken an eine Sternenbeere.",
      tired: "Brumo gähnt herzlich und gönnt sich eine Pause.",
      joy: "Brumo lacht so warm, dass selbst die Sterne heller wirken.",
      lonely: "Brumo rückt ein Stück näher und bietet dir Gesellschaft an.",
      feed: "Brumo bedankt sich begeistert für die Sternenbeere.",
      play: "Brumo jagt lachend dem Lichtfunken nach.",
      pet: "Brumo lächelt breit und lässt die Schultern entspannt sinken.",
      sleep: "Brumo findet einen sicheren Platz und schläft friedlich ein.",
      wake: "Brumo streckt sich und schenkt dir ein fröhliches Guten Morgen.",
      return: "Brumo begrüßt dich, als hätte er einen schönen Tag zu erzählen.",
      adoption: "Brumo öffnet dir sein großes Herz und beginnt mit dir."
    },
    pony: {
      greeting: "Caelo scharrt voller Entdeckerlust mit dem Huf.",
      hungry: "Caelo hält auf seinem Weg nach einer Sternenbeere Ausschau.",
      tired: "Caelo macht eine Pause, bevor der nächste Weg beginnt.",
      joy: "Caelo galoppiert ein Stück, als läge der Himmel offen vor ihm.",
      lonely: "Caelo lädt dich ein, ein Stück des Weges mitzugehen.",
      feed: "Caelo nimmt die Sternenbeere und schnaubt zufrieden.",
      play: "Caelo folgt dem Lichtfunken in einem freudigen Bogen.",
      pet: "Caelo senkt den Kopf und genießt deine Nähe.",
      sleep: "Caelo ruht die Hufe aus und träumt von weiten Wegen.",
      wake: "Caelo hebt den Kopf: Ein neuer Weg wartet.",
      return: "Caelo trabt dir entgegen, bereit für euren nächsten Weg.",
      adoption: "Caelo lädt dich auf einen neuen gemeinsamen Weg ein."
    },
    fairy: {
      greeting: "Selya zeichnet einen kleinen Lichtkreis zur Begrüßung.",
      hungry: "Selya betrachtet die Sternenbeere wie ein winziges Wunder.",
      tired: "Selyas Flügel werden still; ein wenig Ruhe tut gut.",
      joy: "Selya tanzt spielerisch durch einen Schimmer aus Licht.",
      lonely: "Selya lässt ein sanftes Licht bei dir schweben.",
      feed: "Selya nimmt die Sternenbeere und lässt sie kurz funkeln.",
      play: "Selya wirbelt lachend um den Lichtfunken.",
      pet: "Selya lächelt und ein warmes Leuchten umgibt euch.",
      sleep: "Selya lässt das Licht leiser werden und ruht sich aus.",
      wake: "Selya streckt die Flügel und lässt ein Licht aufblitzen.",
      return: "Selya begrüßt dich mit einem kleinen Tanz aus Licht.",
      adoption: "Selya bringt ein kleines Wunder in eure neue Geschichte."
    },
    dog: {
      greeting: "Fenn kommt freundlich zu dir und bleibt an deiner Seite.",
      hungry: "Fenn schaut hoffnungsvoll zur Sternenbeere und dann zu dir.",
      tired: "Fenn legt sich in deiner Nähe für eine Pause hin.",
      joy: "Fenn wedelt begeistert und sucht dein Lächeln.",
      lonely: "Fenn setzt sich zu dir und freut sich über gemeinsame Zeit.",
      feed: "Fenn genießt die Sternenbeere und wedelt dankbar.",
      play: "Fenn saust dem Lichtfunken nach und kehrt zu dir zurück.",
      pet: "Fenn lehnt sich zufrieden an deine Hand.",
      sleep: "Fenn rollt sich in deiner Nähe ein und schläft.",
      wake: "Fenn steht auf und begrüßt dich voller Freude.",
      return: "Fenn erkennt dich sofort und kommt freudig angelaufen.",
      adoption: "Fenn findet einen Platz an deiner Seite."
    },
    elf: {
      greeting: "Aelira lauscht dem Wind und schenkt dir ein ruhiges Lächeln.",
      hungry: "Aelira betrachtet die Sternenbeere mit geduldiger Neugier.",
      tired: "Aelira nimmt sich Zeit für eine Pause unter den Sternen.",
      joy: "Aelira lächelt, als hätte der Wald ein gutes Geheimnis geteilt.",
      lonely: "Aelira lädt dich ein, einen stillen Moment zu teilen.",
      feed: "Aelira nimmt die Sternenbeere mit einem dankbaren Lächeln.",
      play: "Aelira folgt dem Lichtfunken wie einer Spur im Wald.",
      pet: "Aelira schließt kurz die Augen und genießt die Wärme.",
      sleep: "Aelira ruht im Schutz eines stillen Sternenhains.",
      wake: "Aelira öffnet die Augen und begrüßt den neuen Tag.",
      return: "Aelira erkennt deinen Schritt und heißt dich ruhig willkommen.",
      adoption: "Aelira beginnt mit dir einen neuen Pfad."
    }
  },
  en: {
    asterion: {
      greeting: "Asterion keeps a quiet place among the stars for you.",
      hungry: "Asterion regards the star berries with calm interest.",
      tired: "Asterion lowers his wings and looks for a quiet place.",
      joy: "Asterion glows warmly, as if all is well for a moment.",
      lonely: "Asterion moves gently closer and welcomes time together.",
      feed: "Asterion takes the star berry and nods with contentment.",
      play: "Asterion follows the spark while keeping you in sight.",
      pet: "Asterion leans into your hand; his starlight grows warmer.",
      sleep: "Asterion folds his wings and watches over stars in his dreams.",
      wake: "Asterion opens his eyes and greets you with a quiet glimmer.",
      return: "Asterion recognizes you and quietly makes room beside him.",
      adoption: "Asterion begins your shared chronicle with a calm light."
    },
    rabbit: {
      greeting: "Liora lifts her ears, curious about your footsteps.",
      hungry: "Liora gently sniffs for a star berry.",
      tired: "Liora lowers her ears and seeks a soft place to rest.",
      joy: "Liora hops lightly along a little path of light.",
      lonely: "Liora looks your way and stays close by.",
      feed: "Liora nibbles carefully, then looks up contentedly.",
      play: "Liora discovers a new path behind every spark.",
      pet: "Liora stays still and enjoys your gentle hand.",
      sleep: "Liora curls up and dreams of bright paths.",
      wake: "Liora stretches and lifts her curious ears.",
      return: "Liora knows your steps and hops over to meet you.",
      adoption: "Liora follows a new path of light to your side."
    },
    cat: {
      greeting: "Nyra studies you first, then gives a familiar blink.",
      hungry: "Nyra inspects the star berry with a thoughtful gaze.",
      tired: "Nyra chooses a quiet resting place for herself.",
      joy: "Nyra lets a pleased gaze drift across the stars.",
      lonely: "Nyra stays near without giving up her own space.",
      feed: "Nyra checks the star berry, then accepts it with pleasure.",
      play: "Nyra catches the spark with a surprisingly swift leap.",
      pet: "Nyra welcomes a gentle touch and purrs very softly.",
      sleep: "Nyra picks her favorite spot and closes her eyes.",
      wake: "Nyra blinks and studies the new day closely.",
      return: "Nyra sees you coming; her familiar blink says enough.",
      adoption: "Nyra chooses a place nearby and decides to stay."
    },
    orc: {
      greeting: "Brumo waves with a big, friendly smile.",
      hungry: "Brumo visibly brightens at the thought of a star berry.",
      tired: "Brumo gives a hearty yawn and takes a break.",
      joy: "Brumo laughs so warmly that even the stars seem brighter.",
      lonely: "Brumo moves closer and offers you company.",
      feed: "Brumo thanks you with delight for the star berry.",
      play: "Brumo chases the spark with a happy laugh.",
      pet: "Brumo smiles widely and lets his shoulders relax.",
      sleep: "Brumo finds a safe spot and falls peacefully asleep.",
      wake: "Brumo stretches and wishes you a cheerful morning.",
      return: "Brumo greets you as if he has a lovely day to share.",
      adoption: "Brumo opens his big heart to your new story."
    },
    pony: {
      greeting: "Caelo paws the ground, eager to explore.",
      hungry: "Caelo looks for a star berry along the way.",
      tired: "Caelo pauses before the next journey begins.",
      joy: "Caelo gallops a little, as if the sky lay open ahead.",
      lonely: "Caelo invites you to travel a little way together.",
      feed: "Caelo takes the star berry and snorts contentedly.",
      play: "Caelo follows the spark in a joyful arc.",
      pet: "Caelo lowers his head and enjoys your closeness.",
      sleep: "Caelo rests his hooves and dreams of open paths.",
      wake: "Caelo raises his head: a new path awaits.",
      return: "Caelo trots over, ready for your next journey.",
      adoption: "Caelo invites you onto a new path together."
    },
    fairy: {
      greeting: "Selya draws a tiny circle of light to say hello.",
      hungry: "Selya studies the star berry like a little wonder.",
      tired: "Selya's wings grow still; a little rest feels good.",
      joy: "Selya dances playfully through a shimmer of light.",
      lonely: "Selya lets a gentle light float beside you.",
      feed: "Selya takes the star berry and makes it sparkle briefly.",
      play: "Selya whirls around the spark with a laugh.",
      pet: "Selya smiles and a warm glow surrounds you both.",
      sleep: "Selya dims the light and settles down to rest.",
      wake: "Selya stretches her wings and flashes a little light.",
      return: "Selya greets you with a small dance of light.",
      adoption: "Selya brings a little wonder to your new story."
    },
    dog: {
      greeting: "Fenn comes over cheerfully and stays by your side.",
      hungry: "Fenn looks hopefully at the star berry, then at you.",
      tired: "Fenn lies down nearby for a little rest.",
      joy: "Fenn wags enthusiastically and looks for your smile.",
      lonely: "Fenn sits with you and welcomes time together.",
      feed: "Fenn enjoys the star berry and wags gratefully.",
      play: "Fenn races after the spark and returns to you.",
      pet: "Fenn leans contentedly into your hand.",
      sleep: "Fenn curls up near you and falls asleep.",
      wake: "Fenn gets up and greets you with delight.",
      return: "Fenn recognizes you at once and runs over happily.",
      adoption: "Fenn finds a place at your side."
    },
    elf: {
      greeting: "Aelira listens to the wind and offers a quiet smile.",
      hungry: "Aelira regards the star berry with patient curiosity.",
      tired: "Aelira takes time to rest beneath the stars.",
      joy: "Aelira smiles as if the forest shared a kind secret.",
      lonely: "Aelira invites you to share a quiet moment.",
      feed: "Aelira accepts the star berry with a grateful smile.",
      play: "Aelira follows the spark like a trail through the woods.",
      pet: "Aelira closes her eyes briefly and enjoys the warmth.",
      sleep: "Aelira rests in the shelter of a quiet star grove.",
      wake: "Aelira opens her eyes and welcomes the new day.",
      return: "Aelira recognizes your steps and welcomes you calmly.",
      adoption: "Aelira begins a new path with you."
    }
  },
  fr: {
    asterion: {
      greeting: "Asterion te garde une place paisible parmi les étoiles.",
      hungry: "Asterion observe les baies étoilées avec calme.",
      tired: "Asterion abaisse ses ailes et cherche un coin tranquille.",
      joy: "Asterion rayonne doucement, comme si tout allait bien.",
      lonely: "Asterion se rapproche avec douceur pour partager un moment.",
      feed: "Asterion prend la baie étoilée et te remercie d'un signe.",
      play: "Asterion suit l'étincelle sans te perdre de vue.",
      pet: "Asterion se blottit contre ta main; sa lumière se réchauffe.",
      sleep: "Asterion replie ses ailes et veille sur les étoiles en rêve.",
      wake: "Asterion ouvre les yeux et t'accueille d'une douce lueur.",
      return: "Asterion te reconnaît et te fait une place en silence.",
      adoption: "Asterion commence votre chronique dans une lumière paisible."
    },
    rabbit: {
      greeting: "Liora dresse les oreilles, curieuse de tes pas.",
      hungry: "Liora cherche doucement une baie étoilée.",
      tired: "Liora baisse les oreilles et cherche un endroit moelleux.",
      joy: "Liora bondit légèrement sur un petit sentier lumineux.",
      lonely: "Liora te regarde et reste tout près.",
      feed: "Liora grignote avec soin, puis relève la tête, ravie.",
      play: "Liora découvre un nouveau chemin derrière chaque étincelle.",
      pet: "Liora reste immobile et savoure ta main délicate.",
      sleep: "Liora se blottit et rêve de chemins lumineux.",
      wake: "Liora s'étire et dresse ses oreilles curieuses.",
      return: "Liora reconnaît tes pas et bondit à ta rencontre.",
      adoption: "Liora suit un nouveau chemin de lumière vers toi."
    },
    cat: {
      greeting: "Nyra t'observe d'abord, puis cligne des yeux en confiance.",
      hungry: "Nyra examine la baie étoilée avec attention.",
      tired: "Nyra choisit elle-même un endroit calme pour se reposer.",
      joy: "Nyra promène un regard satisfait parmi les étoiles.",
      lonely: "Nyra reste près de toi sans renoncer à son espace.",
      feed: "Nyra inspecte la baie, puis l'accepte avec plaisir.",
      play: "Nyra attrape l'étincelle d'un bond étonnamment vif.",
      pet: "Nyra accepte une douce caresse et ronronne tout bas.",
      sleep: "Nyra choisit son endroit favori et ferme les yeux.",
      wake: "Nyra cligne des yeux et observe la nouvelle journée.",
      return: "Nyra te voit venir; son clin d'œil familier suffit.",
      adoption: "Nyra choisit une place près de toi et décide de rester."
    },
    orc: {
      greeting: "Brumo te salue avec un grand sourire amical.",
      hungry: "Brumo s'illumine à l'idée d'une baie étoilée.",
      tired: "Brumo bâille de bon cœur et fait une pause.",
      joy: "Brumo rit si chaleureusement que les étoiles brillent plus fort.",
      lonely: "Brumo se rapproche et t'offre sa compagnie.",
      feed: "Brumo te remercie avec enthousiasme pour la baie.",
      play: "Brumo poursuit l'étincelle en riant.",
      pet: "Brumo sourit largement et détend les épaules.",
      sleep: "Brumo trouve un endroit sûr et s'endort paisiblement.",
      wake: "Brumo s'étire et te souhaite un joyeux matin.",
      return: "Brumo t'accueille comme s'il avait une belle journée à raconter.",
      adoption: "Brumo ouvre son grand cœur à votre nouvelle histoire."
    },
    pony: {
      greeting: "Caelo gratte le sol, impatient d'explorer.",
      hungry: "Caelo cherche une baie étoilée sur son chemin.",
      tired: "Caelo fait une pause avant la prochaine aventure.",
      joy: "Caelo galope un peu, comme si le ciel s'ouvrait devant lui.",
      lonely: "Caelo t'invite à parcourir un bout de chemin ensemble.",
      feed: "Caelo prend la baie étoilée et souffle de satisfaction.",
      play: "Caelo suit l'étincelle en dessinant un arc joyeux.",
      pet: "Caelo baisse la tête et apprécie ta présence.",
      sleep: "Caelo repose ses sabots et rêve de grands chemins.",
      wake: "Caelo relève la tête : un nouveau chemin l'attend.",
      return: "Caelo trotte vers toi, prêt pour votre prochaine aventure.",
      adoption: "Caelo t'invite sur un nouveau chemin à deux."
    },
    fairy: {
      greeting: "Selya dessine un petit cercle de lumière pour te saluer.",
      hungry: "Selya observe la baie étoilée comme une petite merveille.",
      tired: "Les ailes de Selya se posent; un peu de repos lui fait du bien.",
      joy: "Selya danse parmi les reflets de lumière.",
      lonely: "Selya laisse flotter une douce lumière près de toi.",
      feed: "Selya prend la baie et la fait briller un instant.",
      play: "Selya tourbillonne autour de l'étincelle en riant.",
      pet: "Selya sourit et une lueur chaleureuse vous entoure.",
      sleep: "Selya tamise sa lumière et se repose.",
      wake: "Selya étire ses ailes et fait jaillir une petite lueur.",
      return: "Selya t'accueille avec une petite danse de lumière.",
      adoption: "Selya apporte une petite merveille à votre histoire."
    },
    dog: {
      greeting: "Fenn vient joyeusement vers toi et reste à tes côtés.",
      hungry: "Fenn regarde la baie avec espoir, puis te regarde.",
      tired: "Fenn s'allonge près de toi pour se reposer.",
      joy: "Fenn remue la queue et cherche ton sourire.",
      lonely: "Fenn s'assoit avec toi et profite du moment partagé.",
      feed: "Fenn savoure la baie et remue la queue en remerciement.",
      play: "Fenn court après l'étincelle et revient vers toi.",
      pet: "Fenn se blottit contre ta main avec contentement.",
      sleep: "Fenn se roule en boule près de toi et s'endort.",
      wake: "Fenn se lève et t'accueille avec joie.",
      return: "Fenn te reconnaît aussitôt et accourt joyeusement.",
      adoption: "Fenn trouve sa place à tes côtés."
    },
    elf: {
      greeting: "Aelira écoute le vent et t'offre un sourire tranquille.",
      hungry: "Aelira observe la baie avec une patiente curiosité.",
      tired: "Aelira prend le temps de se reposer sous les étoiles.",
      joy: "Aelira sourit, comme si la forêt lui avait confié un secret.",
      lonely: "Aelira t'invite à partager un moment de calme.",
      feed: "Aelira accepte la baie avec un sourire reconnaissant.",
      play: "Aelira suit l'étincelle comme un sentier dans la forêt.",
      pet: "Aelira ferme brièvement les yeux et savoure la chaleur.",
      sleep: "Aelira se repose dans un bosquet paisible.",
      wake: "Aelira ouvre les yeux et accueille le nouveau jour.",
      return: "Aelira reconnaît tes pas et t'accueille avec calme.",
      adoption: "Aelira commence un nouveau chemin avec toi."
    }
  },
  es: {
    asterion: {
      greeting: "Asterion guarda para ti un lugar tranquilo entre las estrellas.",
      hungry: "Asterion mira las bayas estelares con sereno interés.",
      tired: "Asterion baja las alas y busca un rincón tranquilo.",
      joy: "Asterion brilla con calidez, como si todo estuviera bien.",
      lonely: "Asterion se acerca con cuidado para compartir un momento.",
      feed: "Asterion toma la baya estelar y te asiente con satisfacción.",
      play: "Asterion sigue la chispa sin perderte de vista.",
      pet: "Asterion se apoya en tu mano; su luz se vuelve más cálida.",
      sleep: "Asterion pliega las alas y vela por las estrellas en sueños.",
      wake: "Asterion abre los ojos y te saluda con un brillo suave.",
      return: "Asterion te reconoce y te hace sitio en silencio.",
      adoption: "Asterion comienza vuestra crónica con una luz serena."
    },
    rabbit: {
      greeting: "Liora levanta las orejas, curiosa por tus pasos.",
      hungry: "Liora olfatea con delicadeza en busca de una baya estelar.",
      tired: "Liora baja las orejas y busca un sitio mullido.",
      joy: "Liora salta ligera por un pequeño sendero de luz.",
      lonely: "Liora te mira y se queda cerca.",
      feed: "Liora mordisquea con cuidado y levanta la mirada contenta.",
      play: "Liora descubre un camino nuevo tras cada chispa.",
      pet: "Liora se queda quieta y disfruta de tu mano amable.",
      sleep: "Liora se acurruca y sueña con caminos luminosos.",
      wake: "Liora se estira y levanta sus orejas curiosas.",
      return: "Liora reconoce tus pasos y salta a tu encuentro.",
      adoption: "Liora sigue un nuevo sendero de luz hasta tu lado."
    },
    cat: {
      greeting: "Nyra te observa primero y luego parpadea con confianza.",
      hungry: "Nyra examina la baya estelar con mirada atenta.",
      tired: "Nyra elige por sí misma un lugar tranquilo para descansar.",
      joy: "Nyra contempla las estrellas con una mirada satisfecha.",
      lonely: "Nyra se queda cerca sin renunciar a su propio espacio.",
      feed: "Nyra examina la baya y después la acepta encantada.",
      play: "Nyra atrapa la chispa con un salto sorprendentemente rápido.",
      pet: "Nyra acepta una caricia suave y ronronea bajito.",
      sleep: "Nyra elige su lugar favorito y cierra los ojos.",
      wake: "Nyra parpadea y observa con atención el nuevo día.",
      return: "Nyra te ve llegar; su parpadeo familiar lo dice todo.",
      adoption: "Nyra elige un sitio cerca de ti y decide quedarse."
    },
    orc: {
      greeting: "Brumo te saluda con una gran sonrisa amistosa.",
      hungry: "Brumo se anima visiblemente al pensar en una baya estelar.",
      tired: "Brumo bosteza de buena gana y se toma un descanso.",
      joy: "Brumo ríe con tanta calidez que las estrellas parecen brillar más.",
      lonely: "Brumo se acerca y te ofrece compañía.",
      feed: "Brumo te agradece con entusiasmo la baya estelar.",
      play: "Brumo persigue la chispa entre risas.",
      pet: "Brumo sonríe ampliamente y relaja los hombros.",
      sleep: "Brumo encuentra un sitio seguro y se duerme en paz.",
      wake: "Brumo se estira y te desea una alegre mañana.",
      return: "Brumo te recibe como si tuviera un día bonito que contar.",
      adoption: "Brumo abre su gran corazón a vuestra nueva historia."
    },
    pony: {
      greeting: "Caelo rasca el suelo, deseando explorar.",
      hungry: "Caelo busca una baya estelar por el camino.",
      tired: "Caelo hace una pausa antes de la próxima aventura.",
      joy: "Caelo galopa un poco, como si el cielo se abriera delante.",
      lonely: "Caelo te invita a recorrer un trecho juntos.",
      feed: "Caelo toma la baya estelar y resopla satisfecho.",
      play: "Caelo sigue la chispa en un arco lleno de alegría.",
      pet: "Caelo baja la cabeza y disfruta de tu cercanía.",
      sleep: "Caelo descansa los cascos y sueña con caminos abiertos.",
      wake: "Caelo levanta la cabeza: espera un nuevo camino.",
      return: "Caelo trota hacia ti, listo para vuestra próxima aventura.",
      adoption: "Caelo te invita a recorrer un nuevo camino juntos."
    },
    fairy: {
      greeting: "Selya dibuja un pequeño círculo de luz para saludarte.",
      hungry: "Selya contempla la baya estelar como una pequeña maravilla.",
      tired: "Las alas de Selya se aquietan; le sienta bien descansar.",
      joy: "Selya baila entre destellos de luz.",
      lonely: "Selya deja flotar una luz suave a tu lado.",
      feed: "Selya toma la baya y la hace brillar un instante.",
      play: "Selya gira alrededor de la chispa entre risas.",
      pet: "Selya sonríe y os envuelve una luz cálida.",
      sleep: "Selya atenúa su luz y se acomoda para descansar.",
      wake: "Selya estira las alas y deja escapar un destello.",
      return: "Selya te recibe con un pequeño baile de luz.",
      adoption: "Selya trae una pequeña maravilla a vuestra historia."
    },
    dog: {
      greeting: "Fenn se acerca alegremente y permanece a tu lado.",
      hungry: "Fenn mira la baya con ilusión y luego te mira a ti.",
      tired: "Fenn se tumba cerca de ti para descansar.",
      joy: "Fenn mueve la cola con entusiasmo y busca tu sonrisa.",
      lonely: "Fenn se sienta contigo y disfruta del tiempo compartido.",
      feed: "Fenn saborea la baya y mueve la cola agradecido.",
      play: "Fenn corre tras la chispa y vuelve a tu lado.",
      pet: "Fenn se apoya contento en tu mano.",
      sleep: "Fenn se acurruca cerca de ti y se duerme.",
      wake: "Fenn se levanta y te saluda con alegría.",
      return: "Fenn te reconoce al instante y corre feliz hacia ti.",
      adoption: "Fenn encuentra su lugar a tu lado."
    },
    elf: {
      greeting: "Aelira escucha el viento y te ofrece una sonrisa serena.",
      hungry: "Aelira mira la baya con paciente curiosidad.",
      tired: "Aelira se toma tiempo para descansar bajo las estrellas.",
      joy: "Aelira sonríe como si el bosque compartiera un buen secreto.",
      lonely: "Aelira te invita a compartir un momento tranquilo.",
      feed: "Aelira acepta la baya con una sonrisa de gratitud.",
      play: "Aelira sigue la chispa como una senda por el bosque.",
      pet: "Aelira cierra los ojos un instante y disfruta del calor.",
      sleep: "Aelira descansa en un tranquilo bosque de estrellas.",
      wake: "Aelira abre los ojos y saluda al nuevo día.",
      return: "Aelira reconoce tus pasos y te recibe con calma.",
      adoption: "Aelira comienza un nuevo camino contigo."
    }
  }
};

const MOOD_CONTEXT: Record<Mood, SpeechContext> = {
  sleeping: "resting", hungry: "hungry", tired: "tired", lonely: "lonely",
  radiant: "joy", attentive: "greeting", calm: "greeting"
};

const MOOD_LABELS: Record<Locale, Record<Mood, string>> = {
  de: { sleeping: "Schläft", hungry: "Hungrig", tired: "Müde", lonely: "Sehnsüchtig", radiant: "Strahlend", attentive: "Aufmerksam", calm: "Geborgen" },
  en: { sleeping: "Sleeping", hungry: "Hungry", tired: "Tired", lonely: "Seeking company", radiant: "Radiant", attentive: "Attentive", calm: "Content" },
  fr: { sleeping: "Repos", hungry: "Petit creux", tired: "Besoin de repos", lonely: "Envie de compagnie", radiant: "Rayonnement", attentive: "À l'écoute", calm: "Sérénité" },
  es: { sleeping: "Descanso", hungry: "Con hambre", tired: "Necesita descanso", lonely: "Busca compañía", radiant: "Alegría", attentive: "Atención", calm: "Tranquilidad" }
};

const PLAYER_LEVEL: Record<Locale, string> = {
  de: "Du hast Stufe {level} erreicht.",
  en: "You reached level {level}.",
  fr: "Tu as atteint le niveau {level}.",
  es: "Alcanzaste el nivel {level}."
};
const OFFLINE_PENDING: Record<Locale, string> = {
  de: "Wird synchronisiert, sobald du wieder online bist.",
  en: "This will sync when you are online again.",
  fr: "Ce moment sera synchronisé dès ton retour en ligne.",
  es: "Este momento se sincronizará cuando vuelvas a conectarte."
};

function resolvedLocale(value: unknown): Locale {
  return typeof value === "string" && LOCALES.includes(value as Locale) ? value as Locale : "en";
}

function validLevel(value: unknown): value is number {
  return Number.isSafeInteger(value) && Number(value) >= 1 && Number(value) <= 99;
}

function interpolate(template: string, name: string, level?: number) {
  if (template.includes("{level}") && !validLevel(level)) return null;
  return template.replaceAll("{name}", name).replaceAll("{level}", String(level ?? ""));
}

export function chooseSpeechKey(kind: CompanionKind, context: SpeechContext, seed: string): string {
  if (!isCompanionKind(kind) || !SPEECH_CONTEXTS.includes(context)) throw new RangeError("Invalid speech context.");
  let hash = 2166136261;
  for (const char of seed) hash = Math.imul(hash ^ char.codePointAt(0)!, 16777619);
  return `v${SPEECH_VERSION}.${kind}.${context}.${hash >>> 31}`;
}

export function avoidRepeatedSpeechKey(preferred: string, previous: string | null | undefined): string {
  if (previous !== preferred || !/\.[01]$/.test(preferred)) return preferred;
  return preferred.slice(0, -1) + (preferred.endsWith("0") ? "1" : "0");
}

export function renderSpeech(key: string | null | undefined, locale: Locale | string, params: SpeechParams = {}): string | null {
  const match = /^v1\.([a-z]+)\.([A-Za-z]+)\.([01])$/.exec(key ?? "");
  if (!match || !isCompanionKind(match[1]) || !SPEECH_CONTEXTS.includes(match[2] as SpeechContext)) return null;
  const [, kind, rawContext, variant] = match;
  const context = rawContext as SpeechContext;
  const selected = resolvedLocale(locale);
  const specific = VOICES[selected][kind][context as VoiceContext];
  const template = variant === "0"
    ? specific ?? COMMON[selected][context]
    : specific ? COMMON[selected][context] : COMMON_ALT[selected][context as SharedOnlyContext];
  return interpolate(template, companionProfile(kind).name, params.level);
}

export function renderPlayerLevel(locale: Locale | string, level: number): string | null {
  return interpolate(PLAYER_LEVEL[resolvedLocale(locale)], "", level);
}

export function moodLabel(mood: Mood, locale: Locale | string): string {
  return MOOD_LABELS[resolvedLocale(locale)][mood];
}

export function careSpeechContext(action: CareAction, accepted: boolean, sleeping: boolean): SpeechContext {
  if (accepted) return action;
  if (sleeping) return "resting";
  if (action === "feed") return "satisfied";
  if (action === "play") return "tired";
  if (action === "wake") return "alreadyAwake";
  return "resting";
}

export function offlinePendingText(locale: Locale | string): string {
  return OFFLINE_PENDING[resolvedLocale(locale)];
}

export function speechForMood(mood: Mood, kind: CompanionKind, locale: Locale | string, seed: string): string {
  const context = MOOD_CONTEXT[mood];
  return renderSpeech(chooseSpeechKey(kind, context, seed), locale) ?? companionProfile(kind).name;
}

export function isSpeechContext(value: unknown): value is SpeechContext {
  return typeof value === "string" && SPEECH_CONTEXTS.includes(value as SpeechContext);
}
