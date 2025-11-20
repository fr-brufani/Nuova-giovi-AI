import { z } from "zod";

const EnvSchema = z.object({
  NODE_ENV: z.string().default("development"),
  PORT: z.coerce.number().optional(),
  CORS_ORIGIN: z.string().optional(),
  RATE_LIMIT_MAX: z.coerce.number().optional(),
  GOOGLE_CLOUD_PROJECT: z.string().optional(),
  FIREBASE_DATABASE_URL: z.string().optional(),
  GEMINI_API_KEY_SECRET: z.string().optional(),
  SENDGRID_API_KEY_SECRET: z.string().optional(),
  WHATSAPP_TOKEN_SECRET: z.string().optional(),
  GOOGLE_OAUTH_CLIENT_ID: z.string().optional(),
  GOOGLE_OAUTH_CLIENT_SECRET: z.string().optional(),
  GOOGLE_OAUTH_REDIRECT_URI: z.string().optional(),
  GMAIL_PUBSUB_TOPIC: z.string().optional(),
  SCIDOO_API_BASE_URL: z.string().optional(),
});

export type EnvConfig = z.infer<typeof EnvSchema>;

let cachedEnv: EnvConfig | null = null;

export function loadEnvironment(): EnvConfig {
  if (cachedEnv) return cachedEnv;
  cachedEnv = EnvSchema.parse(process.env);
  return cachedEnv;
}

