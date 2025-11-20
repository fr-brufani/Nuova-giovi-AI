import {
  emailIngestWorkflow,
  handleChatRequest,
  pmsImportWorkflow,
  taskOrchestrationWorkflow,
} from "@workflows/index";
import { logger } from "@utils/logger";

export type PubSubEnvelope =
  | {
      type: "gmail.email";
      payload: {
        emailAddress: string;
        messageId: string;
      };
    }
  | {
      type: "chat.request";
      payload: Parameters<typeof handleChatRequest>[0];
    }
  | {
      type: "pms.import";
      payload: Parameters<typeof pmsImportWorkflow>[0];
    }
  | {
      type: "tasks.toolCall";
      payload: Parameters<typeof taskOrchestrationWorkflow>[0];
    };

export async function handlePubSubMessage(envelope: PubSubEnvelope) {
  switch (envelope.type) {
    case "gmail.email": {
      try {
        await emailIngestWorkflow({
          provider: "gmail",
          emailAddress: envelope.payload.emailAddress,
          messageId: envelope.payload.messageId,
          headers: {},
          body: "",
          rawNotification: envelope.payload,
        });
      } catch (error) {
        logger.error({ err: error, payload: envelope.payload }, "pubsub gmail ingest failed");
        throw error;
      }
      break;
    }
    case "chat.request": {
      try {
        await handleChatRequest(envelope.payload);
      } catch (error) {
        logger.error({ err: error, payload: envelope.payload }, "pubsub chat request failed");
        throw error;
      }
      break;
    }
    case "pms.import": {
      try {
        await pmsImportWorkflow(envelope.payload);
      } catch (error) {
        logger.error({ err: error, payload: { count: envelope.payload.length } }, "pubsub pms import failed");
        throw error;
      }
      break;
    }
    case "tasks.toolCall": {
      try {
        await taskOrchestrationWorkflow(envelope.payload);
      } catch (error) {
        logger.error({ err: error, payload: envelope.payload }, "pubsub task orchestration failed");
        throw error;
      }
      break;
    }
    default:
      logger.warn({ envelope }, "unknown pubsub envelope");
  }
}

