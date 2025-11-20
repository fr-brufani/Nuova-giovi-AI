import type { Firestore } from "@config/firebase";
import { FirestoreRepository } from "@repositories/base";
import { clientConverter } from "@repositories/converters";
import type { Client } from "@types/domain";
import { FieldValue } from "firebase-admin/firestore";

const COLLECTION = "clients";

export class ClientsRepository extends FirestoreRepository {
  constructor(db: Firestore) {
    super(db);
  }

  private collectionRef() {
    return super.collection<Client>(COLLECTION, clientConverter);
  }

  async upsert(client: Client) {
    await this.collectionRef().doc(client.clientId).set(client, { merge: true });
  }

  async findByEmail(email: string) {
    const snapshot = await this.collectionRef().where("primaryEmail", "==", email).limit(1).get();
    if (snapshot.empty) return null;
    return snapshot.docs[0].data();
  }

  async get(clientId: string) {
    const snapshot = await this.collectionRef().doc(clientId).get();
    if (!snapshot.exists) return null;
    return snapshot.data();
  }

  async updateAutoReply(clientId: string, enabled: boolean) {
    await this.doc(`${COLLECTION}/${clientId}`).set(
      {
        autoReplyEnabled: enabled,
        updatedAt: FieldValue.serverTimestamp(),
      },
      { merge: true },
    );
  }
}

export function getClientsRepository(db: Firestore) {
  return new ClientsRepository(db);
}

