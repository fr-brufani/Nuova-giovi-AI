import { describe, expect, it, vi, beforeEach } from "vitest";

import { emailIngestWorkflow } from "@workflows/emailIngest";
import { parseEmail } from "@parsers/index";
import { getFirestore } from "@config/firebase";
vi.mock("@config/firebase", () => ({
  getFirestore: vi.fn(),
}));

vi.mock("@parsers/index", () => ({
  parseEmail: vi.fn(),
}));

vi.mock("@adapters/gmail", () => {
  const fetchMessage = vi.fn();
  const GmailAdapter = vi.fn(() => ({
    fetchMessage,
  }));
  // Static helpers
  GmailAdapter.extractHeaders = vi.fn(() => ({}));
  GmailAdapter.extractBodies = vi.fn(() => ({ text: "", html: "" }));

  const instance = { fetchMessage };

  return {
    GmailAdapter,
    getGmailAdapter: () => instance,
  };
});

const reservationsRepo = {
  get: vi.fn(),
  findByConversation: vi.fn(),
  upsert: vi.fn(),
};

const clientsRepo = {
  upsert: vi.fn(),
};

const propertiesRepo = {
  upsert: vi.fn(),
  touchConversation: vi.fn(),
  appendMessage: vi.fn(),
};

const integrationsRepo = {
  recordInboundEmail: vi.fn(),
  storeRawEmailPayload: vi.fn(),
  getEmailAccount: vi.fn(),
};

const hostsRepo = {
  upsert: vi.fn(),
};

vi.mock("@repositories/index", () => ({
  getReservationsRepository: vi.fn(() => reservationsRepo),
  getClientsRepository: vi.fn(() => clientsRepo),
  getPropertiesRepository: vi.fn(() => propertiesRepo),
  getIntegrationsRepository: vi.fn(() => integrationsRepo),
  getHostsRepository: vi.fn(() => hostsRepo),
}));

describe("emailIngestWorkflow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getFirestore).mockReturnValue({} as never);
    vi.mocked(parseEmail).mockReset();

    reservationsRepo.get.mockReset();
    reservationsRepo.findByConversation.mockReset();
    reservationsRepo.upsert.mockReset();
    clientsRepo.upsert.mockReset();
    propertiesRepo.upsert.mockReset();
    propertiesRepo.touchConversation.mockReset();
    propertiesRepo.appendMessage.mockReset();
    integrationsRepo.recordInboundEmail.mockReset();
    integrationsRepo.storeRawEmailPayload.mockReset();
    integrationsRepo.getEmailAccount.mockReset();
    hostsRepo.upsert.mockReset();
  });

  it("creates reservation, client, property, and conversation when none exist", async () => {
    const start = new Date("2025-03-10T00:00:00Z");
    const end = new Date("2025-03-15T00:00:00Z");

    vi.mocked(parseEmail).mockReturnValue({
      source: "airbnb_confirm",
      reservationId: "ABC123",
      conversationId: "CONV456",
      hostEmail: "owner@example.com",
      clientEmail: "guest@example.com",
      guestName: "Guest Example",
      stayPeriod: { start, end },
      messageText: "Prenotazione confermata",
      channel: "airbnb",
      reservationStatus: "confirmed",
      propertyName: "Imperial Suite",
      metadata: {
        propertyName: "Imperial Suite",
      },
      raw: {},
    });

    integrationsRepo.getEmailAccount.mockResolvedValue({
      emailId: "owner@example.com",
      hostId: "host-123",
      provider: "gmail",
      status: "connected",
      schemaVersion: 2,
    });

    reservationsRepo.get.mockResolvedValue(null);
    reservationsRepo.findByConversation.mockResolvedValue(null);

    await emailIngestWorkflow({
      provider: "sendgrid",
      emailAddress: "owner@example.com",
      messageId: "message-1",
      headers: { from: "owner@example.com" },
      body: "body content",
      html: "<p>body content</p>",
    });

    expect(integrationsRepo.recordInboundEmail).toHaveBeenCalled();
    expect(reservationsRepo.upsert).toHaveBeenCalledWith(
      expect.objectContaining({
        reservationId: "ABC123",
        hostId: "host-123",
        propertyId: expect.stringContaining("host-123"),
        clientId: expect.stringContaining("client-guest-example-com"),
        status: "confirmed",
      }),
    );

    expect(clientsRepo.upsert).toHaveBeenCalledWith(
      expect.objectContaining({
        clientId: expect.stringContaining("client-guest-example-com"),
        primaryEmail: "guest@example.com",
        primaryHostId: "host-123",
      }),
    );

    expect(propertiesRepo.upsert).toHaveBeenCalledWith(
      expect.objectContaining({
        propertyId: expect.stringContaining("host-123"),
        hostId: "host-123",
        name: "Imperial Suite",
      }),
    );

    expect(propertiesRepo.touchConversation).toHaveBeenCalledWith(
      expect.stringContaining("host-123"),
      "CONV456",
      expect.objectContaining({
        reservationId: "ABC123",
        clientId: expect.stringContaining("client-guest-example-com"),
      }),
    );

    expect(propertiesRepo.appendMessage).toHaveBeenCalledWith(
      expect.stringContaining("host-123"),
      "CONV456",
      "message-1",
      expect.objectContaining({
        direction: "inbound",
        messageId: "message-1",
      }),
    );
  });

  it("reuses existing reservation identifiers when already present", async () => {
    const existingReservation = {
      reservationId: "RES-1",
      hostId: "host-existing",
      propertyId: "prop-existing",
      clientId: "client-existing",
      channel: "airbnb",
      status: "pending",
      stayPeriod: { start: new Date("2025-01-01"), end: new Date("2025-01-05") },
      source: { provider: "airbnb" },
    };

    vi.mocked(parseEmail).mockReturnValue({
      source: "airbnb_message",
      conversationId: "CONV-RES-1",
      clientEmail: "guest@example.com",
      guestName: "Guest Example",
      messageText: "Nuovo messaggio",
      channel: "airbnb",
      raw: {},
    });

    integrationsRepo.getEmailAccount.mockResolvedValue(null);
    reservationsRepo.get.mockResolvedValue(existingReservation);
    reservationsRepo.findByConversation.mockResolvedValue(existingReservation);

    await emailIngestWorkflow({
      provider: "gmail",
      emailAddress: "owner@example.com",
      messageId: "message-2",
      headers: { from: "owner@example.com" },
      body: "body content",
    });

    expect(reservationsRepo.upsert).toHaveBeenCalledWith(
      expect.objectContaining({
        reservationId: "RES-1",
        hostId: "host-existing",
        propertyId: "prop-existing",
        clientId: "client-existing",
      }),
    );

    expect(clientsRepo.upsert).toHaveBeenCalledWith(
      expect.objectContaining({
        clientId: "client-existing",
        primaryHostId: "host-existing",
        primaryPropertyId: "prop-existing",
      }),
    );

    expect(propertiesRepo.touchConversation).toHaveBeenCalledWith(
      "prop-existing",
      "CONV-RES-1",
      expect.objectContaining({
        reservationId: "RES-1",
        clientId: "client-existing",
      }),
    );
  });
});


