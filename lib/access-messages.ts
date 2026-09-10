import type { Locale } from "@/lib/i18n";

const messages = {
  de: {
    unavailableTitle: "Dein Zugang ist gerade nicht verfügbar", unavailableText: "Dein Konto ist gesperrt oder die Zugangsprüfung ist gerade nicht erreichbar. Versuche es später erneut. Bleibt das Problem bestehen, wende dich an einen Administrator.",
    refresh: "Erneut prüfen", logout: "Abmelden", home: "Startseite", care: "Zu deinem Sternenfreund", admin: "Benutzerverwaltung", intro: "Hier verwaltest du ausschließlich Zugangsrechte. Persönliche Tagebuchtexte und private Chats sind hier nicht zugänglich.",
    account: "Konto", desired: "Gewünschter Zugang", effective: "Aktueller Zugang", status: "Synchronisierung", save: "Freigabe speichern", none: "Kein Zugang", member: "Mitglied", administrator: "Administrator",
    pending: "Wartet auf Synchronisierung", applied: "Bestätigt", failed: "Wiederholung ausstehend", blocked: "Prüfung erforderlich", success: "Änderung vorgemerkt. Neue Rechte gelten erst nach bestätigter Synchronisierung.", error: "Änderung nicht möglich. Prüfe deine Anmeldung und ob mindestens ein Administrator verbleibt.",
    audit: "Letzte Rechteänderungen", empty: "Noch keine weiteren Anmeldungen vorhanden.", playerName: "Spielername", noPlayerName: "Noch nicht festgelegt"
  },
  en: {
    unavailableTitle: "Your access is currently unavailable", unavailableText: "Your account is restricted or the access check is temporarily unavailable. Try again later. If this continues, contact an administrator.",
    refresh: "Check again", logout: "Sign out", home: "Home", care: "Visit your starfriend", admin: "User administration", intro: "Only access permissions are managed here. Personal diary text and private chats are not accessible here.",
    account: "Account", desired: "Desired access", effective: "Current access", status: "Synchronization", save: "Save access", none: "No access", member: "Member", administrator: "Administrator",
    pending: "Awaiting synchronization", applied: "Confirmed", failed: "Retry pending", blocked: "Review required", success: "Change queued. New access takes effect only after confirmed synchronization.", error: "The change could not be applied. Check your sign-in and ensure at least one administrator remains.",
    audit: "Recent permission changes", empty: "No other sign-ins yet.", playerName: "Player name", noPlayerName: "Not set yet"
  },
  fr: {
    unavailableTitle: "Ton accès est indisponible pour le moment", unavailableText: "Ton compte est restreint ou la vérification d'accès est momentanément indisponible. Réessaie plus tard. Si le problème persiste, contacte un administrateur.",
    refresh: "Vérifier à nouveau", logout: "Se déconnecter", home: "Accueil", care: "Voir ton compagnon", admin: "Gestion des utilisateurs", intro: "Seuls les droits d’accès sont gérés ici. Les textes du journal personnel et les conversations privées ne sont pas accessibles ici.",
    account: "Compte", desired: "Accès souhaité", effective: "Accès actuel", status: "Synchronisation", save: "Enregistrer l’accès", none: "Aucun accès", member: "Membre", administrator: "Administrateur",
    pending: "En attente", applied: "Confirmée", failed: "Nouvel essai prévu", blocked: "Vérification nécessaire", success: "Modification enregistrée. Les nouveaux droits prennent effet après confirmation de la synchronisation.", error: "Modification impossible. Vérifie ta connexion et assure-toi qu’un administrateur reste disponible.",
    audit: "Dernières modifications des droits", empty: "Aucune autre connexion pour le moment.", playerName: "Nom de joueur", noPlayerName: "Pas encore défini"
  },
  es: {
    unavailableTitle: "Tu acceso no está disponible ahora", unavailableText: "Tu cuenta está restringida o la comprobación de acceso no está disponible temporalmente. Inténtalo más tarde. Si el problema persiste, contacta con un administrador.",
    refresh: "Comprobar de nuevo", logout: "Cerrar sesión", home: "Inicio", care: "Visitar a tu compañero", admin: "Administración de usuarios", intro: "Aquí solo se gestionan permisos de acceso. Los textos del diario personal y los chats privados no son accesibles aquí.",
    account: "Cuenta", desired: "Acceso solicitado", effective: "Acceso actual", status: "Sincronización", save: "Guardar acceso", none: "Sin acceso", member: "Miembro", administrator: "Administrador",
    pending: "Pendiente", applied: "Confirmada", failed: "Reintento pendiente", blocked: "Revisión necesaria", success: "Cambio en espera. Los nuevos permisos solo se activan tras confirmar la sincronización.", error: "No se pudo aplicar el cambio. Comprueba tu sesión y que quede al menos un administrador.",
    audit: "Cambios recientes de permisos", empty: "Todavía no hay otros usuarios conectados.", playerName: "Nombre de jugador", noPlayerName: "Aún no definido"
  }
};

export function getAccessMessages(locale: Locale) { return messages[locale] ?? messages.en; }
