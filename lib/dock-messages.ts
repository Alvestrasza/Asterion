import type { Locale } from "./i18n";

const en = {
  unread: "Unread messages",
  collapse: "Collapse friends", expand: "Expand friends", manage: "Manage friends",
  requests: "Friend requests", loading: "Loading friends…", unavailable: "Friends are currently unavailable.",
  sessionEnded: "Your session has changed. Sign in again.", chat: "Open conversation with", unknown: "Status unavailable"
};
type Messages = { [K in keyof typeof en]: string };
const de: Messages = {
  unread: "Ungelesene Nachrichten",
  collapse: "Freundesliste einklappen", expand: "Freundesliste ausklappen", manage: "Freunde verwalten",
  requests: "Freundschaftsanfragen", loading: "Freunde werden geladen…", unavailable: "Freunde sind gerade nicht verfügbar.",
  sessionEnded: "Deine Sitzung hat sich geändert. Melde dich erneut an.", chat: "Unterhaltung öffnen mit", unknown: "Status nicht verfügbar"
};
const fr: Messages = {
  unread: "Messages non lus",
  collapse: "Réduire la liste d’amis", expand: "Développer la liste d’amis", manage: "Gérer les amis",
  requests: "Demandes d’amitié", loading: "Chargement des amis…", unavailable: "Les amis sont momentanément indisponibles.",
  sessionEnded: "Ta session a changé. Reconnecte-toi.", chat: "Ouvrir la conversation avec", unknown: "Statut indisponible"
};
const es: Messages = {
  unread: "Mensajes sin leer",
  collapse: "Contraer la lista de amigos", expand: "Expandir la lista de amigos", manage: "Gestionar amigos",
  requests: "Solicitudes de amistad", loading: "Cargando amigos…", unavailable: "Los amigos no están disponibles ahora.",
  sessionEnded: "Tu sesión ha cambiado. Inicia sesión de nuevo.", chat: "Abrir conversación con", unknown: "Estado no disponible"
};
export function getDockMessages(locale: Locale): Messages { return ({ de, en, fr, es })[locale] ?? en; }
