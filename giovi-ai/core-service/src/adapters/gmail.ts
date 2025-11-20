import { google } from "googleapis";
import type { GoogleAuth, OAuth2Client } from "google-auth-library";

import { loadEnvironment } from "@config/env";

export type GmailUserCredentials = {
  accessToken: string;
  refreshToken?: string;
  expiryDate?: number;
};

export interface GmailMessage {
  id: string;
  threadId: string;
  payload: {
    headers?: Array<{ name?: string; value?: string }>;
    body?: { data?: string };
    parts?: GmailMessage["payload"][];
  };
}

export class GmailAdapter {
  private gmail = google.gmail("v1");
  private readonly auth: GoogleAuth;

  constructor(auth?: GoogleAuth) {
    this.auth =
      auth ??
      new google.auth.GoogleAuth({
        scopes: ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/gmail.send"],
      });
  }

  private async getClient(credentials?: GmailUserCredentials): Promise<OAuth2Client> {
    if (credentials) {
      const env = loadEnvironment();
      if (!env.GOOGLE_OAUTH_CLIENT_ID || !env.GOOGLE_OAUTH_CLIENT_SECRET || !env.GOOGLE_OAUTH_REDIRECT_URI) {
        throw new Error("Google OAuth client configuration missing");
      }
      const oauth2 = new google.auth.OAuth2(env.GOOGLE_OAUTH_CLIENT_ID, env.GOOGLE_OAUTH_CLIENT_SECRET, env.GOOGLE_OAUTH_REDIRECT_URI);
      oauth2.setCredentials({
        access_token: credentials.accessToken,
        refresh_token: credentials.refreshToken,
        expiry_date: credentials.expiryDate,
      });
      return oauth2;
    }
    const client = await this.auth.getClient();
    return client as OAuth2Client;
  }

  async fetchMessage(email: string, messageId: string, credentials?: GmailUserCredentials): Promise<GmailMessage> {
    const authClient = await this.getClient(credentials);
    const res = await this.gmail.users.messages.get({
      auth: authClient,
      userId: email,
      id: messageId,
      format: "full",
    });
    if (!res.data) throw new Error("gmail message not found");
    return res.data as GmailMessage;
  }

  async listMessages(email: string, query: string, maxResults = 100, credentials?: GmailUserCredentials): Promise<string[]> {
    const authClient = await this.getClient(credentials);
    let pageToken: string | undefined;
    const messages: string[] = [];

    do {
      const res = await this.gmail.users.messages.list({
        auth: authClient,
        userId: email,
        q: query,
        maxResults,
        pageToken,
      });
      (res.data.messages ?? []).forEach((message) => {
        if (message.id) {
          messages.push(message.id);
        }
      });
      pageToken = res.data.nextPageToken ?? undefined;
    } while (pageToken && messages.length < maxResults);

    return messages;
  }

  static decodePart(part?: { data?: string }) {
    if (!part?.data) return "";
    const buff = Buffer.from(part.data.replace(/-/g, "+").replace(/_/g, "/"), "base64");
    return buff.toString("utf-8");
  }

  static extractHeaders(message: GmailMessage) {
    return Object.fromEntries(
      (message.payload.headers ?? [])
        .filter((header): header is { name: string; value: string } => Boolean(header.name && header.value))
        .map((header) => [header.name!.toLowerCase(), header.value!]),
    );
  }

  static extractBodies(message: GmailMessage) {
    let text = "";
    let html = "";

    const stack: GmailMessage["payload"][] = [message.payload];
    while (stack.length) {
      const part = stack.pop();
      if (!part) continue;
      if (part.parts) {
        stack.push(...part.parts);
      }
      if (part.mimeType === "text/plain" && part.body) {
        text += GmailAdapter.decodePart(part.body);
      }
      if (part.mimeType === "text/html" && part.body) {
        html += GmailAdapter.decodePart(part.body);
      }
    }

    if (!text && message.payload.body) {
      text = GmailAdapter.decodePart(message.payload.body);
    }

    return { text, html };
  }
}

let gmailAdapterInstance: GmailAdapter | null = null;

export function getGmailAdapter() {
  if (!gmailAdapterInstance) {
    gmailAdapterInstance = new GmailAdapter();
  }
  return gmailAdapterInstance;
}


