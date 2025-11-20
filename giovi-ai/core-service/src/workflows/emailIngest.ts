import { FieldValue } from "firebase-admin/firestore";

import { GmailAdapter, getGmailAdapter } from "@adapters/gmail";
import { getFirestore } from "@config/firebase";
import { parseEmail } from "@parsers/index";
import {
  getReservationsRepository,
  getClientsRepository,
  getPropertiesRepository,
  getIntegrationsRepository,
  getHostsRepository,
} from "@repositories/index";
import {
  clientSchema,
  parsedEmailPayloadSchema,
  reservationSchema,
  type ConversationMessage,
  type EmailIntegrationAccount,
  type ParsedEmailPayload,
  type Reservation,
} from "@types/domain";
import { logger } from "@utils/logger";

export type EmailIngestInput = {
  provider: "gmail" | "sendgrid";
  emailAddress: string;
  messageId: string;
  headers: Record<string, string | undefined>;
  body: string;
  html?: string;
  rawNotification?: Record<string, unknown>;
};

type ReservationContext = Pick<
  Reservation,
  "reservationId" | "propertyId" | "clientId" | "hostId" | "conversationId" | "status"
>;

const gmailAdapter = getGmailAdapter();

function slugify(value: string | undefined, fallback: string): string {
  if (!value) return fallback;
  const normalized = value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return normalized.length ? normalized : fallback;
}

function getMetadataValue<T>(metadata: Record<string, unknown> | undefined, key: string): T | undefined {
  if (!metadata) return undefined;
  const value = metadata[key];
  return (value as T) ?? undefined;
}

function deriveIdentifiers(
  parsed: ParsedEmailPayload,
  input: EmailIngestInput,
  existingReservation: Reservation | null,
  integrationAccount: EmailIntegrationAccount | null,
) {
  const fallbackKey = slugify(parsed.reservationId ?? parsed.conversationId ?? input.messageId, `msg-${Date.now()}`);

  const reservationId = existingReservation?.reservationId ?? parsed.reservationId ?? `email-${fallbackKey}`;
  const conversationId =
    existingReservation?.conversationId ?? parsed.conversationId ?? parsed.reservationId ?? `conv-${fallbackKey}`;

  const hostEmail = parsed.hostEmail ?? integrationAccount?.emailId ?? input.emailAddress;
  const hostId =
    existingReservation?.hostId ??
    integrationAccount?.hostId ??
    `host-${slugify(hostEmail, fallbackKey).replace(/^host-/, "")}`;

  const propertyName =
    (parsed.metadata?.propertyName as string | undefined) ??
    parsed.propertyName ??
    `Property ${conversationId.slice(0, 6)}`;
  const propertyId =
    existingReservation?.propertyId ??
    getMetadataValue<string>(integrationAccount?.metadata, "propertyId") ??
    `${hostId}-${slugify(propertyName, fallbackKey)}`;

  const clientEmail = parsed.clientEmail;
  const clientName =
    parsed.guestName ??
    (parsed.metadata?.guestName as string | undefined) ??
    getMetadataValue<string>(existingReservation?.metadata, "guestName") ??
    clientEmail ??
    `Guest ${conversationId.slice(0, 6)}`;
  const clientId =
    existingReservation?.clientId ??
    (parsed.metadata?.clientId as string | undefined) ??
    getMetadataValue<string>(existingReservation?.metadata, "clientId") ??
    (clientEmail ? `client-${slugify(clientEmail, fallbackKey)}` : `guest-${slugify(clientName, fallbackKey)}`);

  return {
    reservationId,
    conversationId,
    hostId,
    hostEmail,
    propertyId,
    propertyName,
    clientId,
    clientDisplayName: clientName,
    clientEmail,
  };
}

export async function emailIngestWorkflow(input: EmailIngestInput) {
  const db = getFirestore();
  const integrationsRepo = getIntegrationsRepository(db);
  const clientsRepo = getClientsRepository(db);
  const propertiesRepo = getPropertiesRepository(db);
  const reservationsRepo = getReservationsRepository(db);
  const hostsRepo = getHostsRepository(db);

  const integrationAccount = await integrationsRepo.getEmailAccount(input.emailAddress);
  const gmailCredentials =
    input.provider === "gmail" && integrationAccount?.encryptedAccessToken
      ? {
          accessToken: integrationAccount.encryptedAccessToken,
          refreshToken: integrationAccount.encryptedRefreshToken ?? undefined,
          expiryDate: integrationAccount.tokenExpiry?.getTime(),
        }
      : undefined;

  let headers = input.headers;
  let body = input.body;
  let html = input.html;

  if (input.provider === "gmail" && (!body || !body.trim() || !headers || Object.keys(headers).length === 0)) {
    try {
      const message = await gmailAdapter.fetchMessage(input.emailAddress, input.messageId, gmailCredentials);
      headers = GmailAdapter.extractHeaders(message);
      const bodies = GmailAdapter.extractBodies(message);
      body = bodies.text;
      html = bodies.html;
    } catch (error) {
      logger.error({ error, messageId: input.messageId }, "failed to fetch gmail message content");
    }
  }

  const parsed = parseEmail({
    headers,
    body,
    html,
  });

  if (!parsed) {
    logger.warn({ messageId: input.messageId }, "no parser matched inbound email");
    return;
  }

  const parsedPayload = parsedEmailPayloadSchema.parse(parsed);

  await integrationsRepo.recordInboundEmail(input.emailAddress, input.messageId, {
    provider: input.provider,
    emailAddress: input.emailAddress,
    parsedSource: parsedPayload.source ?? "unknown",
    receivedAt: new Date(),
    headers,
    reservationId: parsedPayload.reservationId,
    conversationId: parsedPayload.conversationId,
  });

  await integrationsRepo.storeRawEmailPayload(input.emailAddress, input.messageId, {
    headers,
    body,
    html,
    rawNotification: input.rawNotification,
  });

  let existingReservation: Reservation | null = null;
  if (parsedPayload.reservationId) {
    existingReservation = await reservationsRepo.get(parsedPayload.reservationId);
  }

  if (!existingReservation && parsedPayload.conversationId) {
    existingReservation = await reservationsRepo.findByConversation(parsedPayload.conversationId);
  }

  const identifiers = deriveIdentifiers(parsedPayload, input, existingReservation, integrationAccount);

  const reservationCtx: ReservationContext = {
    reservationId: identifiers.reservationId,
    propertyId: identifiers.propertyId,
    clientId: identifiers.clientId,
    hostId: identifiers.hostId,
    conversationId: identifiers.conversationId,
    status: parsedPayload.reservationStatus ?? existingReservation?.status ?? "pending",
  };

  await hostsRepo.upsert({
    hostId: identifiers.hostId,
    displayName:
      getMetadataValue<string>(integrationAccount?.metadata, "hostDisplayName") ??
      identifiers.hostEmail ??
      identifiers.hostId,
    email: identifiers.hostEmail,
    status: integrationAccount?.status ?? "active",
    schemaVersion: 2,
  });

  await propertiesRepo.upsert({
    propertyId: identifiers.propertyId,
    hostId: identifiers.hostId,
    name: identifiers.propertyName,
    timezone:
      (parsedPayload.metadata?.timezone as string | undefined) ??
      getMetadataValue<string>(integrationAccount?.metadata, "timezone"),
    schemaVersion: 2,
  });

  const reservationUpdate: Reservation = reservationSchema.parse({
    reservationId: reservationCtx.reservationId,
    hostId: reservationCtx.hostId,
    propertyId: reservationCtx.propertyId,
    clientId: reservationCtx.clientId,
    conversationId: reservationCtx.conversationId,
    channel: parsedPayload.channel ?? existingReservation?.channel ?? "email",
    status: parsedPayload.reservationStatus ?? existingReservation?.status ?? "pending",
    stayPeriod:
      parsedPayload.stayPeriod ??
      existingReservation?.stayPeriod ?? {
        start: new Date(),
        end: new Date(),
      },
    source: {
      provider: parsedPayload.source ?? existingReservation?.source.provider ?? "email",
      externalId:
        parsedPayload.reservationId ??
        parsedPayload.conversationId ??
        existingReservation?.source.externalId ??
        input.messageId,
      rawMessageId: input.messageId,
    },
    totals: parsedPayload.totals ?? existingReservation?.totals,
    metadata: {
      ...(existingReservation?.metadata ?? {}),
      ...(parsedPayload.metadata ?? {}),
      guestName: identifiers.clientDisplayName,
      propertyName: identifiers.propertyName,
      clientEmail:
        parsedPayload.clientEmail ?? getMetadataValue<string>(existingReservation?.metadata, "clientEmail"),
      lastEmailMessageAt: new Date().toISOString(),
    },
    schemaVersion: 2,
  });

  await reservationsRepo.upsert(reservationUpdate);

  const clientDoc = clientSchema.parse({
    clientId: reservationCtx.clientId,
    displayName: identifiers.clientDisplayName,
    fullName: parsedPayload.guestName ?? identifiers.clientDisplayName,
    primaryEmail: parsedPayload.clientEmail ?? undefined,
    primaryPhone: parsedPayload.clientPhone ?? undefined,
    whatsappPhone: parsedPayload.clientPhone ?? undefined,
    channelEmails: parsedPayload.clientEmail
      ? {
          ...getMetadataValue<Record<string, string>>(existingReservation?.metadata, "channelEmails"),
          [parsedPayload.channel ?? "email"]: parsedPayload.clientEmail,
        }
      : getMetadataValue<Record<string, string>>(existingReservation?.metadata, "channelEmails"),
    primaryHostId: reservationCtx.hostId,
    primaryPropertyId: reservationCtx.propertyId,
    activeReservationId: reservationCtx.reservationId,
    schemaVersion: 2,
  });

  await clientsRepo.upsert(clientDoc);

  const messageBody =
    parsedPayload.messageText ??
    (typeof parsedPayload.messageHtml === "string" ? parsedPayload.messageHtml : undefined) ??
    body?.slice(0, 2000) ??
    "";

  const message: ConversationMessage = {
    messageId: input.messageId,
    reservationId: reservationCtx.reservationId,
    propertyId: reservationCtx.propertyId,
    clientId: reservationCtx.clientId,
    channel: parsedPayload.channel ?? "email",
    direction: "inbound",
    sentAt: new Date(),
    body: messageBody || undefined,
    rawHeaders: headers,
    provider: input.provider,
    metadata: parsedPayload.metadata,
    schemaVersion: 2,
  };

  await propertiesRepo.touchConversation(reservationCtx.propertyId, reservationCtx.conversationId, {
    reservationId: reservationCtx.reservationId,
    clientId: reservationCtx.clientId,
    channel: parsedPayload.channel ?? "email",
    hostId: reservationCtx.hostId,
    schemaVersion: 2,
    updatedAt: FieldValue.serverTimestamp(),
    lastMessagePreview: message.body?.slice(0, 200),
    lastMessageAt: FieldValue.serverTimestamp(),
    lastDirection: message.direction,
    lastProvider: input.provider,
  });

  await propertiesRepo.appendMessage(reservationCtx.propertyId, reservationCtx.conversationId, message.messageId, message);

  logger.info({ messageId: input.messageId, reservationId: reservationCtx.reservationId }, "email ingest completed");
}


