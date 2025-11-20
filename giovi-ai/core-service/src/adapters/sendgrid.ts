import sgMail from "@sendgrid/mail";

import { loadEnvironment } from "@config/env";
import { logger } from "@utils/logger";

export class SendGridAdapter {
  private readonly disabled: boolean;

  constructor() {
    const env = loadEnvironment();
    const keySecret = env.SENDGRID_API_KEY_SECRET;
    if (!keySecret) {
      this.disabled = true;
      logger.warn("SendGrid API key missing, email sending disabled");
      return;
    }
    if (!keySecret.startsWith("SG.")) {
      this.disabled = true;
      logger.warn("SendGrid API key invalid format, email sending disabled");
      return;
    }
    sgMail.setApiKey(keySecret);
    this.disabled = false;
  }

  async sendEmail(payload: sgMail.MailDataRequired) {
    if (this.disabled) {
      throw new Error("sendgrid_disabled");
    }
    await sgMail.send(payload);
  }
}

let sendGridAdapterInstance: SendGridAdapter | null = null;

export function getSendGridAdapter() {
  if (!sendGridAdapterInstance) {
    sendGridAdapterInstance = new SendGridAdapter();
  }
  return sendGridAdapterInstance;
}


