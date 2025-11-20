import dayjs from "dayjs";
import utc from "dayjs/plugin/utc.js";

import { GmailAdapter, getGmailAdapter } from "@adapters/gmail";
import { getFirestore } from "@config/firebase";
import { getIntegrationsRepository } from "@repositories/index";
import { emailIngestWorkflow } from "@workflows/emailIngest";
import { logger } from "@utils/logger";

dayjs.extend(utc);

export type GmailBackfillInput = {
  hostId: string;
  emailAddress: string;
  lookbackMonths?: number;
  maxMessages?: number;
  query?: string;
  source?: string;
};

export type GmailBackfillResult = {
  totalMessages: number;
  processed: number;
  failed: number;
  skipped: number;
};

const DEFAULT_LOOKBACK_MONTHS = 6;
const DEFAULT_MAX_MESSAGES = 500;

export async function gmailBackfillWorkflow(input: GmailBackfillInput): Promise<GmailBackfillResult> {
  const gmail = getGmailAdapter();
  const db = getFirestore();
  const integrationsRepo = getIntegrationsRepository(db);
  const integrationAccount = await integrationsRepo.getEmailAccount(input.emailAddress);
  const gmailCredentials =
    integrationAccount?.encryptedAccessToken
      ? {
          accessToken: integrationAccount.encryptedAccessToken,
          refreshToken: integrationAccount.encryptedRefreshToken ?? undefined,
          expiryDate: integrationAccount.tokenExpiry?.getTime(),
        }
      : undefined;
  const lookbackMonths = input.lookbackMonths ?? DEFAULT_LOOKBACK_MONTHS;
  const maxMessages = input.maxMessages ?? DEFAULT_MAX_MESSAGES;
  const afterTimestampSeconds = dayjs.utc().subtract(lookbackMonths, "months").unix();

  const querySegments = [`after:${afterTimestampSeconds}`];
  if (input.query?.trim()) {
    querySegments.push(input.query.trim());
  }
  const query = querySegments.join(" ");

  const messageIds = await gmail.listMessages(input.emailAddress, query, maxMessages, gmailCredentials);

  const stats: GmailBackfillResult = {
    totalMessages: messageIds.length,
    processed: 0,
    failed: 0,
    skipped: 0,
  };

  for (const messageId of messageIds) {
    try {
      const message = await gmail.fetchMessage(input.emailAddress, messageId, gmailCredentials);
      const headers = GmailAdapter.extractHeaders(message);
      const bodies = GmailAdapter.extractBodies(message);

      if (!bodies.text && !bodies.html) {
        stats.skipped += 1;
        continue;
      }

      await emailIngestWorkflow({
        provider: "gmail",
        emailAddress: input.emailAddress,
        messageId,
        headers,
        body: bodies.text ?? "",
        html: bodies.html,
        rawNotification: {
          source: input.source ?? "gmail-backfill",
          hostId: input.hostId,
          lookbackMonths,
          query,
        },
      });

      stats.processed += 1;
    } catch (error) {
      stats.failed += 1;
      logger.error({ err: error, hostId: input.hostId, messageId }, "gmail backfill ingestion failed");
    }
  }

  return stats;
}

export type ScidooBackfillInput = Omit<GmailBackfillInput, "query" | "source"> & {
  lookbackMonths?: number;
  maxMessages?: number;
};

export async function scidooBackfillWorkflow(input: ScidooBackfillInput): Promise<GmailBackfillResult> {
  return gmailBackfillWorkflow({
    ...input,
    source: "scidoo-backfill",
    query: 'from:reservation@scidoo.com subject:"Confermata - Prenotazione ID"',
  });
}

