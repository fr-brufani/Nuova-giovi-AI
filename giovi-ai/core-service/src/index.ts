import express from "express";
import helmet from "helmet";
import cors from "cors";
import rateLimit from "express-rate-limit";

import { registerHttpRoutes } from "@transport/http";
import { loadEnvironment } from "@config/env";
import { logger } from "@utils/logger";
import "@parsers/bootstrap";

async function bootstrap() {
  const env = loadEnvironment();
  const app = express();

  app.set("trust proxy", 1);

  app.use(helmet());
  app.use(
    cors({
      origin: env.CORS_ORIGIN ?? true,
      credentials: true,
    }),
  );
  app.use(
    rateLimit({
      windowMs: 15 * 60 * 1000,
      max: Number(env.RATE_LIMIT_MAX ?? 500),
      standardHeaders: true,
      legacyHeaders: false,
    }),
  );
  app.use(express.text({ type: ["text/csv", "application/csv"] }));
  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));
  registerHttpRoutes(app);

  const port = env.PORT ?? 8080;
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  app.use((err: unknown, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
    logger.error({ err }, "unhandled error");
    res.status(500).send({ error: "internal_error" });
  });

  app.listen(port, () => logger.info({ port }, "core-service listening"));
}

bootstrap().catch((error) => {
  logger.fatal({ err: error }, "unable to start core-service");
  process.exit(1);
});

