import admin from "firebase-admin";

import { loadEnvironment } from "@config/env";
import { logger } from "@utils/logger";

let initialized = false;

export function getFirestore() {
  if (!initialized) {
    const env = loadEnvironment();

    if (!admin.apps.length) {
      admin.initializeApp({
        credential: admin.credential.applicationDefault(),
        databaseURL: env.FIREBASE_DATABASE_URL,
      });
      logger.info("firebase admin initialized");
    }
    initialized = true;
  }

  return admin.firestore();
}

export type Firestore = ReturnType<typeof getFirestore>;


