# Guida Test Gmail Watch

## Prerequisiti

1. ✅ Gmail collegata (OAuth completato)
2. ✅ Email importate (opzionale, ma consigliato)
3. ✅ Frontend configurato con URL produzione

---

## Test 1: Attivazione Gmail Watch dal Frontend

### Passi:

1. **Apri il frontend** → Impostazioni → Gmail Integration

2. **Verifica che l'integrazione sia attiva:**
   - Dovresti vedere l'email collegata
   - Status: "Connesso" o "Attivo"

3. **Clicca "Attiva notifiche email"**
   - Il bottone è nella sezione Gmail Integration
   - Dovresti vedere un toast di successo con la data di scadenza

4. **Verifica nel frontend:**
   - Dovresti vedere: "Watch attivo fino al [data]"
   - La data dovrebbe essere ~7 giorni nel futuro

---

## Test 2: Verifica Backend (Firestore)

### Controlla che il watch sia salvato in Firestore:

```bash
# Verifica integrazione Gmail
gcloud firestore documents get \
  projects/giovi-ai/databases/(default)/documents/hostEmailIntegrations/[EMAIL] \
  --project giovi-ai

# Cerca il campo watchSubscription:
# - historyId: dovrebbe essere presente
# - expiration: timestamp in millisecondi (~7 giorni nel futuro)
```

### Oppure via Console Firebase:
1. Vai su Firebase Console → Firestore
2. Apri collezione `hostEmailIntegrations`
3. Trova il documento con la tua email
4. Verifica campo `watchSubscription`:
   ```json
   {
     "historyId": "123456",
     "expiration": 1234567890000,
     "lastTriggered": null
   }
   ```

---

## Test 3: Verifica Log Cloud Run

### Controlla i log del servizio:

```bash
# Log in tempo reale
gcloud run services logs read email-agent-service \
  --region europe-west1 \
  --project giovi-ai \
  --limit 50 \
  --follow

# Cerca questi log:
# - "Gmail Watch attivato con successo"
# - "Watch subscription salvata"
```

---

## Test 4: Test Notifica Reale

### Per testare che le notifiche arrivino:

1. **Invia un'email test** alla casella Gmail collegata:
   - Da Booking: messaggio guest da `@guest.booking.com`
   - Da Airbnb: messaggio guest da `express@airbnb.com`
   - Da Scidoo: conferma prenotazione da `reservation@scidoo.com`

2. **Verifica log Cloud Run** (entro 1-2 minuti):
   ```bash
   gcloud run services logs read email-agent-service \
     --region europe-west1 \
     --project giovi-ai \
     --limit 100 \
     --follow
   ```

3. **Cerca questi log:**
   - `[WATCH] 📧 Nuova email ricevuta: [messageId]`
   - `[WATCH] ✅ Email processata e salvata`
   - `[WATCH] 📧 Messaggio guest pronto per AI reply` (se è un messaggio guest)
   - `[WATCH] ✅ Risposta AI generata` (se auto-reply attivo)

---

## Test 5: Verifica Pub/Sub

### Controlla che Pub/Sub riceva le notifiche:

```bash
# Verifica subscription
gcloud pubsub subscriptions describe gmail-notifications-subscription \
  --project giovi-ai

# Verifica messaggi in coda (dovrebbe essere 0 se tutto processato)
gcloud pubsub subscriptions pull gmail-notifications-subscription \
  --project giovi-ai \
  --limit 5
```

---

## Troubleshooting

### Watch non si attiva:

1. **Verifica topic Pub/Sub:**
   ```bash
   gcloud pubsub topics describe gmail-notifications-giovi-ai --project giovi-ai
   ```

2. **Verifica permessi OAuth:**
   - L'integrazione deve avere scope `https://www.googleapis.com/auth/gmail.modify`

3. **Verifica errori nel frontend:**
   - Apri DevTools (F12) → Console
   - Cerca errori nella chiamata `/watch`

### Notifiche non arrivano:

1. **Verifica che il watch sia ancora attivo:**
   - Controlla `expiration` in Firestore
   - Se scaduto, riattiva con il bottone

2. **Verifica subscription Pub/Sub:**
   ```bash
   gcloud pubsub subscriptions describe gmail-notifications-subscription \
     --project giovi-ai \
     --format="value(pushConfig.pushEndpoint)"
   ```
   - Deve puntare a: `https://email-agent-service-228376111127.europe-west1.run.app/integrations/gmail/notifications`

3. **Verifica che l'email sia rilevante:**
   - Solo email da `reservation@scidoo.com` (se `pmsProvider=scidoo`)
   - Solo email da `@guest.booking.com` o `express@airbnb.com` (messaggi guest)
   - Altre email vengono ignorate

---

## Comandi Utili

### Verifica stato integrazione:
```bash
curl -X GET "https://email-agent-service-228376111127.europe-west1.run.app/integrations/gmail/[EMAIL]" \
  -H "Content-Type: application/json"
```

### Attiva watch manualmente (se frontend non funziona):
```bash
curl -X POST "https://email-agent-service-228376111127.europe-west1.run.app/integrations/gmail/[EMAIL]/watch" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Verifica health del servizio:
```bash
curl "https://email-agent-service-228376111127.europe-west1.run.app/health/live"
```

---

## Checklist Test Completo

- [ ] Gmail collegata via OAuth
- [ ] Bottone "Attiva notifiche email" cliccato
- [ ] Toast di successo ricevuto
- [ ] Watch subscription salvata in Firestore
- [ ] `expiration` è ~7 giorni nel futuro
- [ ] Inviata email test rilevante
- [ ] Log Cloud Run mostrano processamento
- [ ] Email salvata in Firestore (properties/reservations/clients)
- [ ] Se messaggio guest: AI reply generata e inviata (se auto-reply attivo)

---

## Note Importanti

1. **Gmail Watch scade dopo 7 giorni** → Serve rinnovo automatico (Cloud Scheduler) o manuale
2. **Solo email rilevanti vengono processate** → Filtro basato su `pmsProvider` e tipo email
3. **Notifiche arrivano con delay** → Può richiedere 1-2 minuti dopo l'invio email
4. **Test in produzione** → Usa email reali per test completi

