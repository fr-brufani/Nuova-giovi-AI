# 🚀 Istruzioni Deploy Email Agent Service

## Prerequisiti

1. **Google Cloud SDK installato** ✅ (già installato)
2. **Progetto GCP configurato**: `giovi-ai` ✅
3. **API abilitate**:
   - Cloud Run API
   - Cloud Build API
   - Pub/Sub API
   - Secret Manager API

## Step 1: Verifica API abilitate

```bash
gcloud services enable run.googleapis.com \
  cloudbuild.googleapis.com \
  pubsub.googleapis.com \
  secretmanager.googleapis.com \
  --project giovi-ai
```

## Step 2: Verifica Secrets in Secret Manager

I seguenti secrets devono esistere in Secret Manager (verifica che esistano):

```bash
# Verifica secrets esistenti
gcloud secrets list --project giovi-ai --format="table(name)"

# Secrets necessari per email-agent-service:
# ✅ host-token-encryption-key (esiste già)
# ✅ google-oauth-client-id (esiste già)
# ✅ google-oauth-client-secret (esiste già)
# ✅ gemini-api-key (esiste già)
```

**Nota**: Firebase userà Application Default Credentials di Cloud Run (non serve secret separato).

Se qualche secret manca, crealo con:
```bash
# Esempio: se manca gemini-api-key
echo -n "AIzaSyCs7a8J9jwzHl4vo8gnQ2ds1WP7DOP81E0" | gcloud secrets create gemini-api-key \
  --data-file=- --project giovi-ai
```

## Step 3: Deploy su Cloud Run

### Opzione A: Usa lo script automatico

```bash
cd giovi-ai/email-agent-service
./deploy.sh
```

### Opzione B: Deploy manuale

```bash
cd giovi-ai/email-agent-service

# 1. Build e push immagine
gcloud builds submit --tag gcr.io/giovi-ai/email-agent-service --project giovi-ai

# 2. Deploy
gcloud run deploy email-agent-service \
  --image gcr.io/giovi-ai/email-agent-service \
  --platform managed \
  --region europe-west1 \
  --project giovi-ai \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars "APP_ENV=production,FIREBASE_PROJECT_ID=giovi-ai,GMAIL_PUBSUB_TOPIC=projects/giovi-ai/topics/gmail-notifications-giovi-ai" \
  --set-secrets "TOKEN_ENCRYPTION_KEY=host-token-encryption-key:latest" \
  --set-secrets "GOOGLE_OAUTH_CLIENT_ID=google-oauth-client-id:latest" \
  --set-secrets "GOOGLE_OAUTH_CLIENT_SECRET=google-oauth-client-secret:latest" \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest"
```

## Step 4: Ottieni URL del servizio

```bash
SERVICE_URL=$(gcloud run services describe email-agent-service \
  --region europe-west1 \
  --project giovi-ai \
  --format 'value(status.url)')

echo "🌐 Service URL: $SERVICE_URL"
```

## Step 5: Configura Pub/Sub Subscription

Dopo il deploy, configura la subscription Pub/Sub per ricevere notifiche Gmail:

```bash
# Crea subscription (se non esiste)
gcloud pubsub subscriptions create gmail-notifications-subscription \
  --topic=gmail-notifications-giovi-ai \
  --push-endpoint="${SERVICE_URL}/integrations/gmail/notifications" \
  --project giovi-ai \
  --ack-deadline=60
```

**⚠️ IMPORTANTE**: Sostituisci `${SERVICE_URL}` con l'URL reale ottenuto nello Step 4.

## Step 6: Verifica deploy

```bash
# Health check
curl "${SERVICE_URL}/health/live"

# Dovrebbe restituire: {"status":"ok"}
```

## Step 7: Test con utenti reali

1. **Collega Gmail** tramite frontend:
   - Vai su Impostazioni → Gmail Integration
   - Seleziona PMS Provider
   - Clicca "Collega Gmail"

2. **Attiva Gmail Watch**:
   ```bash
   curl -X POST "${SERVICE_URL}/integrations/gmail/TUA-EMAIL/watch" \
     -H "Content-Type: application/json" \
     -d '{}'
   ```

3. **Invia un messaggio test**:
   - Invia un messaggio guest (Booking/Airbnb) alla casella email collegata
   - Verifica nei log Cloud Run che il flusso funzioni:
     ```bash
     gcloud run services logs read email-agent-service \
       --region europe-west1 \
       --project giovi-ai \
       --limit 50
     ```

## Troubleshooting

### Errore: "Secret not found"
- Verifica che i secrets esistano: `gcloud secrets list --project giovi-ai`
- Verifica i nomi dei secrets nello script di deploy

### Errore: "Permission denied"
- Verifica che il service account di Cloud Run abbia i permessi per Secret Manager:
  ```bash
  # Ottieni il service account di Cloud Run
  PROJECT_NUMBER=$(gcloud projects describe giovi-ai --format="value(projectNumber)")
  
  # Aggiungi permessi Secret Manager
  gcloud projects add-iam-policy-binding giovi-ai \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
  
  # Aggiungi permessi Firestore (per Application Default Credentials)
  gcloud projects add-iam-policy-binding giovi-ai \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/datastore.user"
  ```

### Errore: "Port already in use"
- Cloud Run imposta automaticamente PORT, non serve configurarlo manualmente

### Log non visibili
- Verifica che Cloud Logging API sia abilitata
- Controlla i log in Cloud Console: https://console.cloud.google.com/run

## Aggiornamento dopo modifiche

Per aggiornare il servizio dopo modifiche al codice:

```bash
cd giovi-ai/email-agent-service
./deploy.sh
```

Oppure manualmente:

```bash
gcloud builds submit --tag gcr.io/giovi-ai/email-agent-service --project giovi-ai
gcloud run deploy email-agent-service \
  --image gcr.io/giovi-ai/email-agent-service \
  --region europe-west1 \
  --project giovi-ai
```

