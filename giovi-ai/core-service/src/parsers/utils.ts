const IT_MONTHS: Record<string, number> = {
  gennaio: 1,
  gen: 1,
  febbraio: 2,
  feb: 2,
  marzo: 3,
  mar: 3,
  aprile: 4,
  apr: 4,
  maggio: 5,
  mag: 5,
  giugno: 6,
  giu: 6,
  luglio: 7,
  lug: 7,
  agosto: 8,
  ago: 8,
  settembre: 9,
  set: 9,
  sett: 9,
  ottobre: 10,
  ott: 10,
  novembre: 11,
  nov: 11,
  dicembre: 12,
  dic: 12,
};

const whitespaceRegex = /\s+/g;

export function normalizeSpaces(value: string): string {
  return value.replace(whitespaceRegex, " ").trim();
}

export function decodeQuotedPrintable(input: string): string {
  return input
    .replace(/=\r?\n/g, "")
    .replace(/=([A-Fa-f0-9]{2})/g, (_, hex: string) => {
      try {
        return String.fromCharCode(Number.parseInt(hex, 16));
      } catch {
        return _;
      }
    });
}

export function maybeDecodeBase64(input: string): string {
  const trimmed = input.trim();
  const normalized = trimmed.replace(/\s+/g, "");
  if (!normalized || normalized.length % 4 !== 0) return input;
  if (!/^[A-Za-z0-9+/=]+$/.test(normalized)) return input;
  try {
    const decoded = Buffer.from(normalized, "base64").toString("utf8");
    return decoded.length ? decoded : input;
  } catch {
    return input;
  }
}

export function stripHtml(html: string): string {
  return html
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/p>/gi, "\n")
    .replace(/<\/div>/gi, "\n")
    .replace(/<\/li>/gi, "\n")
    .replace(/<li>/gi, "- ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\r/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function normalizePayload(body?: string, html?: string): string {
  if (html) {
    return decodeQuotedPrintable(stripHtml(html)).trim();
  }
  if (!body) return "";
  const decoded = decodeQuotedPrintable(body);
  return decoded.replace(/\r/g, "").trim();
}

export function parseEuroNumber(raw: string | undefined | null): number | null {
  if (!raw) return null;
  let sanitized = raw.replace(/\s+/g, "");
  if (sanitized.startsWith("0") && sanitized.length > 2 && sanitized[1] === "9" && /\d/.test(sanitized[2] ?? "")) {
    sanitized = sanitized.slice(2);
  }
  const hasComma = sanitized.includes(",");
  const hasDot = sanitized.includes(".");
  let normalized = sanitized.replace(/[^\d,.,-]/g, "");

  if (hasComma && hasDot) {
    normalized = normalized.replace(/\./g, "").replace(",", ".");
  } else if (hasComma) {
    normalized = normalized.replace(/\./g, "").replace(",", ".");
  } else {
    normalized = normalized.replace(/,/g, "");
    if (hasDot) {
      const [integerPart, fractionalPart] = normalized.split(".");
      if (integerPart.length > 3 && integerPart.startsWith("0")) {
        const trimmedInt = integerPart.slice(- (integerPart.length - 2));
        normalized = `${trimmedInt}.${fractionalPart ?? ""}`;
      }
    }
  }

  if (!normalized) return null;
  const value = Number.parseFloat(normalized);
  return Number.isFinite(value) ? value : null;
}

export function parseItalianDate(input: string): Date | undefined {
  const trimmed = input.trim().toLowerCase();
  const numericMatch = trimmed.match(/(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})/);
  if (numericMatch) {
    const [, day, month, year] = numericMatch;
    const iso = `${year.length === 2 ? `20${year}` : year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
    const date = new Date(iso);
    if (!Number.isNaN(date.getTime())) return date;
  }

  const textMatch = trimmed.match(/(\d{1,2})\s+([a-zàéìòù]{3,})\s+(\d{4})/i);
  if (textMatch) {
    const [, dayRaw, monthRaw, yearRaw] = textMatch;
    const month = IT_MONTHS[monthRaw.normalize("NFD").replace(/[\u0300-\u036f]/g, "")] ?? IT_MONTHS[monthRaw];
    if (month) {
      const iso = `${yearRaw}-${String(month).padStart(2, "0")}-${dayRaw.padStart(2, "0")}`;
      const date = new Date(iso);
      if (!Number.isNaN(date.getTime())) return date;
    }
  }
  return undefined;
}

export function parseItalianRange(input: string): { start: Date; end: Date } | undefined {
  const cleaned = input.replace(/[–—]/g, "-");
  const rangeMatch = cleaned.match(
    /(\d{1,2}[^\d]{0,3}[a-zàéìòù]{3,}\s+\d{4})\s*-\s*(\d{1,2}[^\d]{0,3}[a-zàéìòù]{3,}\s+\d{4})/i,
  );
  if (rangeMatch) {
    const start = parseItalianDate(rangeMatch[1]);
    const end = parseItalianDate(rangeMatch[2]);
    if (start && end) return { start, end };
  }

  const shortRange = cleaned.match(/(\d{1,2})\s+([a-zàéìòù]{3,})\s*[^\d]+(\d{1,2})\s+([a-zàéìòù]{3,})/i);
  if (shortRange) {
    const [, startDay, startMonth, endDay, endMonth] = shortRange;
    const yearMatch = cleaned.match(/(\d{4})/g);
    const years = yearMatch ? yearMatch.map((y) => Number.parseInt(y, 10)) : [];
    const startYear = years[0] ?? new Date().getFullYear();
    const endYear = years[1] ?? startYear;
    const start = parseItalianDate(`${startDay} ${startMonth} ${startYear}`);
    const end = parseItalianDate(`${endDay} ${endMonth} ${endYear}`);
    if (start && end) return { start, end };
  }
  return undefined;
}

export function extractBetweenMarkers(source: string, start: string, end: string): string | undefined {
  const startIndex = source.indexOf(start);
  if (startIndex === -1) return undefined;
  const sliced = source.slice(startIndex + start.length);
  if (!end) return sliced.trim();
  const endIndex = sliced.indexOf(end);
  return (endIndex === -1 ? sliced : sliced.slice(0, endIndex)).trim();
}

export function collectMatches(regex: RegExp, text: string): string[] {
  const matches: string[] = [];
  let match: RegExpExecArray | null;
  const globalRegex = new RegExp(regex.source, regex.flags.includes("g") ? regex.flags : `${regex.flags}g`);

  while ((match = globalRegex.exec(text)) !== null) {
    if (match[1]) {
      matches.push(normalizeSpaces(match[1]));
    }
  }

  return matches;
}

export function matchFirst(regexes: RegExp[], text: string): string | undefined {
  for (const regex of regexes) {
    const match = regex.exec(text);
    if (match && match[1]) {
      return normalizeSpaces(match[1]);
    }
  }
  return undefined;
}

export function getHeader(headers: Record<string, string | undefined>, key: string): string | undefined {
  const lowerKey = key.toLowerCase();
  const direct = headers[key] ?? headers[key.toLowerCase()];
  if (direct) return direct;
  return Object.entries(headers).find(([k]) => k.toLowerCase() === lowerKey)?.[1];
}
