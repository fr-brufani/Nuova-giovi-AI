# Struttura Firestore Attuale

Esportata il: 2025-11-14

## Collections Root

### 1. `properties/` (Collection Root)
**Path**: `properties/{propertyId}`

**Campi principali**:
- `name` (string) - Nome della property
- `hostId` (string) - ID dell'host proprietario
- `address` (string) - Indirizzo
- `city` (string) - Città
- `country` (string) - Paese
- `bedrooms` (number) - Numero camere
- `bathrooms` (number) - Numero bagni
- `capacity` (number) - Capacità ospiti
- `checkInTime` (string) - Orario check-in
- `checkOutTime` (string) - Orario check-out
- `allowEarlyCheckin` (boolean)
- `allowLateCheckout` (boolean)
- `accessCode` (string) - Codice accesso
- `accessInstructions` (string) - Istruzioni accesso
- `cleaningContactName` (string)
- `cleaningContactPhone` (string)
- `instructions` (string)
- `areaServices` (string)
- `luggageDropOffInstructions` (string)
- `interiorNotes` (string)
- `timezone` (string)
- `status` (string)
- `schemaVersion` (string)
- `createdAt` (Timestamp)
- `updatedAt` (Timestamp)
- `lastUpdatedAt` (Timestamp)

**Query tipica**: `properties.where("hostId", "==", hostId)`

---

### 2. `reservations/` (Collection Root)
**Path**: `reservations/{reservationId}`

**Campi principali** (dalla struttura esistente):
- `hostId` (string) - ID host
- `propertyId` (string) - ID property
- `propertyName` (string) - Nome property (denormalizzato)
- `clientId` (string) - ID cliente
- `clientName` (string) - Nome cliente (denormalizzato)
- `startDate` (Timestamp) - Data check-in
- `endDate` (Timestamp) - Data check-out
- `status` (string) - Stato prenotazione (es: "confirmed")
- `totalPrice` (number) - Prezzo totale
- `adults` (number) - Numero adulti
- `children` (number) - Numero bambini (opzionale)
- `numeroConfermaBooking` (string) - Numero conferma Booking
- `importedFrom` (string) - Fonte import (es: "scidoo_email", "smoobu")
- `createdAt` (Timestamp)
- `lastUpdatedAt` (Timestamp)

**Query tipica**: `reservations.where("hostId", "==", hostId)`

---

### 3. `clients/` (Collection Root)
**Path**: `clients/{clientId}`

**Campi principali**:
- `name` (string) - Nome cliente
- `email` (string) - Email (lowercase)
- `whatsappPhoneNumber` (string) - Telefono WhatsApp
- `role` (string) - Sempre "guest"
- `assignedHostId` (string) - ID host assegnato
- `assignedPropertyId` (string) - ID property associata (ultima prenotazione)
- `reservationId` (string) - ID prenotazione associata (ultima prenotazione)
- `importedFrom` (string) - Fonte import
- `createdAt` (Timestamp)
- `lastUpdatedAt` (Timestamp)

**Note**: 
- `assignedPropertyId` e `reservationId` vengono aggiornati ogni volta che si salva una nuova prenotazione per questo cliente
- Utili per i passaggi successivi (es. invio email automatiche, notifiche)

**Query tipica**: `clients.where("email", "==", email).where("assignedHostId", "==", hostId)`

---

### 4. `hosts/` (Collection Root)
**Path**: `hosts/{hostId}`

**Campi principali**:
- `hostId` (string)
- `email` (string)
- `displayName` (string)
- `role` (string) - "host"
- `schemaVersion` (string)
- `createdAt` (Timestamp)
- `lastLoginAt` (Timestamp)
- `behaviorInstructions` (string) - Opzionale
- `systemPrompt` (string) - Opzionale
- `updatedAt` (Timestamp)

---

### 5. `hostEmailIntegrations/` (Collection Root)
**Path**: `hostEmailIntegrations/{email}`

**Campi principali**:
- `emailAddress` (string) - Email Gmail integrata
- `hostId` (string) - ID host
- `provider` (string) - "gmail"
- `pmsProvider` (string) - "scidoo", "booking", "airbnb", "other"
- `status` (string) - "connected", "disconnected"
- `encryptedAccessToken` (string)
- `encryptedRefreshToken` (string)
- `tokenExpiryDate` (Timestamp)
- `scopes` (array) - Scopes OAuth
- `createdAt` (Timestamp)
- `updatedAt` (Timestamp)

**Subcollections**:
- `hostEmailIntegrations/{email}/processedMessageIds/{messageId}` - Traccia email già processate

---

### 6. `hostEmailAuthorizations/` (Collection Root)
**Path**: `hostEmailAuthorizations/{authId}`

**Campi principali**:
- `hostEmailAddress` (string)
- `hostId` (string)
- `emailProvider` (string)
- `status` (string)
- `refreshToken` (string)
- `scopesGranted` (array)
- `googleHistoryId` (string)
- `googleWatchSubscriptionId` (string)
- `googleWatchSubscriptionExpiry` (Timestamp)
- `isEnabled` (boolean)
- `createdAt` (Timestamp)
- `updatedAt` (Timestamp)

---

### 7. `gioviAiChatDataset/` (Collection Root)
**Path**: `gioviAiChatDataset/{datasetId}`

**Campi principali**:
- `userId` (string)
- `propertyId` (string)
- `hostId` (string)
- `userMessage` (string)
- `aiResponse` (string)
- `channel` (string)
- `timestamp` (Timestamp)
- `promptSent` (string)
- `toolCallPublished` (boolean)
- `wasBlocked` (boolean)
- `blockReason` (string)
- `processingError` (string)

---

### 8. `cleaningAgencies/` (Collection Root)
**Path**: `cleaningAgencies/{agencyId}`

**Campi principali**:
- `agencyId` (string) - coincide con l'UID Firebase del proprietario dell'account agenzia
- `hostId` (string | null) - property manager che ha collegato l'agenzia
- `displayName` (string)
- `email` (string)
- `phone` (string)
- `baseLocation` (map: `{ address, city, country, lat, lng }`)
- `skillsOffered` (array<string>)
- `defaultShiftStart` / `defaultShiftEnd` (string HH:mm)
- `schemaVersion` (number, default 1)
- `createdAt` / `updatedAt` (Timestamp)

**Subcollections**:
- `invitations/{invitationId}` - inviti o link di onboarding per nuovi operatori

---

### 9. `cleaningStaff/` (Collection Root)
**Path**: `cleaningStaff/{staffId}`

**Campi principali**:
- `agencyId` (string)
- `displayName` (string)
- `email` (string)
- `phone` (string)
- `status` (string) - `active | inactive | invited`
- `skills` (array<string>) - riferimenti a `cleaningSkills`
- `homeBase` (map: `{ lat, lng }`)
- `availability` (map) - es: `{ monday: ['08:00-12:00', '15:00-18:00'] }`
- `lastAssignmentAt` (Timestamp | null)
- `createdAt` / `updatedAt`

**Subcollections**:
- `timesheets/{date}` - timbrature e ore lavorate

**Indice consigliato**: `(agencyId ASC, status ASC)`

---

### 10. `cleaningSkills/` (Collection Root)
**Path**: `cleaningSkills/{skillId}`

**Campi principali**:
- `agencyId` (string | null) - `null` per skill globali
- `name` (string)
- `description` (string)
- `icon` (string)
- `createdAt` / `updatedAt`

---

### 11. `cleaningJobs/` (Collection Root)
**Path**: `cleaningJobs/{jobId}`

**Campi principali**:
- `agencyId` (string)
- `hostId` (string)
- `propertyId` (string)
- `reservationId` (string | null)
- `status` (string) - `pending | scheduled | in_progress | completed | cancelled`
- `scheduledDate` (string YYYY-MM-DD)
- `plannedStart` / `plannedEnd` (Timestamp)
- `actualStart` / `actualEnd` (Timestamp)
- `estimatedDurationMinutes` (number)
- `skillsRequired` (array<string>)
- `notes` (string)
- `source` (string) - `email_agent | manual | sync`
- `planId` (string | null) - riferimento a `cleaningPlans`
- `createdAt` / `updatedAt`

**Indice consigliato**: `(agencyId ASC, scheduledDate DESC, status ASC)`

---

### 12. `cleaningPlans/` (Collection Root)
**Path**: `cleaningPlans/{planId}`

**Campi principali**:
- `agencyId` (string)
- `date` (string YYYY-MM-DD)
- `status` (string) - `draft | processing | ready | published`
- `solverVersion` (string)
- `inputJobs` (array<string>)
- `assignments` (array<map>) - `[{ jobId, staffId, startTime, endTime, travelMinutes }]`
- `metrics` (map) - `totalDistanceKm`, `utilisation`, ecc.
- `createdAt` / `updatedAt`

**Subcollections**:
- `events/{eventId}` - log di generazione piano

---

### 13. `cleaningRoutes/` (Collection Root)
**Path**: `cleaningRoutes/{routeId}`

**Campi principali**:
- `agencyId` (string)
- `planId` (string)
- `staffId` (string)
- `date` (string)
- `stops` (array<map>) - `[{ jobId, propertyId, eta, lat, lng }]`
- `distanceKm` (number)
- `travelTimeMinutes` (number)
- `generatedAt` (Timestamp)

---

## Relazioni tra Collections

```
hosts/{hostId}
  └─> properties/{propertyId} (con hostId)
  └─> reservations/{reservationId} (con hostId)
  └─> clients/{clientId} (con assignedHostId)

reservations/{reservationId}
  ├─> propertyId → properties/{propertyId}
  └─> clientId → clients/{clientId}

clients/{clientId}
  └─> assignedHostId → hosts/{hostId}

cleaningAgencies/{agencyId}
  ├─> cleaningStaff/{staffId} (tramite campo agencyId)
  ├─> cleaningJobs/{jobId}
  ├─> cleaningPlans/{planId}
  └─> cleaningRoutes/{routeId}

cleaningJobs/{jobId}
  ├─> properties/{propertyId}
  ├─> reservations/{reservationId} (se collegata)
  └─> cleaningPlans/{planId}
```

---

## Note Importanti

1. **Properties**: Collection root `properties/` con campo `hostId` per filtrare
2. **Clients**: Collection root `clients/` con campo `assignedHostId` per filtrare
3. **Reservations**: Collection root `reservations/` con riferimenti a `propertyId` e `clientId`
4. **Hosts**: Collection root `hosts/` - property manager che si registrano
5. **Filtri**: Tutte le query filtrano per `hostId` per isolare i dati per host
6. **Cleaning Agency**: tutte le nuove collezioni usano `agencyId` per l'isolamento dati; le regole Firestore devono consentire accesso solo ai documenti dell'agenzia autenticata.

## ⚠️ Collection Deprecata

### `users/` (NON USARE)
**Path**: `users/{userId}`

**Stato**: ❌ **DEPRECATA** - Non ha senso logico, è ridondante.

**Motivo**: 
- I property manager sono in `hosts/`
- I clienti/ospiti sono in `clients/`
- Non serve una collection separata `users/`

**Nota**: Alcuni servizi legacy (es. `pms-sync-service`) potrebbero ancora usare `users/` con `role: 'client'`, ma dovrebbero essere migrati a `clients/`.

