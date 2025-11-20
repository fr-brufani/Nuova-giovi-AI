import type { Firestore } from "@config/firebase";
import { FirestoreRepository } from "@repositories/base";
import { emailIntegrationConverter } from "@repositories/converters";
import type { EmailIntegrationAccount } from "@types/domain";

const EMAIL_ACCOUNTS_COLLECTION = "integrations/email/accounts";

export class IntegrationsRepository extends FirestoreRepository {
  constructor(db: Firestore) {
    super(db);
  }

  private emailAccountsCollection() {
    return super.collection<EmailIntegrationAccount>(EMAIL_ACCOUNTS_COLLECTION, emailIntegrationConverter);
  }

  private emailAccountDoc(emailId: string) {
    return this.emailAccountsCollection().doc(emailId);
  }

  private emailAccountSubcollection(emailId: string, subCollection: string) {
    return super.collection(`${EMAIL_ACCOUNTS_COLLECTION}/${emailId}/${subCollection}`);
  }

  async upsertEmailAccount(account: EmailIntegrationAccount) {
    await this.emailAccountDoc(account.emailId).set(
      {
        ...account,
        emailId: account.emailId,
      },
      { merge: true },
    );
  }

  async getEmailAccount(emailId: string) {
    const snapshot = await this.emailAccountDoc(emailId).get();
    if (!snapshot.exists) return null;
    return snapshot.data();
  }

  async updateEmailHistoryCursor(emailId: string, historyId: string) {
    await this.emailAccountDoc(emailId).set(
      {
        lastHistoryId: historyId,
      },
      { merge: true },
    );
  }

  async recordInboundEmail(emailId: string, messageId: string, data: Record<string, unknown>) {
    await this.emailAccountSubcollection(emailId, "messages")
      .doc(messageId)
      .set(
        {
          emailId,
          messageId,
          ...data,
          receivedAt: new Date(),
        },
        { merge: true },
      );
  }

  async storeRawEmailPayload(emailId: string, messageId: string, payload: unknown) {
    await this.emailAccountSubcollection(emailId, "rawPayloads")
      .doc(messageId)
      .set({
        emailId,
        messageId,
        payload,
        storedAt: new Date(),
      });
  }

  async acquireEmailLock(emailId: string, lockId: string, data: Record<string, unknown>) {
    await this.emailAccountSubcollection(emailId, "locks")
      .doc(lockId)
      .set({
        ...data,
        lockedAt: new Date(),
      });
  }

  async saveGmailOAuthTokens(params: {
    hostId: string;
    emailId: string;
    accessToken: string;
    refreshToken?: string;
    expiryDate?: Date;
  }) {
    await this.emailAccountDoc(params.emailId).set(
      {
        emailId: params.emailId,
        hostId: params.hostId,
        provider: "gmail-oauth",
        status: "connected",
        encryptedAccessToken: params.accessToken,
        encryptedRefreshToken: params.refreshToken,
        tokenExpiry: params.expiryDate,
        metadata: {
          updatedAt: new Date().toISOString(),
        },
      },
      { merge: true },
    );
  }
}

export function getIntegrationsRepository(db: Firestore) {
  return new IntegrationsRepository(db);
}


