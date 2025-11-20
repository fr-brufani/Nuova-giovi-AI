import { google } from "googleapis";

import { loadEnvironment } from "@config/env";

type OAuthStatePayload = {
  hostId: string;
  email: string;
  redirectTo?: string;
};

export function createGmailOAuthClient() {
  const env = loadEnvironment();
  const { GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REDIRECT_URI } = env;
  if (!GOOGLE_OAUTH_CLIENT_ID || !GOOGLE_OAUTH_CLIENT_SECRET || !GOOGLE_OAUTH_REDIRECT_URI) {
    throw new Error("Google OAuth configuration missing");
  }
  return new google.auth.OAuth2(GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REDIRECT_URI);
}

export function encodeState(payload: OAuthStatePayload) {
  return Buffer.from(JSON.stringify(payload)).toString("base64url");
}

export function decodeState(state: string): OAuthStatePayload {
  const buffer = Buffer.from(state, "base64url");
  return JSON.parse(buffer.toString());
}

export async function startGmailWatch(email: string, accessToken: string, refreshToken?: string, expiry?: number) {
  const env = loadEnvironment();
  if (!env.GMAIL_PUBSUB_TOPIC) {
    throw new Error("GMAIL_PUBSUB_TOPIC missing");
  }

  const oauth2Client = createGmailOAuthClient();
  oauth2Client.setCredentials({
    access_token: accessToken,
    refresh_token: refreshToken,
    expiry_date: expiry,
  });

  const gmail = google.gmail({ version: "v1", auth: oauth2Client });
  const response = await gmail.users.watch({
    userId: email,
    requestBody: {
      topicName: env.GMAIL_PUBSUB_TOPIC,
      labelIds: ["INBOX"],
    },
  });

  return response.data;
}


