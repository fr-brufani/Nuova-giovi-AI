import axios from "axios";

import { loadEnvironment } from "@config/env";
import type { PmsReservationPayload } from "@workflows/pmsImport";

type FetchReservationsParams = {
  hostId: string;
  apiKey: string;
  since?: string;
  until?: string;
};

export class ScidooAdapter {
  private readonly baseUrl: string;

  constructor() {
    const env = loadEnvironment();
    if (!env.SCIDOO_API_BASE_URL) {
      throw new Error("SCIDOO_API_BASE_URL missing");
    }
    this.baseUrl = env.SCIDOO_API_BASE_URL;
  }

  async fetchReservations(params: FetchReservationsParams): Promise<PmsReservationPayload[]> {
    const response = await axios.get<PmsReservationPayload[]>(`${this.baseUrl}/reservations`, {
      params: {
        hostId: params.hostId,
        since: params.since,
        until: params.until,
      },
      headers: {
        Authorization: `Bearer ${params.apiKey}`,
      },
    });
    return response.data ?? [];
  }
}

let scidooAdapterInstance: ScidooAdapter | null = null;

export function getScidooAdapter() {
  if (!scidooAdapterInstance) {
    scidooAdapterInstance = new ScidooAdapter();
  }
  return scidooAdapterInstance;
}


