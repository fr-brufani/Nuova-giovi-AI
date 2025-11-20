import type { Firestore } from "@config/firebase";
import { FirestoreRepository } from "@repositories/base";
import { hostConverter } from "@repositories/converters";
import type { Host } from "@types/domain";

const COLLECTION = "hosts";

export class HostsRepository extends FirestoreRepository {
  constructor(db: Firestore) {
    super(db);
  }

  private collection() {
    return super.collection<Host>(COLLECTION, hostConverter);
  }

  async upsert(host: Host) {
    await this.collection()
      .doc(host.hostId)
      .set(
        {
          ...host,
          hostId: host.hostId,
        },
        { merge: true },
      );
  }

  async get(hostId: string) {
    const snapshot = await this.collection().doc(hostId).get();
    if (!snapshot.exists) return null;
    return snapshot.data();
  }
}

export function getHostsRepository(db: Firestore) {
  return new HostsRepository(db);
}


