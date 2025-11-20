import { Counter, Histogram, Registry, collectDefaultMetrics } from "prom-client";

export const metricsRegistry = new Registry();

collectDefaultMetrics({ register: metricsRegistry });

export const httpRequestDurationHistogram = new Histogram({
  name: "core_service_http_request_duration_seconds",
  help: "Duration of HTTP requests in seconds",
  labelNames: ["method", "route", "status_code"],
  buckets: [0.01, 0.05, 0.1, 0.3, 0.5, 1, 2, 5, 10],
  registers: [metricsRegistry],
});

export const ingestCounter = new Counter({
  name: "core_service_ingest_total",
  help: "Total number of ingest operations processed",
  labelNames: ["type"],
  registers: [metricsRegistry],
});


