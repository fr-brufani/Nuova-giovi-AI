import { FieldValue, Timestamp } from "firebase-admin/firestore";

import { getFirestore } from "@config/firebase";
import {
  getReservationsRepository,
  getClientsRepository,
  getPropertiesRepository,
  getHostsRepository,
  getIntegrationsRepository,
} from "@repositories/index";
import { clientSchema, reservationSchema, type Reservation } from "@types/domain";
import { logger } from "@utils/logger";

export type PmsReservationPayload = {
  reservationId: string;
  hostId: string;
  propertyId: string;
  clientId: string;
  channel: string;
  status: string;
  stayPeriod: { start: string; end: string };
  totals?: { amount: number; currency: string; extras?: number | null };
  raw?: Record<string, unknown>;
  client?: { fullName: string; email: string; phone?: string };
  metadata?: Record<string, unknown>;
};

export async function pmsImportWorkflow(reservations: PmsReservationPayload[]) {
  const db = getFirestore();
  const reservationsRepo = getReservationsRepository(db);
  const clientsRepo = getClientsRepository(db);
  const propertiesRepo = getPropertiesRepository(db);
  const hostsRepo = getHostsRepository(db);
  const integrationsRepo = getIntegrationsRepository(db);

  for (const pmsReservation of reservations) {
    const stayPeriod = {
      start: new Date(pmsReservation.stayPeriod.start),
      end: new Date(pmsReservation.stayPeriod.end),
    };

    const reservationDoc: Reservation = reservationSchema.parse({
      reservationId: pmsReservation.reservationId,
      hostId: pmsReservation.hostId,
      propertyId: pmsReservation.propertyId,
      clientId: pmsReservation.clientId,
      channel: pmsReservation.channel,
      status: pmsReservation.status,
      stayPeriod,
      source: {
        provider: "pms-import",
        externalId: pmsReservation.reservationId,
      },
      totals: pmsReservation.totals,
      metadata: {
        ...(pmsReservation.metadata ?? {}),
        importedAt: new Date().toISOString(),
      },
      schemaVersion: 2,
    });

    await reservationsRepo.upsert(reservationDoc);

    if (pmsReservation.client?.email) {
      const clientDoc = clientSchema.parse({
        clientId: pmsReservation.clientId,
        fullName: pmsReservation.client?.fullName ?? pmsReservation.clientId,
        primaryEmail: pmsReservation.client.email,
        primaryPhone: pmsReservation.client.phone,
        primaryHostId: pmsReservation.hostId,
        primaryPropertyId: pmsReservation.propertyId,
        activeReservationId: pmsReservation.reservationId,
        schemaVersion: 2,
      });

      await clientsRepo.upsert(clientDoc);
    }

    await propertiesRepo.touchConversation(pmsReservation.propertyId, reservationDoc.reservationId, {
      reservationId: reservationDoc.reservationId,
      channel: reservationDoc.channel,
      source: "pms-import",
      hostId: pmsReservation.hostId,
      clientId: pmsReservation.clientId,
      schemaVersion: 2,
      updatedAt: FieldValue.serverTimestamp(),
      lastMessagePreview: "Imported via PMS",
      lastMessageAt: FieldValue.serverTimestamp(),
      lastDirection: "system",
    });

    if (pmsReservation.raw) {
      await integrationsRepo.storeRawEmailPayload("pms", reservationDoc.reservationId, {
        propertyId: pmsReservation.propertyId,
        hostId: pmsReservation.hostId,
        payload: pmsReservation.raw,
        storedAt: Timestamp.now().toDate(),
      });
    }

    const host = await hostsRepo.get(pmsReservation.hostId);
    if (!host) {
      await hostsRepo.upsert({
        hostId: pmsReservation.hostId,
        displayName: `Host ${pmsReservation.hostId}`,
        email: `${pmsReservation.hostId}@example.com`,
        status: "active",
        schemaVersion: 2,
      });
    }
  }

  logger.info({ count: reservations.length }, "pms import processed");
}
