import { FieldValue } from "firebase-admin/firestore";

import type { Firestore } from "@config/firebase";
import { FirestoreRepository } from "@repositories/base";
import { conversationMessageConverter, propertyConverter } from "@repositories/converters";
import type { ConversationMessage, Property } from "@types/domain";

const COLLECTION = "properties";

export class PropertiesRepository extends FirestoreRepository {
  constructor(db: Firestore) {
    super(db);
  }

  private collection() {
    return super.collection<Property>(COLLECTION, propertyConverter);
  }

  private conversationCollection(propertyId: string) {
    return super.collection(`${COLLECTION}/${propertyId}/conversations`);
  }

  private conversationMessagesCollection(propertyId: string, conversationId: string) {
    return super
      .collection<ConversationMessage>(
        `${COLLECTION}/${propertyId}/conversations/${conversationId}/messages`,
        conversationMessageConverter,
      );
  }

  async upsert(property: Property) {
    await this.collection().doc(property.propertyId).set(property, { merge: true });
  }

  async get(propertyId: string) {
    const doc = await this.collection().doc(propertyId).get();
    if (!doc.exists) return null;
    return doc.data();
  }

  async touchConversation(propertyId: string, conversationId: string, payload: Record<string, unknown>) {
    const ref = this.conversationCollection(propertyId).doc(conversationId);
    const schemaVersion = (payload as { schemaVersion?: number }).schemaVersion ?? 2;
    await ref.set(
      {
        ...payload,
        conversationId,
        schemaVersion,
        updatedAt: FieldValue.serverTimestamp(),
      },
      { merge: true },
    );
    return ref;
  }

  async appendMessage(propertyId: string, conversationId: string, messageId: string, data: ConversationMessage) {
    await this.conversationMessagesCollection(propertyId, conversationId).doc(messageId).set(data, { merge: true });
  }
}

export function getPropertiesRepository(db: Firestore) {
  return new PropertiesRepository(db);
}

