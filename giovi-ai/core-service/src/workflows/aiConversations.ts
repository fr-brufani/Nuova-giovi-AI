import { getGeminiAdapter, getSendGridAdapter, getWhatsAppAdapter, getPubSubAdapter } from "@adapters/index";
import { getFirestore } from "@config/firebase";
import { getClientsRepository, getPropertiesRepository } from "@repositories/index";
import { logger } from "@utils/logger";

export type ChatRequest = {
  reservationId: string;
  propertyId: string;
  clientId: string;
  prompt: string;
  channel: "email" | "whatsapp";
  meta?: Record<string, unknown>;
};

const gemini = getGeminiAdapter();
const sendgrid = getSendGridAdapter();
const whatsapp = getWhatsAppAdapter();
const pubsub = getPubSubAdapter();

export async function handleChatRequest(request: ChatRequest) {
  const db = getFirestore();
  const clientsRepo = getClientsRepository(db);

  try {
    const client = await clientsRepo.get(request.clientId);
    if (client && client.autoReplyEnabled === false) {
      logger.info(
        { clientId: request.clientId, reservationId: request.reservationId },
        "auto reply disabled for client, skipping AI response",
      );
      return;
    }
  } catch (error) {
    logger.error({ err: error, clientId: request.clientId }, "failed to load client preferences");
  }

  let response;
  try {
    response = await gemini.generate(request.prompt, request.meta);
  } catch (error) {
    logger.error({ err: error, request }, "gemini generate failed");
    throw error;
  }
  const propertiesRepo = getPropertiesRepository(db);

  const messageText = response.text;

  if (request.channel === "email") {
    if (!request.meta?.email) throw new Error("email metadata required for email channel");
    try {
      await sendgrid.sendEmail({
        to: String(request.meta.email),
        from: String(request.meta.from ?? "concierge@giovi.ai"),
        subject: String(request.meta.subject ?? "Risposta Giovi AI"),
        text: messageText,
      });
    } catch (error) {
      logger.error({ err: error, email: request.meta.email }, "sendgrid send failed");
      throw error;
    }
  } else if (request.channel === "whatsapp") {
    if (!request.meta?.phoneNumberId || !request.meta?.to) throw new Error("whatsapp metadata missing (phoneNumberId, to)");
    try {
      await whatsapp.sendMessage(String(request.meta.phoneNumberId), {
        messaging_product: "whatsapp",
        to: request.meta.to,
        type: "text",
        text: { body: messageText },
      });
    } catch (error) {
      logger.error({ err: error, to: request.meta.to }, "whatsapp send failed");
      throw error;
    }
  }

  try {
    await propertiesRepo.appendMessage(
      request.propertyId,
      request.reservationId,
      `ai-${Date.now()}`,
      {
        reservationId: request.reservationId,
        propertyId: request.propertyId,
        clientId: request.clientId,
        channel: request.channel,
        direction: "outbound",
        sentAt: new Date(),
        body: messageText,
        provider: "gemini",
        rawHeaders: response.toolCalls ? { toolCalls: response.toolCalls } : undefined,
      },
    );
  } catch (error) {
    logger.error({ err: error, reservationId: request.reservationId }, "failed to append AI response");
    throw error;
  }

  if (response.toolCalls?.length) {
    try {
      await pubsub.publish("tasks-tool-call", {
        reservationId: request.reservationId,
        propertyId: request.propertyId,
        hostId: request.meta?.hostId,
        toolCalls: response.toolCalls,
      });
    } catch (error) {
      logger.error({ err: error, reservationId: request.reservationId }, "failed to publish tool calls");
    }
  }

  logger.info({ reservationId: request.reservationId }, "ai response generated");
}


