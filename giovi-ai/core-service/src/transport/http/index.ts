import type { Express, Request, Response } from "express";
import { parse } from "csv-parse/sync";
import { z } from "zod";

import { GmailAdapter, getGmailAdapter } from "@adapters/gmail";
import { getScidooAdapter } from "@adapters/scidoo";
import { emailIngestWorkflow } from "@workflows/emailIngest";
import type { ChatRequest } from "@workflows/aiConversations";
import { handleChatRequest } from "@workflows/aiConversations";
import type { PmsReservationPayload } from "@workflows/pmsImport";
import { pmsImportWorkflow } from "@workflows/pmsImport";
import { handlePubSubMessage } from "@transport/pubsub";
import type { PubSubEnvelope } from "@transport/pubsub";
import { gmailBackfillWorkflow, resetHostData, scidooBackfillWorkflow } from "@workflows/index";
import { getClientsRepository, getIntegrationsRepository } from "@repositories/index";
import { asyncHandler } from "@utils/asyncHandler";
import { ingestCounter, metricsRegistry } from "@utils/metrics";
import { logger } from "@utils/logger";
import { createGmailOAuthClient, decodeState, encodeState, startGmailWatch } from "@utils/gmailOAuth";
import { getFirestore } from "@config/firebase";

const gmailAdapter = getGmailAdapter();
const scidooAdapter = (() => {
  try {
    return getScidooAdapter();
  } catch (error) {
    logger.warn({ err: error }, "scidoo adapter not fully configured");
    return null;
  }
})();

const chatRequestSchema = z.object({
  reservationId: z.string().min(1),
  propertyId: z.string().min(1),
  clientId: z.string().min(1),
  prompt: z.string().min(1),
  channel: z.enum(["email", "whatsapp"]),
  meta: z.record(z.unknown()).optional(),
}) satisfies z.ZodType<ChatRequest>;

const stayPeriodSchema = z.object({
  start: z.string().min(1),
  end: z.string().min(1),
});

const totalSchema = z
  .object({
    amount: z.number(),
    currency: z.string().min(1),
    extras: z.number().optional(),
  })
  .optional();

const clientSchema = z
  .object({
    fullName: z.string().optional(),
    email: z.string().email({ message: "invalid email" }).optional(),
    phone: z.string().optional(),
  })
  .optional();

const pmsReservationSchema = z.object({
  reservationId: z.string().min(1),
  hostId: z.string().min(1),
  propertyId: z.string().min(1),
  clientId: z.string().min(1),
  channel: z.string().min(1),
  status: z.string().min(1),
  stayPeriod: stayPeriodSchema,
  total: totalSchema,
  raw: z.record(z.unknown()).optional(),
  client: clientSchema,
}) satisfies z.ZodType<PmsReservationPayload>;

const pmsReservationsSchema = z.array(pmsReservationSchema).min(1);

const pubSubEnvelopeSchema: z.ZodType<PubSubEnvelope> = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("gmail.email"),
    payload: z.object({
      emailAddress: z.string().min(1),
      messageId: z.string().min(1),
    }),
  }),
  z.object({
    type: z.literal("chat.request"),
    payload: chatRequestSchema,
  }),
  z.object({
    type: z.literal("pms.import"),
    payload: pmsReservationsSchema,
  }),
  z.object({
    type: z.literal("tasks.toolCall"),
    payload: z.object({
      toolCallId: z.string().min(1),
      timestamp: z.string().min(1),
      payload: z.object({
        reservationId: z.string().min(1),
        propertyId: z.string().optional(),
        hostId: z.string().optional(),
        taskId: z.string().optional(),
        type: z.string().min(1),
        title: z.string().optional(),
        details: z.record(z.unknown()).optional(),
        status: z.string().optional(),
        priority: z.string().optional(),
        providerPhone: z.string().optional(),
        assignee: z.string().optional(),
        dueAt: z.string().optional(),
        scheduledAt: z.string().optional(),
      }),
    }),
  }),
]);

const scidooImportSchema = z.object({
  hostId: z.string().min(1),
  apiKey: z.string().optional(),
  since: z.string().optional(),
  until: z.string().optional(),
  reservations: pmsReservationsSchema.optional(),
});

const scidooBackfillSchema = z.object({
  hostId: z.string().min(1),
  emailAddress: z.string().email(),
  lookbackMonths: z.number().min(1).max(12).optional(),
  maxMessages: z.number().min(1).max(1000).optional(),
});

const gmailBackfillSchema = z.object({
  hostId: z.string().min(1),
  emailAddress: z.string().email(),
  lookbackMonths: z.number().min(1).max(12).optional(),
  maxMessages: z.number().min(1).max(1000).optional(),
  query: z.string().optional(),
});

const hostResetSchema = z.object({
  hostId: z.string().min(1),
});

const gmailAuthStartSchema = z.object({
  hostId: z.string().min(1),
  email: z.string().email(),
  redirectTo: z.string().url().optional(),
});

const clientAutoReplySchema = z.object({
  hostId: z.string().min(1),
  enabled: z.boolean(),
});

function mapCsvRowToReservation(row: Record<string, string>): PmsReservationPayload {
  const stayPeriodStart = row["stayPeriod.start"] ?? row.stayPeriodStart;
  const stayPeriodEnd = row["stayPeriod.end"] ?? row.stayPeriodEnd;

  const totalAmount = row["total.amount"] ?? row.totalAmount;
  const totalCurrency = row["total.currency"] ?? row.totalCurrency;
  const totalExtras = row["total.extras"] ?? row.totalExtras;

  const clientFullName = row["client.fullName"] ?? row.clientFullName;
  const clientEmail = row["client.email"] ?? row.clientEmail;
  const clientPhone = row["client.phone"] ?? row.clientPhone;

  const payload: PmsReservationPayload = {
    reservationId: row.reservationId,
    hostId: row.hostId,
    propertyId: row.propertyId,
    clientId: row.clientId,
    channel: row.channel,
    status: row.status,
    stayPeriod: {
      start: stayPeriodStart ?? "",
      end: stayPeriodEnd ?? "",
    },
  };

  if (totalAmount && totalCurrency) {
    payload.total = {
      amount: Number(totalAmount),
      currency: totalCurrency,
      extras: totalExtras ? Number(totalExtras) : undefined,
    };
  }

  if (clientEmail) {
    payload.client = {
      fullName: clientFullName ?? clientEmail,
      email: clientEmail,
      phone: clientPhone,
    };
  }

  return payload;
}

export function registerHttpRoutes(app: Express) {
  app.get("/_health", (_req: Request, res: Response) => {
    res.status(200).send({ ok: true });
  });

  app.get(
    "/metrics",
    asyncHandler(async (_req: Request, res: Response) => {
      res.set("Content-Type", metricsRegistry.contentType);
      res.send(await metricsRegistry.metrics());
    }),
  );

  app.post(
    "/webhooks/gmail",
    asyncHandler(async (req: Request, res: Response) => {
      const { messageId, emailAddress, headers, body, html } = req.body ?? {};

      if (!messageId || !emailAddress) {
        res.status(400).send({ error: "missing messageId or emailAddress" });
        return;
      }

      let parsedHeaders = headers as Record<string, string | undefined> | undefined;
      let textBody = body as string | undefined;
      let htmlBody = html as string | undefined;

      if (!textBody || !parsedHeaders) {
        try {
          const message = await gmailAdapter.fetchMessage(emailAddress, messageId);
          parsedHeaders = GmailAdapter.extractHeaders(message);
          const bodies = GmailAdapter.extractBodies(message);
          textBody = bodies.text;
          htmlBody = bodies.html;
        } catch (error) {
          logger.error({ err: error, emailAddress, messageId }, "unable to fetch gmail message");
          res.status(502).send({ error: "gmail_unavailable" });
          return;
        }
      }

      try {
        await emailIngestWorkflow({
          provider: "gmail",
          messageId,
          emailAddress,
          headers: parsedHeaders ?? {},
          body: textBody ?? "",
          html: htmlBody,
          rawNotification: req.body,
        });
      } catch (error) {
        logger.error({ err: error, emailAddress, messageId }, "gmail webhook ingest failed");
        res.status(500).send({ error: "ingest_failed" });
        return;
      }

      res.status(204).send();
    }),
  );

  app.post(
    "/chat/respond",
    asyncHandler(async (req: Request, res: Response) => {
      const parseResult = chatRequestSchema.safeParse(req.body);

      if (!parseResult.success) {
        res.status(400).send({ error: "invalid_request", details: parseResult.error.flatten() });
        return;
      }

      try {
        await handleChatRequest(parseResult.data);
        ingestCounter.inc({ type: "chat" });
        res.status(202).send({ accepted: true });
      } catch (error) {
        logger.error({ err: error, reservationId: parseResult.data.reservationId }, "chat respond failed");
        res.status(502).send({ error: "upstream_failure" });
      }
    }),
  );

  app.post(
    "/pms/import",
    asyncHandler(async (req: Request, res: Response) => {
      const contentType = req.headers["content-type"] ?? "";
      let reservationsPayload: unknown;

      if (typeof req.body === "string") {
        const records = parse(req.body, {
          columns: true,
          skip_empty_lines: true,
          trim: true,
        }) as Record<string, string>[];
        reservationsPayload = records.map(mapCsvRowToReservation);
      } else if (contentType.includes("application/json") || Array.isArray(req.body) || typeof req.body === "object") {
        const body = req.body;
        reservationsPayload = Array.isArray(body) ? body : [body];
      } else {
        res.status(415).send({ error: "unsupported_media_type" });
        return;
      }

      const parsed = pmsReservationsSchema.safeParse(reservationsPayload);

      if (!parsed.success) {
        res.status(400).send({ error: "invalid_request", details: parsed.error.flatten() });
        return;
      }

      try {
        await pmsImportWorkflow(parsed.data);
        ingestCounter.inc({ type: "pms" }, parsed.data.length);
        res.status(202).send({ imported: parsed.data.length });
      } catch (error) {
        logger.error({ err: error, count: parsed.data.length }, "pms import failed");
        res.status(500).send({ error: "ingest_failed" });
      }
    }),
  );

  app.post(
    "/toolcall/pubsub",
    asyncHandler(async (req: Request, res: Response) => {
      const message = req.body?.message;

      if (!message?.data) {
        res.status(400).send({ error: "missing_message_data" });
        return;
      }

      const decoded = Buffer.from(String(message.data), "base64").toString("utf8");

      let envelopeJson: unknown;
      try {
        envelopeJson = JSON.parse(decoded);
      } catch (error) {
        logger.warn({ error, decoded }, "invalid pubsub payload");
        res.status(400).send({ error: "invalid_json" });
        return;
      }

      const envelopeResult = pubSubEnvelopeSchema.safeParse(envelopeJson);

      if (!envelopeResult.success) {
        res.status(400).send({ error: "invalid_envelope", details: envelopeResult.error.flatten() });
        return;
      }

      try {
        await handlePubSubMessage(envelopeResult.data);
        ingestCounter.inc({ type: "pubsub" });
        res.status(204).send();
      } catch (error) {
        logger.error({ err: error, envelopeType: envelopeResult.data.type }, "pubsub handling failed");
        res.status(500).send({ error: "handler_failed" });
      }
    }),
  );

  app.post(
    "/webhooks/sendgrid",
    asyncHandler(async (req: Request, res: Response) => {
      const events = Array.isArray(req.body) ? req.body : [req.body];

      const results = await Promise.allSettled(
        events.map(async (event) => {
          if (!event?.sg_event_id) return;
          const headers = (event.headers ?? {}) as Record<string, string | undefined>;
          await emailIngestWorkflow({
            provider: "sendgrid",
            messageId: String(event.sg_event_id),
            emailAddress: String(event.email ?? ""),
            headers,
            body: String(event.text ?? ""),
            html: event.html,
            rawNotification: event,
          });
        }),
      );

      const failures = results.filter((result): result is PromiseRejectedResult => result.status === "rejected");
      if (failures.length) {
        logger.error({ failures: failures.map((f) => f.reason?.message ?? f.reason), count: failures.length }, "sendgrid ingest partial failure");
      }

      res.status(failures.length ? 207 : 202).send({ accepted: events.length - failures.length, failed: failures.length });
    }),
  );

  app.post(
    "/integrations/scidoo/import",
    asyncHandler(async (req: Request, res: Response) => {
      const parseResult = scidooImportSchema.safeParse(req.body);
      if (!parseResult.success) {
        res.status(400).send({ error: "invalid_request", details: parseResult.error.flatten() });
        return;
      }

      const { hostId, reservations, apiKey, since, until } = parseResult.data;
      let payload: PmsReservationPayload[] = reservations ?? [];

      if (!payload.length) {
        if (!apiKey) {
          res.status(400).send({ error: "missing_api_key" });
          return;
        }

        if (!scidooAdapter) {
          res.status(500).send({ error: "scidoo_adapter_not_configured" });
          return;
        }

        try {
          payload = await scidooAdapter.fetchReservations({
            hostId,
            apiKey,
            since,
            until,
          });
        } catch (error) {
          logger.error({ err: error, hostId }, "scidoo api import failed");
          res.status(502).send({ error: "scidoo_api_failure" });
          return;
        }
      }

      if (!payload.length) {
        res.status(204).send();
        return;
      }

      await pmsImportWorkflow(
        payload.map((reservation) => ({
          ...reservation,
          hostId,
        })),
      );

      logger.info({ hostId, imported: payload.length }, "scidoo import completed");
      res.status(202).send({ imported: payload.length });
    }),
  );

  app.post(
    "/integrations/scidoo/backfill",
    asyncHandler(async (req: Request, res: Response) => {
      const parseResult = scidooBackfillSchema.safeParse(req.body);
      if (!parseResult.success) {
        res.status(400).send({ error: "invalid_request", details: parseResult.error.flatten() });
        return;
      }

      const result = await scidooBackfillWorkflow(parseResult.data);
      res.status(202).send(result);
    }),
  );

  app.post(
    "/integrations/gmail/backfill",
    asyncHandler(async (req: Request, res: Response) => {
      const parseResult = gmailBackfillSchema.safeParse(req.body);
      if (!parseResult.success) {
        res.status(400).send({ error: "invalid_request", details: parseResult.error.flatten() });
        return;
      }

      const payload = parseResult.data;
      const db = getFirestore();
      const integrationsRepo = getIntegrationsRepository(db);
      const account = await integrationsRepo.getEmailAccount(payload.emailAddress);
      if (!account) {
        res.status(400).send({ error: "gmail_account_not_connected" });
        return;
      }
      if (account.hostId && account.hostId !== payload.hostId) {
        res.status(403).send({ error: "forbidden" });
        return;
      }

      const result = await gmailBackfillWorkflow(payload);
      res.status(202).send(result);
    }),
  );

  app.post(
    "/hosts/reset",
    asyncHandler(async (req: Request, res: Response) => {
      const schemaResult = hostResetSchema.safeParse(req.body);
      if (!schemaResult.success) {
        res.status(400).send({ error: "invalid_request", details: schemaResult.error.flatten() });
        return;
      }

      const summary = await resetHostData(schemaResult.data.hostId);
      res.status(202).send(summary);
    }),
  );

  app.patch(
    "/clients/:clientId/auto-reply",
    asyncHandler(async (req: Request, res: Response) => {
      const paramSchema = z.object({ clientId: z.string().min(1) });
      const { clientId } = paramSchema.parse(req.params);

      const parseResult = clientAutoReplySchema.safeParse(req.body);
      if (!parseResult.success) {
        res.status(400).send({ error: "invalid_request", details: parseResult.error.flatten() });
        return;
      }

      const payload = parseResult.data;
      const db = getFirestore();
      const clientsRepo = getClientsRepository(db);
      const client = await clientsRepo.get(clientId);
      if (!client) {
        res.status(404).send({ error: "client_not_found" });
        return;
      }

      if (client.primaryHostId && client.primaryHostId !== payload.hostId) {
        res.status(403).send({ error: "forbidden" });
        return;
      }

      await clientsRepo.updateAutoReply(clientId, payload.enabled);
      res.status(204).send();
    }),
  );

  app.get(
    "/integrations/gmail/auth-url",
    asyncHandler(async (req: Request, res: Response) => {
      const parseResult = gmailAuthStartSchema.safeParse(req.query);
      if (!parseResult.success) {
        res.status(400).send({ error: "invalid_request", details: parseResult.error.flatten() });
        return;
      }

      const oauthClient = createGmailOAuthClient();
      const state = encodeState(parseResult.data);
      const authUrl = oauthClient.generateAuthUrl({
        access_type: "offline",
        scope: [
          "https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.modify",
          "https://www.googleapis.com/auth/gmail.send",
        ],
        prompt: "consent",
        state,
      });

      res.send({ url: authUrl });
    }),
  );

  app.get(
    "/integrations/gmail/oauth/callback",
    asyncHandler(async (req: Request, res: Response) => {
      const { code, state } = req.query ?? {};
      if (!code || !state || typeof code !== "string" || typeof state !== "string") {
        res.status(400).send("Missing code or state");
        return;
      }

      let payload: ReturnType<typeof decodeState>;
      try {
        payload = decodeState(state);
      } catch (error) {
        logger.error({ err: error }, "invalid gmail oauth state");
        res.status(400).send("Invalid state");
        return;
      }

      const oauthClient = createGmailOAuthClient();
      const tokenResponse = await oauthClient.getToken(code);
      oauthClient.setCredentials(tokenResponse.tokens);

      const accessToken = tokenResponse.tokens.access_token;
      if (!accessToken) {
        res.status(500).send("Missing access token");
        return;
      }

      const refreshToken = tokenResponse.tokens.refresh_token;
      const expiryDate = tokenResponse.tokens.expiry_date ? new Date(tokenResponse.tokens.expiry_date) : undefined;

      const db = getFirestore();
      const integrationsRepo = getIntegrationsRepository(db);

      await integrationsRepo.saveGmailOAuthTokens({
        hostId: payload.hostId,
        emailId: payload.email,
        accessToken,
        refreshToken,
        expiryDate,
      });

      try {
        const watchResponse = await startGmailWatch(payload.email, accessToken, refreshToken, tokenResponse.tokens.expiry_date);
        if (watchResponse.historyId) {
          await integrationsRepo.updateEmailHistoryCursor(payload.email, String(watchResponse.historyId));
        }
      } catch (error) {
        logger.error({ err: error, email: payload.email }, "gmail watch subscription failed");
      }

      if (payload.redirectTo) {
        res.redirect(payload.redirectTo);
      } else {
        res.send("Gmail integration completed. You can close this window.");
      }
    }),
  );
}

