## Firestore v2 – Linee Guida per la Codebase

### 1. Schema di riferimento
- `hosts/{hostId}`
  - campi: `displayName`, `email`, `createdAt`, `status`, `schemaVersion`
  - subcollections consigliate: `integrations/{integrationId}`
- `properties/{propertyId}`
  - campi: `hostId`, `name`, `address`, `contacts[]`, `timezone`, `schemaVersion`
  - subcollections:
    - `tasks/{taskId}` → `status`, `type`, `details`, `providerPhone`, `timestamps`, `schemaVersion`
      - `events/{eventId}` per history (facoltativo ma consigliato)
    - `clients/{clientId}` (ghost reference per conversazioni)
    - `conversations/{conversationId}/messages/{messageId}`
- `clients/{clientId}`
  - campi principali: `displayName`, `email`, `whatsappPhone`, `primaryHostId`, `primaryPropertyId`, `activeReservationId`, `schemaVersion`
  - subcollections opzionali: `contacts`, `preferences`
- `reservations/{reservationId}`
  - campi: `hostId`, `propertyId`, `clientId`, `source`, `status`, `startDate`, `endDate`, `checkinTime`, `checkoutTime`, `guests`, `schemaVersion`
  - campo `rawPayloadRef` verso `reservationRawPayloads/{source}/{reservationId}`
- `integrations/email/{emailId}`
  - campi: `hostId`, `provider`, `status`, `scopes`, `encryptedAccessToken`, `encryptedRefreshToken`, `tokenExpiry`, `schemaVersion`
  - subcollection `locks/{messageId}` per idempotenza Gmail

### 2. Servizi Backend

#### 2.1 `gemini-proxy-service`
1. **Risoluzione property e host**
   - `getPropertyData`: leggere da `firestore.collection('properties').doc(propertyId)` e validare `hostId`. Aggiungere check che `doc.data()?.hostId === hostId`; in caso contrario loggare `FORBIDDEN_PROPERTY_ACCESS`.
   - Aggiungere helper `getHostById` se servono dati host (per email/system).
2. **Lookup client**
   - `findClientByEmail`/`findClientByBookingEmail`: puntare a `firestore.collection('clients')`. Aggiornare query per usare indici su `email`/`bookingEmail`.
   - Aggiornare `handleChatMessageWithGemini` per usare `clients/{clientId}` al posto di `users`.
3. **Conversazioni**
   - `getConversationHistory`: `{propertyId}/conversations/{clientId}/messages` ordinato per `createdAt`.
     ```ts
     const messagesRef = firestore
       .collection('properties')
       .doc(propertyId)
       .collection('conversations')
       .doc(clientId)
       .collection('messages')
       .orderBy('createdAt', 'desc')
       .limit(limit);
     ```
   - `saveChatInteraction`: scrivere sia il messaggio utente sia la risposta AI come due documenti `messages` con `direction: 'incoming' | 'outgoing'`, `channel`, `payload`, `schemaVersion`. Creare/aggiornare documento conversazione con metadati (ultimo messaggio, stato).
4. **Tasks Pub/Sub**
   - Pubblica `toolCallToPublish.context` con `taskPath: properties/${propertyId}/tasks/{taskId}`.
   - Quando salvi risposte provider (webhook WhatsApp/email), usa `properties/{propertyId}/tasks/{taskId}/events`.
5. **Email & Gmail integration**
   - Spostare scrittura config in `firestore.collection('integrations').doc('email').collection('accounts').doc(email)` **oppure** `integrations/email/{email}` se preferisci struttura piatta.
   - Aggiornare `processedMessageIds` annidati in `locks`.
6. **Property dataset caching**
   - Dopo refactor, `propertyData` è top-level: considera caching in memoria (`Map<propertyId, PropertyDoc>`) per ridurre round trip nelle conversazioni.

#### 2.2 `workflow-service`
1. **Costanti Firestore**
   ```ts
   const HOSTS_COLLECTION = 'hosts';
   const PROPERTIES_COLLECTION = 'properties';
   const CLIENTS_COLLECTION = 'clients';
   const RESERVATIONS_COLLECTION = 'reservations';
   ```
2. **Proprietà**
   - `getPropertyDetails`: `firestore.collection(PROPERTIES_COLLECTION).doc(propertyId)` e verificare `hostId`.
3. **Client**
   - `getClientDetails`: `firestore.collection(CLIENTS_COLLECTION).doc(clientId)`.
   - Aggiornare `whatsappPhoneNumber` → `whatsappPhone`.
4. **Tasks**
   - `saveTask`: creare doc `firestore.collection('properties').doc(propertyId).collection('tasks').doc()`.
   - `updateTaskStatus` & `appendTaskEvent`: passare `propertyId` insieme a `taskId` (arriva già dal payload tool call). Aggiornare reference in post-processing provider (`providerResponsePayload`).
   - `broadcastTaskToProvider`: leggere `providerPhone` dal campo top-level del task, non da JSON annidato.
5. **Conversazioni e chat log**
   - Tutti i riferimenti a `gioviAiChatDataset` da rimuovere. Se serve logging, usare `properties/{propertyId}/conversations/{clientId}/messages`.
6. **Prenotazioni**
   - `getReservationDetails`: query su `reservations` filtrando `propertyId`/`clientId`.
   - Indici da creare: `(propertyId asc, endDate desc)` e `(propertyId asc, startDate asc)`.

#### 2.3 `pms-sync-service`
1. **Import clienti**
   - Scrivere/aggiornare `clients/{clientId}`
     ```ts
     const clientRef = firestore.collection('clients').doc(existingIdOrNew);
     batch.set(clientRef, {
       email,
       displayName,
       whatsappPhone,
       primaryHostId: hostId,
       updatedAt: FieldValue.serverTimestamp(),
       schemaVersion: 2
     }, { merge: true });
     ```
   - Aggiornare `hosts/{hostId}` con contatori se necessario (es. `stats.totalClients`).
2. **Import proprietà**
   - Persistenza diretta in `properties/{propertyId}` con `hostId`.
   - Se l’host non ha ancora la property, crea doc con `schemaVersion: 2`.
3. **Import prenotazioni**
   - Creare `reservations/{reservationId}` (nuovo ID -> `source: 'csv_scidoo'`).
   - Salvare payload originale in `reservationRawPayloads/csv/{reservationId}`.
   - Aggiornare `clients/{clientId}` (`activeReservationId`, `lastStayAt`), `properties/{propertyId}` (`nextCheckin`, `nextCheckout`).
4. **Batch strategy**
   - Preferisci `bulkWriter` invece di `batch` dove possibile (per import grandi).

### 3. Frontend (`giovi-ai-working-app`)

#### 3.1 Librerie di servizio
Aggiorna `src/services/firestore`:
- `chat.ts`
  - Nuovo path: `collection(db, 'properties', propertyId, 'conversations', clientId, 'messages')`.
  - Mappa `direction` → `sender`.
  - Query: `orderBy('createdAt', 'asc')`.
- `clients.ts`
  - Source: `collection(db, 'clients')`.
  - Aggiorna campi mappati (`primaryHostId`, `primaryPropertyId`, `whatsappPhone`).
- `properties.ts`
  - `fetchHostProperties`: query `collection(db, 'properties')`, `where('hostId', '==', hostId)`.
  - `fetchPropertyById`: `doc(db, 'properties', propertyId)`.
- `reservations.ts`
  - Query su `collection(db, 'reservations')` filtrata per `hostId` e `propertyId`.
  - Aggiungi `orderBy('startDate')` e map `source`, `status`, `checkinTime`.
- Aggiorna `services/firestore/types.ts` con i nuovi campi.

#### 3.2 Hooks/Provider
- `useUserRole` / `AuthProvider`: se il ruolo host/client non sta più su `users`, eseguire una fetch verso `hosts` o `clients` in base al token `customClaims`.
- Dove il frontend assume `users/{uid}/properties`, sostituire con `properties` top-level filtrate per host.

#### 3.3 Pagine critiche
- `pages/Alloggi.tsx` / `AlloggiDetail.tsx`
  - Dipendono da `useHostProperties` & `usePropertyById` → già aggiornate dai service.
  - Se mostrano contatti pulizie, assicurati che i nuovi campi coincidano.
- `pages/Clienti.tsx`
  - Mostrare `primaryPropertyId`, `whatsappPhone`.
  - Per ottenere property name: join contro `properties`.
- `pages/Calendario.tsx`
  - Consuma `useReservationsByProperty`; aggiunge logica per distinguere `source`.
- `pages/TestChatbot.tsx` / `components/chat`
  - Caricamento conversazioni, invio messaggi: aggiornare path e payload.

### 4. Migrazione e verifiche
1. **Pulizia test (se richiesto)**
   - Cancellare collezioni legacy (`gioviAiChatDataset`, `users`, `propertyTasks`, `hostEmailAuthorizations`, ecc.).
2. **Deploy codice aggiornato**
   - Implementare le modifiche backend + frontend.
   - Aggiornare `firestore.rules`:
     - Ruoli host → accesso a `properties` dove `resource.data.hostId == request.auth.uid`.
     - Client → lettura conversazioni `properties/{propertyId}/conversations/{clientId}` se `clientId == request.auth.uid`.
3. **Indici**
   - Creare indici compositi:
     - `reservations`: `(hostId asc, propertyId asc, startDate desc)`
     - `properties`: `(hostId asc, status asc)`
     - `properties/{propertyId}/tasks`: `(status asc, providerPhone asc)`
     - `properties/{propertyId}/conversations/{clientId}/messages`: `(createdAt asc)`
4. **Test**
   - Unit test per parser email/WhatsApp con nuovi path Firestore.
   - Test E2E: import CSV, generazione task, conversazione AI.

### 5. Next Steps
- Aggiornare diagramma architettura (file `TECHNICAL_ARCHITECTURE_ANALYSIS.md`).
- Condividere il nuovo schema con il team (link in Confluence / Notion).
- Pianificare retrocompatibilità (se servono script per ambienti staging/produzione).

---

**Nota**: dopo l’eliminazione delle collezioni esistenti, ricordarsi di eseguire un `seed` minimo (1 host, 1 property, 1 client) prima di testare UI e webhook.

