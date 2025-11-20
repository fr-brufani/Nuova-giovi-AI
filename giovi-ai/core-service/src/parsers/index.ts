import { parsedEmailPayloadSchema, type ParsedEmailPayload } from "@types/domain";

export type ParserInput = {
  headers: Record<string, string | undefined>;
  body: string;
  html?: string;
};

export type EmailParser = (input: ParserInput) => ParsedEmailPayload | null;

export type ParserRegistry = {
  id: string;
  match: (input: ParserInput) => boolean;
  parse: EmailParser;
};

const registry: ParserRegistry[] = [];

export function registerParser(parser: ParserRegistry) {
  registry.push(parser);
}

export function parseEmail(input: ParserInput): ParsedEmailPayload | null {
  const matched = registry.find((parser) => parser.match(input));
  if (!matched) return null;
  const parsed = matched.parse(input);
  return parsedEmailPayloadSchema.parse(parsed);
}

// TODO: import registerParser in specific parser modules (es. ./airbnbConfirm) to populate registry.

