import { registerParser, type ParserInput } from "@parsers/index";
import { getHeader, maybeDecodeBase64, normalizePayload } from "@parsers/utils";

function extractConversationId(content: string): string | undefined {
  const match = content.match(/(?:thread|conversation)[^\d]*(\d{6,})/i);
  if (match) return match[1];
  const urlMatch = content.match(/airbnb\.com\/messaging\/thread\/(\d{6,})/i);
  return urlMatch?.[1];
}

function extractFromHeaders(headers: Record<string, string | undefined>): string | undefined {
  const candidates = ["reply-to", "from", "x-original-to"];
  for (const key of candidates) {
    const value = getHeader(headers, key);
    if (!value) continue;
    const match = value.match(/(?:thread|conversation)[^\d]*(\d{6,})/i);
    if (match) return match[1];
  }
  return undefined;
}

function extractGuestName(headers: Record<string, string | undefined>, content: string): string | undefined {
  const subject = getHeader(headers, "subject");
  if (subject) {
    const subjectMatch = subject.match(/messaggio da\s+(.+)/i);
    if (subjectMatch) return subjectMatch[1].trim();
  }
  const bodyMatch = content.match(/da\s+([-A-ZÀ-ÿ' ]{3,})/i);
  return bodyMatch?.[1]?.trim();
}

function extractMessageText(content: string): string | undefined {
  const lines = content
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length);

  let startIndex = lines.findIndex((line) => /messaggio(?:\s+da)?[:]?$/i.test(line) || /messaggio ricevuto/i.test(line));
  if (startIndex === -1) {
    startIndex = lines.findIndex((line) => /scrivi la tua risposta sopra/i.test(line));
  }

  if (startIndex >= 0) {
    const slice = lines.slice(startIndex + 1);
    const endIndex = slice.findIndex((line) => line.startsWith("Gestisci") || line.startsWith("Rispondi") || line.startsWith("https://"));
    const messageLines = endIndex >= 0 ? slice.slice(0, endIndex) : slice;
    const text = messageLines.join("\n").trim();
    if (text) return text;
  }

  const sanitizedLines = lines.filter(
    (line) =>
      !/^nuovo messaggio/i.test(line) &&
      !/^messaggio da/i.test(line) &&
      !/^numero di conferma/i.test(line) &&
      !/^scrivi la tua risposta sopra/i.test(line) &&
      !/^rispondi/i.test(line) &&
      !/^https?:\/\//i.test(line) &&
      !/^#+/i.test(line),
  );
  if (sanitizedLines.length) {
    return sanitizedLines[0];
  }

  const paragraph = content
    .split("\n\n")
    .map((section) => section.trim())
    .find((section) => section.length > 0);
  return paragraph;
}

registerParser({
  id: "airbnb_message",
  match: ({ headers }) => {
    const from = getHeader(headers, "from");
    return Boolean(from && from.toLowerCase().includes("reply.airbnb.com"));
  },
  parse: ({ body, html, headers }: ParserInput) => {
    const decodedBody = body ? maybeDecodeBase64(body) : body;
    const decodedHtml = html ? maybeDecodeBase64(html) : html;
    const content = normalizePayload(decodedBody, decodedHtml);
    const conversationId =
      extractConversationId(content) ??
      (decodedHtml ? extractConversationId(decodedHtml) : undefined) ??
      (decodedBody ? extractConversationId(decodedBody) : undefined) ??
      extractFromHeaders(headers);
    const guestName = extractGuestName(headers, content);
    const messageText = (() => {
      const primary = extractMessageText(content);
      if (primary) return primary;
      if (decodedBody) {
        const fallback = extractMessageText(decodedBody);
        if (fallback) return fallback;
      }
      if (decodedHtml) {
        const htmlFallback = extractMessageText(decodedHtml);
        if (htmlFallback) return htmlFallback;
      }
      return undefined;
    })();
    const sentAt = getHeader(headers, "date") ? new Date(getHeader(headers, "date") as string) : undefined;

    return {
      source: "airbnb_message",
      conversationId,
      guestName,
      messageText,
      channel: "airbnb",
      metadata: {
        subject: getHeader(headers, "subject"),
        sentAt: sentAt && !Number.isNaN(sentAt.getTime()) ? sentAt.toISOString() : undefined,
      },
      raw: { body, html },
    };
  },
});
