import type { Firestore } from "@config/firebase";
import { FirestoreRepository } from "@repositories/base";
import { propertyTaskConverter, propertyTaskEventConverter } from "@repositories/converters";
import type { PropertyTask, PropertyTaskEvent } from "@types/domain";

const PROPERTIES_COLLECTION = "properties";

export class PropertyTasksRepository extends FirestoreRepository {
  constructor(db: Firestore) {
    super(db);
  }

  private tasksCollection(propertyId: string) {
    return super.collection<PropertyTask>(`${PROPERTIES_COLLECTION}/${propertyId}/tasks`, propertyTaskConverter);
  }

  private taskDoc(propertyId: string, taskId: string) {
    return this.tasksCollection(propertyId).doc(taskId);
  }

  private taskEventsCollection(propertyId: string, taskId: string) {
    return super.collection<PropertyTaskEvent>(
      `${PROPERTIES_COLLECTION}/${propertyId}/tasks/${taskId}/events`,
      propertyTaskEventConverter,
    );
  }

  async upsertTask(propertyId: string, task: PropertyTask) {
    await this.taskDoc(propertyId, task.taskId).set(
      {
        ...task,
        propertyId,
        taskId: task.taskId,
      },
      { merge: true },
    );
  }

  async getTask(propertyId: string, taskId: string) {
    const snapshot = await this.taskDoc(propertyId, taskId).get();
    if (!snapshot.exists) return null;
    return snapshot.data();
  }

  async updateTask(propertyId: string, taskId: string, updater: (task: PropertyTask | null) => PropertyTask) {
    const docRef = this.taskDoc(propertyId, taskId);
    const snapshot = await docRef.get();
    const currentTask = snapshot.exists ? snapshot.data() ?? null : null;
    const nextTask = updater(currentTask);
    await docRef.set(
      {
        ...nextTask,
        propertyId,
        taskId,
      },
      { merge: false },
    );
    return nextTask;
  }

  async appendTaskEvent(propertyId: string, taskId: string, event: PropertyTaskEvent) {
    await this.taskEventsCollection(propertyId, taskId)
      .doc(event.eventId)
      .set({
        ...event,
        taskId,
        propertyId,
      });
  }
}

export function getTasksRepository(db: Firestore) {
  return new PropertyTasksRepository(db);
}


