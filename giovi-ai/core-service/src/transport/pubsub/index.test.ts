import { describe, expect, it, vi, beforeEach } from "vitest";

import { handlePubSubMessage } from "@transport/pubsub";
import {
  emailIngestWorkflow,
  handleChatRequest,
  pmsImportWorkflow,
  taskOrchestrationWorkflow,
} from "@workflows/index";

vi.mock("@workflows/index", () => ({
  emailIngestWorkflow: vi.fn(),
  handleChatRequest: vi.fn(),
  pmsImportWorkflow: vi.fn(),
  taskOrchestrationWorkflow: vi.fn(),
}));

describe("handlePubSubMessage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("routes gmail envelopes to email ingest workflow", async () => {
    await handlePubSubMessage({
      type: "gmail.email",
      payload: {
        emailAddress: "owner@example.com",
        messageId: "123",
      },
    });

    expect(emailIngestWorkflow).toHaveBeenCalledWith(
      expect.objectContaining({
        provider: "gmail",
        emailAddress: "owner@example.com",
        messageId: "123",
      }),
    );
  });

  it("routes chat requests", async () => {
    await handlePubSubMessage({
      type: "chat.request",
      payload: {
        reservationId: "res-1",
        propertyId: "prop-1",
        clientId: "client-1",
        prompt: "Hello",
        channel: "email",
      },
    });

    expect(handleChatRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        reservationId: "res-1",
        prompt: "Hello",
      }),
    );
  });

  it("routes PMS import envelopes", async () => {
    await handlePubSubMessage({
      type: "pms.import",
      payload: [
        {
          reservationId: "r-1",
          hostId: "h-1",
          propertyId: "p-1",
          clientId: "c-1",
          channel: "booking",
          status: "confirmed",
          stayPeriod: { start: "2025-01-01", end: "2025-01-03" },
        },
      ],
    });

    expect(pmsImportWorkflow).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({
          reservationId: "r-1",
        }),
      ]),
    );
  });

  it("routes task tool call envelopes", async () => {
    await handlePubSubMessage({
      type: "tasks.toolCall",
      payload: {
        toolCallId: "tool-123",
        timestamp: new Date().toISOString(),
        payload: {
          reservationId: "res-1",
          propertyId: "prop-1",
          hostId: "host-1",
          type: "cleaning",
        },
      },
    });

    expect(taskOrchestrationWorkflow).toHaveBeenCalledWith(
      expect.objectContaining({
        toolCallId: "tool-123",
        payload: expect.objectContaining({
          reservationId: "res-1",
          type: "cleaning",
        }),
      }),
    );
  });
});


