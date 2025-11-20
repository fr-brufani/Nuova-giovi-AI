import { registerParser, type ParserInput } from "@parsers/index";
import { getHeader, normalizePayload, parseItalianDate, parseItalianRange } from "@parsers/utils";

function extractConversationId(content: string): string | undefined {
  const patterns = [
    /conversation(?:Id)?["']?\s*[:=]\s*["']?(\d{6,})/i,
    /airbnb\.com\/messaging\/thread\/(\d{6,})/i,
    /thread(?:Id)?[:\s]+(\d{6,})/i,
  ];
  for (const pattern of patterns) {
    const match = content.match(pattern);
    if (match) return match[1];
  }
  return undefined;
}

function extractConfirmationCode(content: string): string | undefined {
  const patterns = [
    /codice di conferma[:\s]+([A-Z0-9]{6,})/i,
    /confirmation code[:\s]+([A-Z0-9]{6,})/i,
    /codice[:\s]+([A-Z0-9]{6,})/i,
  ];
  for (const pattern of patterns) {
    const match = content.match(pattern);
    if (match) return match[1].trim();
  }
  return undefined;
}

function extractGuestName(content: string): string | undefined {
  const match = content.match(/(?:ospite|guest|nome ospite)[:\s]+([-A-ZÀ-ÿ' ]{3,})/i);
  return match?.[1]?.trim();
}

function extractPropertyName(content: string): string | undefined {
  const match = content.match(/(?:alloggio|struttura|listing|accommodation)[:\s]+([^\n]+)/i);
  if (match) return match[1].trim();
  const titleMatch = content.match(/titolo[:\s]+([^\n]+)/i);
  return titleMatch?.[1]?.trim();
}

function extractStayPeriod(content: string) {
  const range = parseItalianRange(content);
  if (range) return range;

  const checkIn = content.match(/check-?in[:\s]+([^\n]+)/i);
  const checkOut = content.match(/check-?out[:\s]+([^\n]+)/i);
  if (checkIn && checkOut) {
    const start = parseItalianDate(checkIn[1]);
    const end = parseItalianDate(checkOut[1]);
    if (start && end) {
      return { start, end };
    }
  }
  return undefined;
}

registerParser({
  id: "airbnb_confirm",
  match: ({ headers }) => {
    const from = getHeader(headers, "from");
    return Boolean(from && from.toLowerCase().includes("automated@airbnb.com"));
  },
  parse: ({ body, html, headers }: ParserInput) => {
    const content = normalizePayload(body, html);
    const conversationId =
      extractConversationId(content) ??
      (html ? extractConversationId(html) : undefined) ??
      (body ? extractConversationId(body) : undefined);
    const confirmationCode = extractConfirmationCode(content);
    const guestName = extractGuestName(content);
    const propertyName = extractPropertyName(content);
    const stayPeriod = extractStayPeriod(content);
    const toHeader = getHeader(headers, "to");
    const hostEmailMatch = toHeader?.match(/<([^>]+)>/);
    const hostEmail = hostEmailMatch ? hostEmailMatch[1].trim() : toHeader?.split(",")[0]?.trim();

    return {
      source: "airbnb_confirm",
      reservationId: confirmationCode,
      conversationId,
      guestName,
      hostEmail,
      stayPeriod,
      reservationStatus: confirmationCode ? "confirmed" : undefined,
      channel: "airbnb",
      propertyName,
      metadata: {
        propertyName,
        confirmationCode,
      },
      raw: { body, html },
    };
  },
});
