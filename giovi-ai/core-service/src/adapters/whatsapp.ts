import axios from "axios";

import { loadEnvironment } from "@config/env";

export class WhatsAppAdapter {
  private readonly token: string;

  constructor() {
    const env = loadEnvironment();
    if (!env.WHATSAPP_TOKEN_SECRET) {
      throw new Error("WHATSAPP_TOKEN_SECRET missing");
    }
    this.token = env.WHATSAPP_TOKEN_SECRET;
  }

  async sendMessage(phoneNumberId: string, payload: Record<string, unknown>) {
    await axios.post(`https://graph.facebook.com/v19.0/${phoneNumberId}/messages`, payload, {
      headers: {
        Authorization: `Bearer ${this.token}`,
      },
    });
  }
}

let whatsappAdapterInstance: WhatsAppAdapter | null = null;

export function getWhatsAppAdapter() {
  if (!whatsappAdapterInstance) {
    whatsappAdapterInstance = new WhatsAppAdapter();
  }
  return whatsappAdapterInstance;
}


