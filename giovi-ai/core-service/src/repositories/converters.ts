import { FieldValue, Timestamp, type FirestoreDataConverter } from "firebase-admin/firestore";

import {
  clientSchema,
  conversationMessageSchema,
  emailIntegrationAccountSchema,
  hostSchema,
  propertySchema,
  propertyTaskEventSchema,
  propertyTaskSchema,
  reservationSchema,
  type Client,
  type ConversationMessage,
  type EmailIntegrationAccount,
  type Host,
  type Property,
  type PropertyTask,
  type PropertyTaskEvent,
  type Reservation,
} from "@types/domain";

type FirestoreTimestamp = Timestamp | Date | undefined | null;
const FIRESTORE_SCHEMA_VERSION = 2;

function ensureTimestamp(value: FirestoreTimestamp) {
  if (!value) return undefined;
  if (value instanceof Timestamp) return value;
  if (value instanceof Date) return Timestamp.fromDate(value);
  return undefined;
}

function toDate(value: unknown, fallback?: Date): Date | undefined {
  if (!value) return undefined;
  if (value instanceof Date) return value;
  if (value instanceof Timestamp) return value.toDate();
  return fallback;
}

export const reservationConverter: FirestoreDataConverter<Reservation> = {
  toFirestore(reservation) {
    return {
      ...reservation,
      schemaVersion: reservation.schemaVersion ?? FIRESTORE_SCHEMA_VERSION,
      stayPeriod: {
        start: ensureTimestamp(reservation.stayPeriod.start) ?? FieldValue.serverTimestamp(),
        end: ensureTimestamp(reservation.stayPeriod.end) ?? FieldValue.serverTimestamp(),
      },
      createdAt: ensureTimestamp(reservation.createdAt) ?? FieldValue.serverTimestamp(),
      updatedAt: FieldValue.serverTimestamp(),
    };
  },
  fromFirestore(snapshot) {
    const data = snapshot.data();
    return reservationSchema.parse({
      ...data,
      reservationId: data.reservationId ?? snapshot.id,
      stayPeriod: {
        start: toDate(data.stayPeriod?.start) ?? new Date(),
        end: toDate(data.stayPeriod?.end) ?? new Date(),
      },
      createdAt: toDate(data.createdAt),
      updatedAt: toDate(data.updatedAt),
    });
  },
};

export const clientConverter: FirestoreDataConverter<Client> = {
  toFirestore(client) {
    return {
      ...client,
      schemaVersion: client.schemaVersion ?? FIRESTORE_SCHEMA_VERSION,
      createdAt: ensureTimestamp(client.createdAt) ?? FieldValue.serverTimestamp(),
      updatedAt: FieldValue.serverTimestamp(),
    };
  },
  fromFirestore(snapshot) {
    const data = snapshot.data();
    return clientSchema.parse({
      ...data,
      clientId: data.clientId ?? snapshot.id,
      createdAt: toDate(data.createdAt),
      updatedAt: toDate(data.updatedAt),
    });
  },
};

export const hostConverter: FirestoreDataConverter<Host> = {
  toFirestore(host) {
    return {
      ...host,
      schemaVersion: host.schemaVersion ?? FIRESTORE_SCHEMA_VERSION,
      createdAt: ensureTimestamp(host.createdAt) ?? FieldValue.serverTimestamp(),
      updatedAt: FieldValue.serverTimestamp(),
    };
  },
  fromFirestore(snapshot) {
    const data = snapshot.data();
    return hostSchema.parse({
      ...data,
      hostId: data.hostId ?? snapshot.id,
      createdAt: toDate(data.createdAt),
      updatedAt: toDate(data.updatedAt),
    });
  },
};

export const propertyConverter: FirestoreDataConverter<Property> = {
  toFirestore(property) {
    return {
      ...property,
      schemaVersion: property.schemaVersion ?? FIRESTORE_SCHEMA_VERSION,
      createdAt: ensureTimestamp(property.createdAt) ?? FieldValue.serverTimestamp(),
      updatedAt: FieldValue.serverTimestamp(),
    };
  },
  fromFirestore(snapshot) {
    const data = snapshot.data();
    return propertySchema.parse({
      ...data,
      propertyId: data.propertyId ?? snapshot.id,
      createdAt: toDate(data.createdAt),
      updatedAt: toDate(data.updatedAt),
    });
  },
};

export const propertyTaskConverter: FirestoreDataConverter<PropertyTask> = {
  toFirestore(task) {
    return {
      ...task,
      schemaVersion: task.schemaVersion ?? FIRESTORE_SCHEMA_VERSION,
      timestamps: {
        createdAt: ensureTimestamp(task.timestamps?.createdAt) ?? FieldValue.serverTimestamp(),
        updatedAt: FieldValue.serverTimestamp(),
        dueAt: ensureTimestamp(task.timestamps?.dueAt),
        scheduledAt: ensureTimestamp(task.timestamps?.scheduledAt),
        completedAt: ensureTimestamp(task.timestamps?.completedAt),
        cancelledAt: ensureTimestamp(task.timestamps?.cancelledAt),
      },
    };
  },
  fromFirestore(snapshot) {
    const data = snapshot.data();
    return propertyTaskSchema.parse({
      ...data,
      taskId: data.taskId ?? snapshot.id,
      timestamps: {
        createdAt: toDate(data.timestamps?.createdAt) ?? new Date(),
        updatedAt: toDate(data.timestamps?.updatedAt) ?? new Date(),
        dueAt: toDate(data.timestamps?.dueAt),
        scheduledAt: toDate(data.timestamps?.scheduledAt),
        completedAt: toDate(data.timestamps?.completedAt),
        cancelledAt: toDate(data.timestamps?.cancelledAt),
      },
    });
  },
};

export const propertyTaskEventConverter: FirestoreDataConverter<PropertyTaskEvent> = {
  toFirestore(event) {
    return {
      ...event,
      schemaVersion: event.schemaVersion ?? FIRESTORE_SCHEMA_VERSION,
      createdAt: ensureTimestamp(event.createdAt) ?? FieldValue.serverTimestamp(),
    };
  },
  fromFirestore(snapshot) {
    const data = snapshot.data();
    return propertyTaskEventSchema.parse({
      ...data,
      eventId: data.eventId ?? snapshot.id,
      createdAt: toDate(data.createdAt) ?? new Date(),
    });
  },
};

export const conversationMessageConverter: FirestoreDataConverter<ConversationMessage> = {
  toFirestore(message) {
    return {
      ...message,
      schemaVersion: message.schemaVersion ?? FIRESTORE_SCHEMA_VERSION,
      sentAt: ensureTimestamp(message.sentAt) ?? FieldValue.serverTimestamp(),
      createdAt: ensureTimestamp(message.createdAt) ?? FieldValue.serverTimestamp(),
      updatedAt: FieldValue.serverTimestamp(),
    };
  },
  fromFirestore(snapshot) {
    const data = snapshot.data();
    return conversationMessageSchema.parse({
      ...data,
      messageId: data.messageId ?? snapshot.id,
      sentAt: toDate(data.sentAt) ?? new Date(),
      createdAt: toDate(data.createdAt),
      updatedAt: toDate(data.updatedAt),
    });
  },
};

export const emailIntegrationConverter: FirestoreDataConverter<EmailIntegrationAccount> = {
  toFirestore(integration) {
    return {
      ...integration,
      schemaVersion: integration.schemaVersion ?? FIRESTORE_SCHEMA_VERSION,
      tokenExpiry: ensureTimestamp(integration.tokenExpiry),
      createdAt: ensureTimestamp(integration.createdAt) ?? FieldValue.serverTimestamp(),
      updatedAt: FieldValue.serverTimestamp(),
    };
  },
  fromFirestore(snapshot) {
    const data = snapshot.data();
    return emailIntegrationAccountSchema.parse({
      ...data,
      emailId: data.emailId ?? snapshot.id,
      tokenExpiry: toDate(data.tokenExpiry),
      createdAt: toDate(data.createdAt),
      updatedAt: toDate(data.updatedAt),
    });
  },
};

