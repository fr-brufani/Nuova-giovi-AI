import { registerParser, type ParserInput } from "@parsers/index";
import { getHeader, maybeDecodeBase64, normalizePayload } from "@parsers/utils";

function extractReservationIdFromString(content: string): string | undefined {
  const emailMatch = content.match(/(\d{6,})-[A-Z0-9]+\.[A-Z0-9]+@[a-z.]*mchat\.booking\.com/i);
  if (emailMatch) return emailMatch[1];
  const genericMatch = content.match(/numero di conferma[:=\s]+(\d{6,})/i);
  return genericMatch?.[1];
}

function extractReservationId(headers: Record<string, string | undefined>, content: string): string | undefined {
  const candidates = [
    getHeader(headers, "from"),
    getHeader(headers, "reply-to"),
    getHeader(headers, "to"),
    getHeader(headers, "x-bme-id"),
    getHeader(headers, "return-path"),
  ].filter(Boolean) as string[];

  for (const value of candidates) {
    const match = extractReservationIdFromString(value);
    if (match) return match;
  }
  return extractReservationIdFromString(content);
}

function extractGuestName(headers: Record<string, string | undefined>, content: string): string | undefined {
  const from = getHeader(headers, "from");
  const fromMatch = from?.match(/"([^"]+?)\s+via Booking\.com"/i);
  if (fromMatch) return fromMatch[1].trim();
  const subject = getHeader(headers, "subject");
  const subjectMatch = subject?.match(/messaggio da\s+(.+)/i);
  if (subjectMatch) return subjectMatch[1].trim();
  const bodyMatch = content.match(/messaggio da\s+([-A-ZÀ-ÿ' ]+)/i);
  return bodyMatch?.[1]?.trim();
}

function extractMessageText(content: string): string | undefined {
  const decoded = content.replace(/\r/g, "");
  const afterConfirmationSplit = decoded.split(/numero di conferma[:=\s]+\d{6,}/i);
  if (afterConfirmationSplit.length > 1) {
    const candidate = afterConfirmationSplit[1]
      .split(/(?:^|\n)\s*(?:Gestisci|Rispondi|https?:\/\/)/i)[0]
      .replace(/\n{2,}/g, "\n")
      .trim();
    if (candidate) {
      const firstParagraph = candidate.split(/\n{2,}/)[0].trim();
      if (firstParagraph) return firstParagraph;
    }
  }
  const sections = decoded.split(/--+\s*/);
  for (const section of sections) {
    const trimmed = section.trim();
    if (!trimmed) continue;
    if (/numero di conferma/i.test(trimmed)) {
      const paragraphs = trimmed.split(/\n{2,}/).map((p) => p.trim());
      const candidate = paragraphs.find((p) => p && !/^numero di conferma/i.test(p));
      if (candidate) return candidate;
    }
  }

  const lines = decoded
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length);

  const startIndex = lines.findIndex((line) => /nuovo messaggio|messaggio ricevuto/i.test(line));
  if (startIndex >= 0) {
    const slice = lines.slice(startIndex + 1);
    const endIndex = slice.findIndex((line) => /^gestisci|^rispondi|^https?:\/\//i.test(line));
    const messageLines = endIndex >= 0 ? slice.slice(0, endIndex) : slice;
    const text = messageLines.join("\n").trim();
    if (text) return text;
  }

  return lines.length ? lines[0] : undefined;
}

registerParser({
  id: "booking_chat",
  match: ({ headers }) => {
    const from = getHeader(headers, "from");
    return Boolean(from && from.toLowerCase().includes("@mchat.booking.com"));
  },
  parse: ({ body, html, headers }: ParserInput) => {
    const decodedBody = body ? maybeDecodeBase64(body) : body;
    const decodedHtml = html ? maybeDecodeBase64(html) : html;
    const content = normalizePayload(decodedBody, decodedHtml);

    const reservationId = extractReservationId(headers, content);
    const conversationId = reservationId;
    const guestName = extractGuestName(headers, content);
    const messageText = extractMessageText(content);
    const sentAtHeader = getHeader(headers, "date");
    const sentAt = sentAtHeader ? new Date(sentAtHeader) : undefined;

    return {
      source: "booking_chat",
      reservationId,
      conversationId,
      guestName,
      messageText,
      channel: "booking",
      metadata: {
        subject: getHeader(headers, "subject"),
        sentAt: sentAt && !Number.isNaN(sentAt.getTime()) ? sentAt.toISOString() : undefined,
      },
      raw: { body, html },
    };
  },
});
