import { beforeEach, describe, expect, it, vi } from "vitest";

import { pmsImportWorkflow } from "@workflows/pmsImport";
import { getFirestore } from "@config/firebase";

const reservationsRepo = {
  upsert: vi.fn(),
};

const clientsRepo = {
  upsert: vi.fn(),
};

const propertiesRepo = {
  touchConversation: vi.fn(),
};

const hostsRepo = {
  get: vi.fn(),
  upsert: vi.fn(),
};

const integrationsRepo = {
  storeRawEmailPayload: vi.fn(),
};

vi.mock("@config/firebase", () => ({
  getFirestore: vi.fn(),
}));

vi.mock("@repositories/index", () => ({
  getReservationsRepository: vi.fn(() => reservationsRepo),
  getClientsRepository: vi.fn(() => clientsRepo),
  getPropertiesRepository: vi.fn(() => propertiesRepo),
  getHostsRepository: vi.fn(() => hostsRepo),
  getIntegrationsRepository: vi.fn(() => integrationsRepo),
}));

describe("pmsImportWorkflow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getFirestore).mockReturnValue({} as never);
  });

  it("persists reservations and clients with totals and metadata", async () => {
    hostsRepo.get.mockResolvedValue(null);

    await pmsImportWorkflow([
      {
        reservationId: "res-1",
        hostId: "host-1",
        propertyId: "prop-1",
        clientId: "client-1",
        channel: "booking",
        status: "confirmed",
        stayPeriod: {
          start: "2025-02-01",
          end: "2025-02-05",
        },
        totals: {
          amount: 349.55,
          currency: "EUR",
          extras: 90,
        },
        client: {
          fullName: "Francesco Brufani",
          email: "guest@example.com",
          phone: "+39 331 5681407",
        },
        metadata: {
          source: "booking.com",
        },
        raw: {
          source: "csv",
        },
      },
    ]);

    expect(reservationsRepo.upsert).toHaveBeenCalledWith(
      expect.objectContaining({
        reservationId: "res-1",
        hostId: "host-1",
        propertyId: "prop-1",
        totals: expect.objectContaining({
          amount: 349.55,
          currency: "EUR",
          extras: 90,
        }),
        metadata: expect.objectContaining({
          source: "booking.com",
        }),
      }),
    );

    expect(clientsRepo.upsert).toHaveBeenCalledWith(
      expect.objectContaining({
        clientId: "client-1",
        primaryEmail: "guest@example.com",
        primaryPhone: "+39 331 5681407",
        primaryHostId: "host-1",
        activeReservationId: "res-1",
      }),
    );

    expect(propertiesRepo.touchConversation).toHaveBeenCalledWith(
      "prop-1",
      "res-1",
      expect.objectContaining({
        reservationId: "res-1",
        hostId: "host-1",
      }),
    );

    expect(hostsRepo.upsert).toHaveBeenCalledWith(
      expect.objectContaining({
        hostId: "host-1",
      }),
    );

    expect(integrationsRepo.storeRawEmailPayload).toHaveBeenCalledWith(
      "pms",
      "res-1",
      expect.objectContaining({
        hostId: "host-1",
        propertyId: "prop-1",
      }),
    );
  });
});


