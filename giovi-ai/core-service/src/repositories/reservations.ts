import type { Firestore } from "@config/firebase";
import { FirestoreRepository } from "@repositories/base";
import { reservationConverter } from "@repositories/converters";
import type { Reservation } from "@types/domain";

const COLLECTION = "reservations";

export class ReservationsRepository extends FirestoreRepository {
  constructor(db: Firestore) {
    super(db);
  }

  private collection() {
    return super.collection<Reservation>(COLLECTION, reservationConverter);
  }

  async upsert(reservation: Reservation) {
    await this.collection()
      .doc(reservation.reservationId)
      .set(
        {
          ...reservation,
          reservationId: reservation.reservationId,
        },
        { merge: true },
      );
  }

  async findByConversation(conversationId: string) {
    const snapshot = await this.collection()
      .where("conversationId", "==", conversationId)
      .limit(1)
      .get();
    if (snapshot.empty) return null;
    return snapshot.docs[0].data();
  }

  async get(reservationId: string) {
    const doc = await this.collection().doc(reservationId).get();
    if (!doc.exists) return null;
    return doc.data();
  }
}

export function getReservationsRepository(db: Firestore) {
  return new ReservationsRepository(db);
}

