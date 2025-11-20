## Local Development Setup

Follow these steps when you want to run both the core-service and the frontend locally for faster testing.

### 1. Prepare environment variables

Create a copy of the sample env files and fill in the values you already use in production (they will stay only on your machine):

```bash
cp core-service/env.local.example core-service/.env.local
cp giovi/frontend/giovi-ai-working-app/env.local.example giovi/frontend/giovi-ai-working-app/.env.local
```

Recommended values:

- keep the same Firebase/GCP credentials you already have
- for local OAuth add the redirect URI `http://localhost:8080/integrations/gmail/oauth/callback`
- for the frontend set `VITE_CORE_SERVICE_URL=http://localhost:8080`

> ⚠️ After editing the OAuth client in Google Cloud remember to add both redirect URIs:
> - `https://core-service-228376111127.europe-west1.run.app/integrations/gmail/oauth/callback` (production)
> - `http://localhost:8080/integrations/gmail/oauth/callback` (local dev)

### 2. Run the core-service locally

```bash
cd core-service
npm install
npm run dev
```

The service listens on `http://localhost:8080` and prints logs directly to the terminal.

### 3. Run the frontend locally

```bash
cd giovi/frontend/giovi-ai-working-app
npm install
npm run dev
```

Vite exposes the UI at `http://localhost:5173` and uses the core-service URL defined in `.env.local`.

### 4. Test the flows

- Import Scidoo via API
- Import/backfill Gmail (after OAuth the browser should redirect to `http://localhost:5173/impostazioni`)
- Reset host data

All logs are available immediately in the two terminals. Once everything works you can build & deploy:

```bash
# frontend
npm run build
firebase deploy --only hosting --project giovi-ai

# backend
cd core-service
npm run test
npm run deploy    # wrapper around gcloud run deploy …
```


