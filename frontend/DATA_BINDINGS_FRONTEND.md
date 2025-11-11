# Frontend ↔ Firebase Data Mapping

Descrive come il nuovo frontend React (`giovi-ai/giovi/frontend/giovi-ai-working-app`) popola ciascuna vista tramite Firestore/Functions. Utile per verificare che i dati mostrati non siano più mock.

---

## 1. Autenticazione e profilo

| Vista / Hook | Origine dati | Note |
|--------------|--------------|------|
| `AuthProvider` (`src/providers/AuthProvider.tsx`) | Firebase Auth (`onAuthStateChanged`) + `users/{uid}` | Al login viene letto/creato il documento profilo; il ruolo è ricavato da `users/{uid}.role`. |
| `useUserRole` | `AuthProvider` | Restituisce `role` e `loading`. |
| `Sidebar`, `Index`, `Alloggi`, `Dashboard`, `Clienti`, `Calendario` | `useAuth()` | Usano `profile.role` e `profile.assignedHostId` per determinare l’host da interrogare. |

---

## 2. Alloggi

| Componente | Origine dati | Query |
|------------|--------------|-------|
| `Alloggi` (`pages/Alloggi.tsx`) | Firestore `users/{hostId}/properties` | `useHostProperties(hostId)` usa `collection(db, 'users', hostId, 'properties')`. |
| `Dashboard` (sezione “I tuoi alloggi”) | Idem | Mostra prime 6 proprietà da `useHostProperties`. |
| `AlloggiDetail` (`pages/AlloggiDetail.tsx`) | Firestore `users/{hostId}/properties/{propertyId}` | `usePropertyById(hostId, propertyId)` esegue `doc(...).get()`. Mostra anche il campo raw JSON. |

Campi principali attesi per ogni proprietà: `name`, `address/indirizzo`, `rooms/stanze`, `capacity/ospiti_max`, `cleaningContactName`, `cleaningContactPhone`, eventuali `coverImage`.

---

## 3. Prenotazioni

| Componente | Origine dati | Query |
|------------|--------------|-------|
| `Dashboard` (occupazione) | Firestore `reservations` | `useHostReservations(hostId)`, query `where('hostId', '==', hostId)`. |
| `Clienti` (`pages/Clienti.tsx`) | Idem | Lista prenotazioni, join con clienti/proprietà. |
| `Calendario` (`pages/Calendario.tsx`) | Idem | Mappa prenotazioni per settimana. |
| `AlloggiDetail` (sezione “Prossime prenotazioni”) | `reservations` filtrate per proprietà | `useReservationsByProperty(hostId, propertyId)` con `where('propertyId','==',propertyId)` e `orderBy('startDate','desc')`. |

Campi attesi: `propertyId`, `clientId`, `startDate`, `endDate`, `status`, `propertyName`, `clientName`, `importedFrom`.

---

## 4. Clienti

| Componente | Origine dati | Query |
|------------|--------------|-------|
| `Clienti` (colonna sinistra) | Firestore `users` | `useClientsByIds(ids)` esegue batch di `where(documentId(), 'in', chunk)`. |
| `Clienti` (contatti) | `users/{clientId}` | Recupera `name`, `email`, `whatsappPhoneNumber`. |

---

## 5. Chat & Task

| Componente | Origine dati | Query |
|------------|--------------|-------|
| `Clienti` (chat destra) | Firestore `gioviAiChatDataset` | `useChatMessages(clientId, propertyId)` → query `where('userId','==', clientId)` + `where('propertyId','==', propertyId)` + `orderBy('timestamp','asc')`. |
| Messaggi sistema | `gioviAiChatDataset` | Messaggi con `isSystemUpdate` vengono mostrati come mittente `system`. |
| Task operativi (pulizie) | Firestore `propertyTasks` | Ancora non visualizzati lato UI; prevista integrazione nella fase workflow. |

---

## 6. Verifica assenza mock

1. Nel progetto non esistono più import da `src/data/mockData.ts` (file rimosso).
2. Tutti i componenti utilizzano hook in `src/services/firestore/` oppure `useAuth`.
3. Per confermare via codice:
   ```bash
   rg \"mock\" src/
   ```
   deve restituire vuoto (eccetto commenti se presenti).

---

## 7. Test manuale consigliato

1. Avviare `npm run dev -- --host 0.0.0.0 --port 4173`.
2. Aprire `http://localhost:4173/`, registrarsi/loggarsi con utente host.
3. Verificare:
   - `Dashboard`: conteggi reali (proprietà e prenotazioni attive).
   - `Alloggi`: elenco proprietà reali; clic → dettaglio con dati raw Firestore.
   - `Clienti`: lista prenotazioni → associare chat registrata in `gioviAiChatDataset`.
   - `Calendario`: prenotazioni distribuite nella settimana.
4. In assenza di dati Firestore, le UI mostrano stati vuoti (card con messaggi “Nessun alloggio/cliente”).

---

## 8. Prossimi passi (per fasi successive)

| Fase | Azione |
|------|--------|
| 3 | Collegare `TestChatbot`/`AI` a `getAiChatResponse` (Firebase Functions). |
| 3 | Abilitare invio messaggi (workflow-service). |
| 4 | Integrare configurazioni PMS (`pms-sync-service` REST). |

---

Ultimo aggiornamento: 2025-11-11.

