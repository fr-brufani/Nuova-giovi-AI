import { vi, describe, it, expect, beforeEach } from "vitest";

import { taskOrchestrationWorkflow } from "@workflows/taskOrchestration";
import { getFirestore } from "@config/firebase";
import {
  getPropertiesRepository,
  getReservationsRepository,
  getTasksRepository,
} from "@repositories/index";
import type { Reservation } from "@types/domain";

vi.mock("@config/firebase", () => ({
  getFirestore: vi.fn(),
}));

vi.mock("@repositories/index", () => {
  const tasksRepo = {
    updateTask: vi.fn(),
    appendTaskEvent: vi.fn(),
  };
  const reservationsRepo = {
    get: vi.fn(),
  };
  const propertiesRepo = {
    touchConversation: vi.fn(),
  };

  return {
    getTasksRepository: vi.fn(() => tasksRepo),
    getReservationsRepository: vi.fn(() => reservationsRepo),
    getPropertiesRepository: vi.fn(() => propertiesRepo),
  };
});

describe("taskOrchestrationWorkflow", () => {
  const tasksRepo = getTasksRepository({} as never);
  const reservationsRepo = getReservationsRepository({} as never);
  const propertiesRepo = getPropertiesRepository({} as never);

  beforeEach(() => {
    vi.mocked(getFirestore).mockReturnValue({} as never);
    vi.clearAllMocks();
  });

  it("creates a new task and appends an event", async () => {
    const reservation: Reservation = {
      reservationId: "res-123",
      hostId: "host-1",
      propertyId: "prop-1",
      clientId: "client-1",
      channel: "email",
      status: "pending",
      stayPeriod: { start: new Date(), end: new Date() },
      source: { provider: "pms" },
    };

    vi.mocked(reservationsRepo.get).mockResolvedValue(reservation);
    vi.mocked(tasksRepo.updateTask).mockImplementation(async (_propertyId, _taskId, updater) => {
      return updater(null);
    });

    await taskOrchestrationWorkflow({
      toolCallId: "tool-1",
      timestamp: new Date().toISOString(),
      payload: {
        reservationId: reservation.reservationId,
        propertyId: reservation.propertyId,
        hostId: reservation.hostId,
        type: "cleaning",
        status: "pending",
      },
    });

    expect(tasksRepo.updateTask).toHaveBeenCalled();
    expect(tasksRepo.appendTaskEvent).toHaveBeenCalled();
    expect(propertiesRepo.touchConversation).toHaveBeenCalledWith(
      reservation.propertyId,
      reservation.conversationId ?? reservation.reservationId,
      expect.objectContaining({
        reservationId: reservation.reservationId,
        clientId: reservation.clientId,
      }),
    );
  });

  it("skips when reservation does not exist", async () => {
    vi.mocked(reservationsRepo.get).mockResolvedValue(null);

    await taskOrchestrationWorkflow({
      toolCallId: "tool-2",
      timestamp: new Date().toISOString(),
      payload: {
        reservationId: "missing",
        propertyId: "prop-2",
        hostId: "host-2",
        type: "todo",
      },
    });

    expect(tasksRepo.updateTask).not.toHaveBeenCalled();
    expect(tasksRepo.appendTaskEvent).not.toHaveBeenCalled();
  });
});


