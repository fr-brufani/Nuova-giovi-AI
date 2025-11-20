import { PubSub } from "@google-cloud/pubsub";

import { loadEnvironment } from "@config/env";

export class PubSubAdapter {
  private readonly pubsub: PubSub;

  constructor() {
    const env = loadEnvironment();
    this.pubsub = new PubSub({ projectId: env.GOOGLE_CLOUD_PROJECT });
  }

  async publish(topic: string, message: Record<string, unknown>) {
    const dataBuffer = Buffer.from(JSON.stringify(message));
    await this.pubsub.topic(topic).publishMessage({ data: dataBuffer });
  }
}

let pubSubAdapterInstance: PubSubAdapter | null = null;

export function getPubSubAdapter() {
  if (!pubSubAdapterInstance) {
    pubSubAdapterInstance = new PubSubAdapter();
  }
  return pubSubAdapterInstance;
}


