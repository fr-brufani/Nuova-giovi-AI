import { z } from "zod";

export const stayPeriodSchema = z.object({
  start: z.coerce.date(),
  end: z.coerce.date(),
});

export type StayPeriod = z.infer<typeof stayPeriodSchema>;

const reservationTotalsSchema = z.object({
  amount: z.number().nullable().optional(),
  currency: z.string().nullable().optional(),
  extras: z.number().nullable().optional(),
  baseRate: z.number().nullable().optional(),
  commission: z.number().nullable().optional(),
});

export const reservationSchema = z.object({
  reservationId: z.string(),
  channel: z.string(),
  hostId: z.string(),
  propertyId: z.string(),
  clientId: z.string(),
  status: z.string(),
  stayPeriod: stayPeriodSchema,
  conversationId: z.string().optional(),
  source: z.object({
    provider: z.string(),
    externalId: z.string().optional(),
    rawMessageId: z.string().optional(),
  }),
  totals: reservationTotalsSchema.optional(),
  metadata: z.record(z.unknown()).optional(),
  schemaVersion: z.number().default(2),
  createdAt: z.coerce.date().optional(),
  updatedAt: z.coerce.date().optional(),
});

export type Reservation = z.infer<typeof reservationSchema>;

export const clientSchema = z.object({
  clientId: z.string(),
  displayName: z.string().optional(),
  fullName: z.string().optional(),
  primaryEmail: z.string().email().optional(),
  whatsappPhone: z.string().optional(),
  primaryPhone: z.string().optional(),
  primaryHostId: z.string().optional(),
  primaryPropertyId: z.string().optional(),
  activeReservationId: z.string().optional(),
  channelEmails: z.record(z.string()).optional(),
  autoReplyEnabled: z.boolean().optional().default(true),
  schemaVersion: z.number().default(2),
  createdAt: z.coerce.date().optional(),
  updatedAt: z.coerce.date().optional(),
  metadata: z.record(z.unknown()).optional(),
});

export type Client = z.infer<typeof clientSchema>;

export const conversationMessageSchema = z.object({
  messageId: z.string(),
  reservationId: z.string(),
  propertyId: z.string(),
  clientId: z.string(),
  channel: z.string(),
  direction: z.enum(["inbound", "outbound", "system"]),
  sentAt: z.coerce.date(),
  body: z.string().optional(),
  attachments: z
    .array(
      z.object({
        url: z.string(),
        type: z.string(),
        name: z.string().optional(),
      }),
    )
    .optional(),
  rawHeaders: z.record(z.unknown()).optional(),
  provider: z.string().optional(),
  schemaVersion: z.number().default(2),
  createdAt: z.coerce.date().optional(),
  updatedAt: z.coerce.date().optional(),
  metadata: z.record(z.unknown()).optional(),
});

export type ConversationMessage = z.infer<typeof conversationMessageSchema>;

export const parsedEmailPayloadSchema = z.object({
  source: z.string(),
  reservationId: z.string().optional(),
  conversationId: z.string().optional(),
  hostEmail: z.string().email().optional(),
  clientEmail: z.string().email().optional(),
  clientPhone: z.string().optional(),
  guestName: z.string().optional(),
  stayPeriod: stayPeriodSchema.optional(),
  messageText: z.string().optional(),
  messageHtml: z.string().optional(),
  channel: z.string().optional(),
  reservationStatus: z.string().optional(),
  paymentStatus: z.string().optional(),
  propertyName: z.string().optional(),
  roomName: z.string().optional(),
  totals: reservationTotalsSchema.optional(),
  services: z.array(z.string()).optional(),
  notes: z.array(z.string()).optional(),
  raw: z.unknown(),
  metadata: z.record(z.unknown()).optional(),
});

export type ParsedEmailPayload = z.infer<typeof parsedEmailPayloadSchema>;

export const hostSchema = z.object({
  hostId: z.string(),
  displayName: z.string(),
  email: z.string().email(),
  status: z.string(),
  schemaVersion: z.number().default(2),
  createdAt: z.coerce.date().optional(),
  updatedAt: z.coerce.date().optional(),
});

export type Host = z.infer<typeof hostSchema>;

export const propertySchema = z.object({
  propertyId: z.string(),
  hostId: z.string(),
  name: z.string(),
  address: z
    .object({
      line1: z.string().optional(),
      line2: z.string().optional(),
      city: z.string().optional(),
      country: z.string().optional(),
      postalCode: z.string().optional(),
    })
    .optional(),
  contacts: z
    .array(
      z.object({
        type: z.string(),
        value: z.string(),
      }),
    )
    .optional(),
  timezone: z.string().optional(),
  metadata: z.record(z.unknown()).optional(),
  schemaVersion: z.number().default(2),
  createdAt: z.coerce.date().optional(),
  updatedAt: z.coerce.date().optional(),
});

export type Property = z.infer<typeof propertySchema>;

export const taskTimestampsSchema = z.object({
  createdAt: z.coerce.date(),
  updatedAt: z.coerce.date(),
  dueAt: z.coerce.date().optional(),
  scheduledAt: z.coerce.date().optional(),
  completedAt: z.coerce.date().optional(),
  cancelledAt: z.coerce.date().optional(),
});

export type TaskTimestamps = z.infer<typeof taskTimestampsSchema>;

export const propertyTaskSchema = z.object({
  taskId: z.string(),
  propertyId: z.string(),
  hostId: z.string(),
  reservationId: z.string().optional(),
  title: z.string().optional(),
  status: z.string(),
  type: z.string(),
  priority: z.string().optional(),
  details: z.record(z.unknown()).optional(),
  providerPhone: z.string().optional(),
  assignee: z.string().optional(),
  context: z.record(z.unknown()).optional(),
  timestamps: taskTimestampsSchema,
  schemaVersion: z.number().default(2),
  metadata: z.record(z.unknown()).optional(),
});

export type PropertyTask = z.infer<typeof propertyTaskSchema>;

export const propertyTaskEventSchema = z.object({
  eventId: z.string(),
  taskId: z.string(),
  propertyId: z.string(),
  hostId: z.string(),
  type: z.string(),
  payload: z.record(z.unknown()).optional(),
  createdAt: z.coerce.date(),
  schemaVersion: z.number().default(2),
  metadata: z.record(z.unknown()).optional(),
});

export type PropertyTaskEvent = z.infer<typeof propertyTaskEventSchema>;

export const emailIntegrationAccountSchema = z.object({
  emailId: z.string(),
  hostId: z.string(),
  provider: z.string(),
  status: z.string(),
  scopes: z.array(z.string()).optional(),
  encryptedAccessToken: z.string().optional(),
  encryptedRefreshToken: z.string().optional(),
  tokenExpiry: z.coerce.date().optional(),
  metadata: z.record(z.unknown()).optional(),
  schemaVersion: z.number().default(2),
  createdAt: z.coerce.date().optional(),
  updatedAt: z.coerce.date().optional(),
  lastHistoryId: z.string().optional(),
});

export type EmailIntegrationAccount = z.infer<typeof emailIntegrationAccountSchema>;

