import type { Locale } from "./i18n";
const en = {
  title: "Friends", back: "My companion", username: "Player name", hint: "3–32 characters: a–z, 0–9, dot, dash or underscore. Choose a nickname, not your full name.",
  friendCode: "Your friend code", friendCodeHint: "Share this code with people you know. It is not a password. Requests still need your approval.",
  codeInvalid: "Enter the complete friend code in XXXXX-XXX-XXXXX format.",
  discoverable: "Allow friendship requests using my friend code", save: "Save", saved: "Saved.",
  search: "Find a friend", query: "Your friend's code (XXXXX-XXX-XXXXX)", find: "Search", noResult: "No matching player available.", request: "Send request", sent: "Request sent or already pending.",
  incoming: "Received requests", outgoing: "Sent requests", accepted: "Your friends", blocked: "Blocked players", empty: "Nothing here yet.",
  accept: "Accept", decline: "Decline", remove: "Remove", cancel: "Withdraw", block: "Block", unblock: "Unblock",
  online: "Online", offline: "Offline", level: "Pet level", privacy: "Only confirmed friends can see your online status and pet level. Finding someone requires their friend code, not a name or email address. Online status may take up to 90 seconds to update.",
  error: "That did not work. Please try again.", rate: "Please wait before trying again. You can send up to five new requests per day.",
  unavailable: "This request is no longer available.", profileRequired: "Save a player name first.", usernameUnavailable: "That player name is not available.",
  cooldown: "You cannot send another request to this player yet. Please wait seven days.",
  choose: "Choose your first companion", chooseNote: "Who would you like to look after?", adopt: "Choose this companion", busy: "Please wait…", confirm: "Confirm this change?"
};
type Messages = { [K in keyof typeof en]: string };
const de: Messages = {
  title: "Freunde", back: "Mein Sternenfreund", username: "Spielername", hint: "3–32 Zeichen: a–z, 0–9, Punkt, Bindestrich oder Unterstrich. Wähle einen Spitznamen, nicht deinen vollständigen Namen.",
  friendCode: "Dein Freundescode", friendCodeHint: "Teile diesen Code mit Menschen, die du kennst. Er ist kein Passwort. Anfragen musst du weiterhin bestätigen.",
  codeInvalid: "Gib den vollständigen Freundescode im Format XXXXX-XXX-XXXXX ein.",
  discoverable: "Freundschaftsanfragen über meinen Freundescode erlauben", save: "Speichern", saved: "Gespeichert.",
  search: "Freund finden", query: "Freundescode des anderen Spielers (XXXXX-XXX-XXXXX)", find: "Suchen", noResult: "Kein passender Spieler verfügbar.", request: "Anfrage senden", sent: "Anfrage gesendet oder bereits vorhanden.",
  incoming: "Erhaltene Anfragen", outgoing: "Gesendete Anfragen", accepted: "Deine Freunde", blocked: "Blockierte Spieler", empty: "Hier ist noch niemand.",
  accept: "Annehmen", decline: "Ablehnen", remove: "Entfernen", cancel: "Zurückziehen", block: "Blockieren", unblock: "Freigeben",
  online: "Online", offline: "Offline", level: "Pet-Level", privacy: "Nur bestätigte Freunde sehen deinen Online-Status und Pet-Level. Zum Finden brauchst du den Freundescode, keinen Namen und keine E-Mail-Adresse. Der Online-Status kann bis zu 90 Sekunden verzögert sein.",
  error: "Das hat nicht geklappt. Bitte versuche es erneut.", rate: "Bitte warte vor dem nächsten Versuch. Du kannst täglich bis zu fünf neue Anfragen senden.",
  unavailable: "Diese Anfrage ist nicht mehr verfügbar.", profileRequired: "Speichere zuerst einen Spielernamen.", usernameUnavailable: "Dieser Spielername ist nicht verfügbar.",
  cooldown: "Du kannst diesem Spieler noch keine neue Anfrage senden. Bitte warte sieben Tage.",
  choose: "Wähle deinen ersten Sternenfreund", chooseNote: "Um wen möchtest du dich kümmern?", adopt: "Diesen Sternenfreund wählen", busy: "Einen Moment…", confirm: "Diese Änderung bestätigen?"
};
const fr: Messages = {
  title: "Amis", back: "Mon compagnon", username: "Pseudo", hint: "3 à 32 caractères : a–z, 0–9, point, tiret ou tiret bas. Choisis un pseudo, pas ton nom complet.",
  friendCode: "Ton code ami", friendCodeHint: "Partage ce code avec des personnes que tu connais. Ce n’est pas un mot de passe. Tu dois toujours accepter les demandes.",
  codeInvalid: "Saisis le code ami complet au format XXXXX-XXX-XXXXX.",
  discoverable: "Autoriser les demandes d’amitié avec mon code ami", save: "Enregistrer", saved: "Enregistré.",
  search: "Trouver un ami", query: "Code de ton ami (XXXXX-XXX-XXXXX)", find: "Rechercher", noResult: "Aucun joueur correspondant disponible.", request: "Envoyer une demande", sent: "Demande envoyée ou déjà en attente.",
  incoming: "Demandes reçues", outgoing: "Demandes envoyées", accepted: "Tes amis", blocked: "Joueurs bloqués", empty: "Personne pour le moment.",
  accept: "Accepter", decline: "Refuser", remove: "Retirer", cancel: "Annuler", block: "Bloquer", unblock: "Débloquer",
  online: "En ligne", offline: "Hors ligne", level: "Niveau du compagnon", privacy: "Seuls tes amis confirmés voient ton statut et le niveau de ton compagnon. Pour trouver quelqu’un, utilise son code ami, pas son nom ni son e-mail. Le statut peut avoir 90 secondes de retard.",
  error: "Cela n’a pas fonctionné. Réessaie.", rate: "Patiente avant de réessayer. Tu peux envoyer cinq nouvelles demandes par jour.", unavailable: "Cette demande n’est plus disponible.", profileRequired: "Enregistre d’abord un pseudo.", usernameUnavailable: "Ce pseudo n’est pas disponible.", cooldown: "Attends sept jours avant d’envoyer une nouvelle demande à ce joueur.",
  choose: "Choisis ton premier compagnon", chooseNote: "De qui veux-tu prendre soin ?", adopt: "Choisir ce compagnon", busy: "Un instant…", confirm: "Confirmer ce changement ?"
};
const es: Messages = {
  title: "Amigos", back: "Mi compañero", username: "Nombre de jugador", hint: "Entre 3 y 32 caracteres: a–z, 0–9, punto, guion o guion bajo. Elige un apodo, no tu nombre completo.",
  friendCode: "Tu código de amigo", friendCodeHint: "Comparte este código con personas que conoces. No es una contraseña. Debes seguir aceptando las solicitudes.",
  codeInvalid: "Introduce el código de amigo completo con el formato XXXXX-XXX-XXXXX.",
  discoverable: "Permitir solicitudes de amistad con mi código de amigo", save: "Guardar", saved: "Guardado.",
  search: "Buscar un amigo", query: "Código de tu amigo (XXXXX-XXX-XXXXX)", find: "Buscar", noResult: "No hay ningún jugador disponible que coincida.", request: "Enviar solicitud", sent: "Solicitud enviada o ya pendiente.",
  incoming: "Solicitudes recibidas", outgoing: "Solicitudes enviadas", accepted: "Tus amigos", blocked: "Jugadores bloqueados", empty: "Todavía no hay nadie.",
  accept: "Aceptar", decline: "Rechazar", remove: "Eliminar", cancel: "Retirar", block: "Bloquear", unblock: "Desbloquear",
  online: "En línea", offline: "Desconectado", level: "Nivel de la mascota", privacy: "Solo los amigos confirmados ven tu estado y el nivel de tu mascota. Para encontrar a alguien necesitas su código de amigo, no su nombre ni su correo. El estado puede tardar hasta 90 segundos en actualizarse.",
  error: "No ha funcionado. Inténtalo de nuevo.", rate: "Espera antes de volver a intentarlo. Puedes enviar cinco solicitudes nuevas al día.", unavailable: "Esta solicitud ya no está disponible.", profileRequired: "Guarda primero un nombre de jugador.", usernameUnavailable: "Ese nombre no está disponible.", cooldown: "Espera siete días antes de enviar otra solicitud a este jugador.",
  choose: "Elige tu primer compañero", chooseNote: "¿A quién quieres cuidar?", adopt: "Elegir este compañero", busy: "Un momento…", confirm: "¿Confirmar este cambio?"
};
export function getSocialMessages(locale: Locale): Messages { return ({ de, en, fr, es })[locale] ?? en; }
