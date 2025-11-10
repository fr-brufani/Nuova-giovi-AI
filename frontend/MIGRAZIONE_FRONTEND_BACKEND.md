# Migrazione del frontend React verso il backend Firebase

Questo documento descrive lo stato attuale del nuovo frontend (`frontend/giovi-ai-working-app`) e del backend esistente, analizza i gap rispetto all'integrazione con Firebase e definisce un piano operativo per sostituire i dati dummy con quelli reali.

---

## 1. Stato attuale

### 1.1 Frontend React
- **Stack**: Vite + React 18 + TypeScript + Tailwind + shadcn/ui (`package.json`).
- **Struttura principale**:
  - `src/pages` contiene le view principali (`Index`, `Alloggi`, `Clienti`, `Calendario`, `AI`, `TestChatbot`, `Impostazioni`, ecc.).
  - `src/components/layout` gestisce `Dashboard`, `Sidebar`, `PageLayout`.
  - `src/data/mockData.ts` fornisce proprietà, clienti, prenotazioni e messaggi fittizi.
  - `src/hooks/useMockAuth.tsx` simula login/registrazione via `localStorage` e definisce i ruoli.
  - `src/hooks/useUserRole.tsx` re-esporta la versione mock.
  - React Query è configurato ma non ancora usato per chiamate reali.
- **Routing**: `App.tsx` utilizza `BrowserRouter`; alcune route puntano a versioni `.backup` non attive.
- **Note**: i componenti “backup” (es. `AgencyDashboard.tsx.backup`) sono copie legacy e non vengono importati.

### 1.2 Backend Firebase & servizi Node
- **Firebase Functions (`functions/src/index.ts`)**:
  - Funzione callable `getAiChatResponse` che usa Gemini e legge Firestore:
    - Autenticazione via Firebase Auth (solo utenti con ruolo `client`).
    - Recupera proprietà in `users/{hostId}/properties/{propertyId}`.
    - Usa `users` per verificare i permessi del cliente.
- **pms-sync-service (`pms-sync-service/src/server.ts`)**:
  - REST API protetta da Firebase ID Token.
  - Import CSV clienti/prenotazioni.
  - Sincronizzazione automatica con PMS esterni (Smoobu webhook, Scidoo API).
  - Scrive su Firestore:
    - Raccolta `users` (host/client) e sottocollezione `users/{hostId}/properties`.
    - Raccolta `reservations` con documenti `smoobu_*`, `scidoo_*` ecc.
- **workflow-service (`workflow-service/src/server.ts`)**:
  - Riceve azioni Pub/Sub dall’assistente AI.
  - Legge/salva compiti su `propertyTasks`.
  - Invia messaggi WhatsApp via `gemini-proxy-service`.
  - Notifica clienti aggiornando `gioviAiChatDataset` o inviando WA.
- **gemini-proxy-service (`gemini-proxy-service/lib/server.js`)**:
  - Proxy per Gemini, WhatsApp, Gmail, SendGrid, ecc.
  - Usa Firestore per cronologia conversazioni (`users/{userId}/propertyInteractions/{propertyId}/conversations`) e dataset chat globale (`gioviAiChatDataset`).
- **Schema Firestore atteso (principale)**:
  - `users/{uid}`: documenti host/client (campi: `role`, `email`, `name`, `assignedHostId`, `assignedPropertyId`, `whatsappPhoneNumber`, API key PMS, ecc.).
  - `users/{hostId}/properties/{propertyId}`: dati proprietà (nome, indirizzo, contatti, info check-in/out, etc.).
  - `reservations/{reservationId}`: prenotazioni con riferimenti a host/property/client e metadati PMS.
  - `propertyTasks/{taskId}`: ticket operativi per pulizie/tecnici.
  - `gioviAiChatDataset`: log conversazioni.
  - `hostEmailIntegrations/{docId}`: credenziali Gmail criptate (gestite dal proxy).

---

## 2. Gap front-backend

| Modulo frontend | Fonte dati attuale | Fonte dati attesa | Considerazioni |
|-----------------|--------------------|-------------------|----------------|
| Auth / ruoli (`useMockAuth`, `useUserRole`) | `localStorage` + hook mock | Firebase Auth + Firestore `users` | Serve sostituire con flusso reale (email/password, custom claims, ruoli). |
| Dashboard (`Dashboard.tsx`) | `mockProperties`, `mockBookings` | `users/{host}/properties`, `reservations` | Richiede conteggio prenotazioni attive e calcolo tasso occupazione da Firestore. |
| Lista alloggi (`Alloggi.tsx`, `PropertyCard`) | `mockProperties` | `users/{hostId}/properties` | Necessita mapping campi (nome, indirizzo, foto, stato). |
| Dettaglio alloggio (`AlloggiDetail.tsx`) | `mockProperties` | `users/{hostId}/properties/{propertyId}` + forse `reservations` e `propertyTasks` | Prevedere fetch combinato. |
| Calendario (`Calendario.tsx`) | `mockBookings`, `mockClients` | `reservations` + `users` | Richiede join tra prenotazioni e anagrafiche clienti; valutare Cloud Function aggregatrice o query multiple. |
| Clienti & chat (`Clienti.tsx`) | `mockBookings`, `mockClients`, `mockMessages` | `users` (client), `reservations`, `gioviAiChatDataset` | Necessario ordinare conversazioni e sincronizzare con AI/WhatsApp. |
| AI/Test Chatbot (`AI.tsx`, `TestChatbot.tsx`) | placeholder | Firebase callable `getAiChatResponse` + log conversazioni | Servono chiamate functions e interfaccia conversazione. |
| Impostazioni | attuale placeholder | Firestore `users/{hostId}` per configurazioni PMS e preferenze | Integrare con `pms-sync-service` endpoints. |

---

## 3. Piano di migrazione

### Fase 0 — Prerequisiti
1. Recuperare config Firebase Web (`apiKey`, `authDomain`, `projectId`, ecc.) dal progetto esistente.
2. Creare file `.env` (non committato) per Vite:
   ```
   VITE_FIREBASE_API_KEY=...
   VITE_FIREBASE_AUTH_DOMAIN=...
   VITE_FIREBASE_PROJECT_ID=...
   VITE_FIREBASE_STORAGE_BUCKET=...
   VITE_FIREBASE_APP_ID=...
   VITE_FIREBASE_MESSAGING_SENDER_ID=...
   ```
3. Installare SDK necessari nel frontend: `firebase`, `firebase-functions`, `@firebase/auth`, `@firebase/firestore`.
4. Definire regole Firestore e Auth aggiornate (vedi §4).

### Fase 1 — Integrazione Firebase di base
1. Creare `src/lib/firebase.ts` con inizializzazione app/singletone (Auth, Firestore, Functions).
2. Sostituire `useMockAuth` con hook reale che:
   - usa `onAuthStateChanged`;
   - supporta `signInWithEmailAndPassword`, `createUserWithEmailAndPassword`, `sendPasswordResetEmail`, `signOut`;
   - salva in stato il ruolo recuperato da `users/{uid}.role`.
3. Aggiornare `useUserRole` per leggere Firestore (`users/{uid}`) e gestire fallback (es. ruoli `property_manager`, `cleaning_agency`, `cleaner`).
4. Aggiornare `Auth.tsx` per usare i nuovi metodi e gestire errori Firebase specifici.

### Fase 2 — Sostituzione dati mock
**Obiettivo**: eliminare `src/data/mockData.ts` e relative importazioni.

Per ogni modulo:
1. **Proprietà** (`Alloggi.tsx`, `PropertyCard`, `Dashboard`):
   - Query Firestore: `collection('users').doc(hostId).collection('properties')`.
   - Considerare `onSnapshot` per realtime o `getDocs` + React Query per caching.
   - Mappare campi -> UI (es. `name`, `address`, `rooms`, `cleaningContact`, `photos` se presenti).
   - Gestire proprietà senza dati completi (fallback UI).
2. **Prenotazioni & Clienti** (`Clienti.tsx`, `Calendario.tsx`, `Dashboard`):
   - Ottenere prenotazioni filtrate per host: `collection('reservations').where('hostId','==',currentHostId)`.
   - Per ogni prenotazione, recuperare cliente: `doc('users', clientId)` (cache con React Query).
   - Per calendario, convertire `startDate`, `endDate` (Firestore Timestamp) in `Date`.
   - Valutare creazione di Cloud Function REST/Callable che restituisce join pronto (performance).
3. **Dettaglio alloggio** (`AlloggiDetail.tsx`):
   - Recuperare dettagli proprietà + prenotazioni future + task associati (`propertyTasks.where('propertyId','==',propertyId)`).
4. **Conversazioni** (`Clienti.tsx`, futura `Chat`):
   - Leggere cronologia da `gioviAiChatDataset` filtrando per `clientId`/`propertyId`, ordinata per `timestamp`.
   - Per conversazioni embed (propertyInteractions) usare path nested (opzionale).
5. **Statistiche Dashboard**:
   - Calcolare `totalProperties` e `activeBookings` a runtime dai dati Firestore.
   - Valutare memorizzazione di metriche aggregate nel backend (Cloud Functions) se necessario per performance.

### Fase 3 — Integrazione AI & workflow
1. **Chatbot**:
   - Usare Firebase Functions client (`getFunctions(app, region)`) e `httpsCallable('getAiChatResponse')`.
   - Passare `message`, `hostId`, `propertyId`.
   - Gestire errori (`unauthenticated`, `permission-denied`, `failed-precondition`, ecc.).
   - Dopo risposta, salvare conversazione nel log (via Cloud Function o scrittura diretta se permessa).
2. **Task operativi**:
   - Per richieste di pulizia/manutenzione, scrivere su `propertyTasks` (coerente con workflow-service) o invocare endpoint REST se previsto.
   - Monitorare aggiornamenti task per aggiornare UI (listener su `propertyTasks`).
3. **Notifiche**:
   - Se il frontend deve mostrare stati WhatsApp/Gmail, leggere campi `status`, `lastProviderResponseAt`, etc. dai documenti `propertyTasks`.

### Fase 4 — Integrazione PMS / Impostazioni
1. Collegare pagina impostazioni con API `pms-sync-service`:
   - Endpoints principali: `/config/scidoo`, `/config/scidoo/status`, `/config/scidoo/sync-properties`, `/config/scidoo/sync-now`, `/import-pms-data`.
   - Richiedono header `Authorization: Bearer <Firebase ID token>`.
   - Gestire upload CSV (utilizzare `fetch` con `Content-Type: application/json` come da backend).
2. Visualizzare stato sincronizzazioni leggendo Firestore (`users/{hostId}.scidooSyncStats` ecc.).
3. Garantire che il frontend non conservi API key in chiaro (usare Cloud Functions/Callable se necessario).

### Fase 5 — Pulizia e rifinitura
1. Rimuovere file `.backup` se non necessari.
2. Eliminare `mockData`, `useMockAuth`, `useMockUserRole`.
3. Aggiornare `README.md` con istruzioni reali (installazione, env, flussi supportati).
4. Aggiungere test end-to-end (es. Cypress/Playwright) per scenari critici: login, lista alloggi, calendario, chat AI, import CSV.

---

## 4. Sicurezza & configurazione

- **Regole Firestore**:
  - Consentire lettura/scrittura solo ad utenti autenticati.
  - Restringere `users/{uid}`: un host può leggere il proprio doc; un cliente solo i propri dati.
  - Restrizioni per `users/{hostId}/properties`: consentire al relativo host e a servizi privilegiati.
  - `reservations`: accesso in lettura agli host proprietari; scrittura solo da Cloud Functions / servizi backend.
  - `propertyTasks` e `gioviAiChatDataset`: scrittura solo da servizi; lettura limitata a host/client coinvolti.
- **CORS**:
  - Aggiungere dominio del frontend alle whitelist dei servizi (`pms-sync-service`, `workflow-service`, `gemini-proxy-service`).
- **Gestione segreti**:
  - Nessuna API key Gemini/SendGrid nel frontend; tutte gestite da Secret Manager via Cloud Run.
- **Ruoli utente**:
  - Considerare uso di [Custom Claims](https://firebase.google.com/docs/auth/admin/custom-claims) per distinguere `property_manager`, `cleaning_agency`, `cleaner`.
  - Aggiornare logica di routing (es. `Index.tsx`) per basarsi sui ruoli reali.

---

## 5. Verifica & test

1. **Smoke test**: login, logout, routing protetto.
2. **Dati real-time**: aggiungere/modificare proprietà e verificare aggiornamento UI.
3. **Calendario**: controllare corretta rappresentazione prenotazioni importate da Scidoo/Smoobu.
4. **Chat AI**: inviare messaggi come cliente e verificare risposta dall’assistente.
5. **Workflow**: simulare richiesta pulizia e verificare creazione task + notifiche.
6. **PMS import**: eseguire `/config/scidoo/test` + `/config/scidoo` dal frontend.
7. **Regressioni**: assicurarsi che non restino riferimenti a mock in bundle di produzione.

---

## 6. Prossimi passi consigliati

1. Introdurre uno strato di servizi/frontend per Firestore (es. `src/services/firestore/properties.ts`) per centralizzare query e trasformazioni.
2. Valutare l’uso di React Query con persister (IndexedDB) per ridurre round-trip.
3. Implementare gestione errori e skeleton loader coerenti in tutte le pagine.
4. Definire analytics (es. `reservations` → report) eventualmente tramite Cloud Functions programmate.
5. Pianificare test di integrazione con ambienti di staging (Firebase project separato).

---

### Sintesi operativa
1. Configurare Firebase SDK nel frontend e sostituire l’autenticazione mock.
2. Reimplementare fetch dati (`properties`, `reservations`, `users`) con Firestore/Functions.
3. Integrare le feature AI e workflow chiamando i servizi esistenti.
4. Aggiornare impostazioni/pagine gestionali per parlare con `pms-sync-service`.
5. Eliminare dati dummy, aggiornare documentazione e completare QA.


