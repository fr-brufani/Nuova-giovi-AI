import { registerParser, type ParserInput } from "@parsers/index";
import {
  extractBetweenMarkers,
  getHeader,
  normalizePayload,
  parseEuroNumber,
  parseItalianDate,
} from "@parsers/utils";

function extractReservationId(content: string, headers: Record<string, string | undefined>): string | undefined {
  const bodyMatch = content.match(/ID (?:Voucher|Prenotazione)[^\d]*(\d{6,})/i);
  if (bodyMatch) return bodyMatch[1];
  const subject = getHeader(headers, "subject");
  const subjectMatch = subject?.match(/ID\s*(\d{6,})/i);
  if (subjectMatch) return subjectMatch[1];
  return undefined;
}

function extractStatus(content: string): string | undefined {
  return content.match(/Stato Prenotazione[:=\s]+([A-Za-zÀ-ÿ ]+)/i)?.[1]?.trim();
}

function extractAgency(content: string): string | undefined {
  const arrowMatch = content.match(/Agenzia Prenotante[^\n]*->\s*([A-Za-zÀ-ÿ0-9 ]+)/i);
  if (arrowMatch) return arrowMatch[1].trim();
  const match = content.match(/Agenzia Prenotante[^\w]+([A-Za-zÀ-ÿ0-9 ]+)/i);
  if (match) return match[1].trim();
  return undefined;
}

function extractGuestName(content: string): string | undefined {
  const match = content.match(/(?:Nome Ospite|Ospite)[^=\n]*[:=]\s*(?:\d+\s*)?([-A-ZÀ-ÿ' ]+)/i);
  return match?.[1]?.trim();
}

function extractClientEmail(content: string): string | undefined {
  return content.match(/Email(?: Ospite)?[:=\s]+([^\s]+@[^\s]+)/i)?.[1]?.trim();
}

function extractClientPhone(content: string): string | undefined {
  return content.match(/Cellulare[:=\s]+([\d+\s]+)/i)?.[1]?.replace(/\s+/g, " ").trim();
}

function extractStay(content: string) {
  const checkInRaw = content.match(/Data di Check-in[:=\s]+([0-9/]+)/i)?.[1];
  const checkOutRaw = content.match(/Data di Check-out[:=\s]+([0-9/]+)/i)?.[1];
  if (!checkInRaw || !checkOutRaw) return undefined;
  const start = parseItalianDate(checkInRaw);
  const end = parseItalianDate(checkOutRaw);
  if (start && end) return { start, end };
  return undefined;
}

function extractServices(content: string): string[] | undefined {
  const section = extractBetweenMarkers(content, "Servizi Prenotati", "---------------------------------------------------------------");
  if (!section) return undefined;
  const services = section
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length)
    .map((line) => line.replace(/^N\.\d+\s*/i, "").trim());
  return services.length ? Array.from(new Set(services)) : undefined;
}

function extractNotes(content: string): string | undefined {
  const section = extractBetweenMarkers(content, "Note", "---------------------------------------------------------------");
  if (section) return section.replace(/\s+/g, " ").trim();
  const noteMatch = content.match(/Note[:=\s]+(.+)/i);
  return noteMatch?.[1]?.trim();
}

function detectCurrency(content: string): string | null {
  if (content.includes("€")) return "EUR";
  if (content.toLowerCase().includes("eur")) return "EUR";
  return null;
}

function cleanScidooField(value: string | undefined): string | undefined {
  if (!value) return value;
  let cleaned = value.replace(/^09/, "");
  cleaned = cleaned.replace(/^0+\s*/, "");
  return cleaned.trim();
}

registerParser({
  id: "scidoo_confirm",
  match: ({ headers }) => {
    const from = getHeader(headers, "from");
    return Boolean(from && from.toLowerCase().includes("scidoo.com"));
  },
  parse: ({ body, html, headers }: ParserInput) => {
    const content = normalizePayload(body, html);
    const extendedContent = `${content}\n${body ?? ""}`;
    const reservationId = extractReservationId(extendedContent, headers);
    const reservationStatus = extractStatus(extendedContent) ?? extractStatus(content);
    const agency = extractAgency(extendedContent);
    const guestName = extractGuestName(extendedContent);
    const clientEmail = extractClientEmail(extendedContent);
    const clientPhone = extractClientPhone(extendedContent);
    const stayPeriod = extractStay(extendedContent);

    const propertyName = cleanScidooField(extendedContent.match(/Struttura Richiesta[:=\s]+([^\n]+)/i)?.[1]);
    const roomName = cleanScidooField(extendedContent.match(/Camera\/Alloggio[:=\s]+([^\n]+)/i)?.[1]);
    const guests = cleanScidooField(extendedContent.match(/Ospiti[:=\s]+([^\n]+)/i)?.[1]);
    const ratePlan = cleanScidooField(extendedContent.match(/Tariffa[:=\s]+([^\n]+)/i)?.[1]);

    const totalAmountRaw = extendedContent.match(/Totale Prenotazione[:=\s]+([0-9.,€ ]+)/i)?.[1];
    const totalExtrasRaw = extendedContent.match(/Totale Extra[:=\s]+([0-9.,€ ]+)/i)?.[1];
    const totalBaseRaw = extendedContent.match(/Totale Retta[:=\s]+([0-9.,€ ]+)/i)?.[1];
    const commissionRaw = extendedContent.match(/Commissione[:=\s]+([0-9.,€ ]+)/i)?.[1];

    const totals = {
      amount: parseEuroNumber(totalAmountRaw),
      currency: detectCurrency(totalAmountRaw ?? extendedContent),
      extras: parseEuroNumber(totalExtrasRaw),
      baseRate: parseEuroNumber(totalBaseRaw),
      commission: parseEuroNumber(commissionRaw),
    };

    const services = extractServices(extendedContent);
    const notes = extractNotes(extendedContent);
    const paymentStatus = notes?.match(/PRE-PAID|PREPAID|PAID/i)?.[0]?.toUpperCase();

    const createdAtHeader = getHeader(headers, "date");
    const createdAt = createdAtHeader ? new Date(createdAtHeader) : undefined;

    return {
      source: "scidoo_confirm",
      reservationId,
      reservationStatus,
      guestName,
      clientEmail,
      clientPhone,
      stayPeriod,
      channel: "scidoo",
      totals,
      paymentStatus,
      services,
      notes: notes ? [notes] : undefined,
      propertyName,
      roomName,
      metadata: {
        agency,
        guests,
        ratePlan,
        propertyName,
        roomName,
        commission: totals.commission,
        notes,
        createdAt: createdAt && !Number.isNaN(createdAt.getTime()) ? createdAt.toISOString() : undefined,
      },
      raw: { body, html },
    };
  },
});
