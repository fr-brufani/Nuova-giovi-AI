import { FieldValue } from "firebase-admin/firestore";
import { nanoid } from "nanoid";

import { getFirestore } from "@config/firebase";
import { getPropertiesRepository, getReservationsRepository, getTasksRepository } from "@repositories/index";
import type { PropertyTask, PropertyTaskEvent } from "@types/domain";
import { logger } from "@utils/logger";

type GeminiToolCallTaskPayload = {
  reservationId: string;
  propertyId: string;
  hostId: string;
  taskId?: string;
  type: string;
  title?: string;
  details?: Record<string, unknown>;
  status?: string;
  priority?: string;
  providerPhone?: string;
  assignee?: string;
  dueAt?: string;
  scheduledAt?: string;
};

export type TaskOrchestrationEnvelope = {
  toolCallId: string;
  timestamp: string;
  payload: GeminiToolCallTaskPayload;
};

export async function taskOrchestrationWorkflow(envelope: TaskOrchestrationEnvelope) {
  const db = getFirestore();
  const tasksRepo = getTasksRepository(db);
  const reservationsRepo = getReservationsRepository(db);
  const propertiesRepo = getPropertiesRepository(db);

  const { payload } = envelope;
  const reservation = await reservationsRepo.get(payload.reservationId);

  if (!reservation) {
    logger.warn({ payload }, "task orchestration skipped: reservation not found");
    return;
  }

  const propertyId = payload.propertyId ?? reservation.propertyId;
  const hostId = payload.hostId ?? reservation.hostId;
  const taskId = payload.taskId ?? nanoid();

  const timestamps: PropertyTask["timestamps"] = {
    createdAt: new Date(),
    updatedAt: new Date(),
    dueAt: payload.dueAt ? new Date(payload.dueAt) : undefined,
    scheduledAt: payload.scheduledAt ? new Date(payload.scheduledAt) : undefined,
  };

  const task: PropertyTask = {
    taskId,
    propertyId,
    hostId,
    reservationId: reservation.reservationId,
    status: payload.status ?? "pending",
    type: payload.type,
    title: payload.title,
    priority: payload.priority,
    details: payload.details,
    providerPhone: payload.providerPhone,
    assignee: payload.assignee,
    context: {
      toolCallId: envelope.toolCallId,
      generatedAt: envelope.timestamp,
    },
    timestamps,
    schemaVersion: 2,
  };

  const persistedTask = await tasksRepo.updateTask(propertyId, taskId, (current) => {
    if (!current) {
      return task;
    }

    const nextTask: PropertyTask = {
      ...current,
      ...task,
      timestamps: {
        ...current.timestamps,
        updatedAt: new Date(),
        dueAt: task.timestamps.dueAt ?? current.timestamps.dueAt,
        scheduledAt: task.timestamps.scheduledAt ?? current.timestamps.scheduledAt,
        completedAt: task.timestamps.completedAt ?? current.timestamps.completedAt,
        cancelledAt: task.timestamps.cancelledAt ?? current.timestamps.cancelledAt,
      },
    };

    return nextTask;
  });

  const event: PropertyTaskEvent = {
    eventId: envelope.toolCallId,
    taskId: persistedTask.taskId,
    propertyId,
    hostId,
    type: "gemini.toolCall",
    payload: {
      toolCallId: envelope.toolCallId,
      ...payload,
    },
    createdAt: new Date(),
    schemaVersion: 2,
  };

  await tasksRepo.appendTaskEvent(propertyId, persistedTask.taskId, event);

  const conversationId = reservation.conversationId ?? reservation.reservationId;
  await propertiesRepo.touchConversation(propertyId, conversationId, {
    reservationId: reservation.reservationId,
    clientId: reservation.clientId,
    hostId,
    schemaVersion: 2,
    updatedAt: FieldValue.serverTimestamp(),
    lastMessagePreview: `Task aggiornato: ${persistedTask.title ?? persistedTask.type}`,
    lastMessageAt: FieldValue.serverTimestamp(),
    lastDirection: "system",
  });

  logger.info(
    { taskId: persistedTask.taskId, propertyId, hostId, reservationId: reservation.reservationId },
    "task orchestration workflow completed",
  );
}


