#!/bin/bash
# Script per deploy email-agent-service su Google Cloud Run

set -e

PROJECT_ID="giovi-ai"
SERVICE_NAME="email-agent-service"
REGION="europe-west1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploy di ${SERVICE_NAME} su Cloud Run..."

# 1. Build e push immagine Docker
echo "📦 Building Docker image..."
gcloud builds submit --tag ${IMAGE_NAME} --project ${PROJECT_ID}

# 2. Deploy su Cloud Run
echo "☁️  Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars "APP_ENV=production,FIREBASE_PROJECT_ID=${PROJECT_ID},GMAIL_PUBSUB_TOPIC=projects/${PROJECT_ID}/topics/gmail-notifications-giovi-ai" \
  --set-secrets "TOKEN_ENCRYPTION_KEY=host-token-encryption-key:latest" \
  --set-secrets "GOOGLE_OAUTH_CLIENT_ID=google-oauth-client-id:latest" \
  --set-secrets "GOOGLE_OAUTH_CLIENT_SECRET=google-oauth-client-secret:latest" \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest"

echo "✅ Deploy completato!"
echo ""
echo "📋 Prossimi passi:"
echo "1. Verifica che il servizio sia attivo: gcloud run services describe ${SERVICE_NAME} --region ${REGION}"
echo "2. Ottieni l'URL del servizio: gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'"
echo "3. Configura Pub/Sub subscription con l'URL del servizio"
echo "4. Testa l'endpoint: curl \$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')/health/live"

