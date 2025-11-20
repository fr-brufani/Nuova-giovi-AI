import admin from "firebase-admin";

import { getFirestore } from "@config/firebase";
import { logger } from "@utils/logger";

export type HostResetResult = {
  hostId: string;
  propertiesDeleted: number;
  reservationsDeleted: number;
  clientsDeleted: number;
};

export async function resetHostData(hostId: string): Promise<HostResetResult> {
  const db = getFirestore();

  let propertiesDeleted = 0;
  const propertiesSnapshot = await db.collection("properties").where("hostId", "==", hostId).get();
  for (const doc of propertiesSnapshot.docs) {
    await admin.firestore().recursiveDelete(doc.ref);
    propertiesDeleted += 1;
  }

  const reservationsSnapshot = await db.collection("reservations").where("hostId", "==", hostId).get();
  await Promise.all(reservationsSnapshot.docs.map((doc) => doc.ref.delete()));
  const reservationsDeleted = reservationsSnapshot.size;

  const clientsSnapshot = await db.collection("clients").where("primaryHostId", "==", hostId).get();
  await Promise.all(clientsSnapshot.docs.map((doc) => doc.ref.delete()));
  const clientsDeleted = clientsSnapshot.size;

  logger.info(
    { hostId, propertiesDeleted, reservationsDeleted, clientsDeleted },
    "host data reset completed",
  );

  return { hostId, propertiesDeleted, reservationsDeleted, clientsDeleted };
}


