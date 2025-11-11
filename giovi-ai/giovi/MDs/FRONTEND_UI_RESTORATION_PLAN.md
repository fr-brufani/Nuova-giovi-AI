## Ripristino UI Avanzata – Piano di Implementazione

### Obiettivo
Ricostruire la UI completa già prototipata con Supabase (tab dettaglio alloggio, pagine AI/Impostazioni/Test Chatbot, flusso “Nuovo alloggio”) integrandola con la nuova struttura Firestore/servizi interni e rimuovendo gli stub “frontend-only”.

---

### Roadmap a Step (Stato Aggiornato)

#### Step 1 – Area Proprietà ✅ completato
1. **Nuova struttura componenti**
   - Creare `src/components/property-details/` con componenti modulari per tab:
     - `BaseInfoTab`, `CheckInOutTab`, `AccessTab`, `ParkingTab`, `InteriorTab`, `AreaTab`, `EmergencyTab`, `CleaningTab`.
     - Ogni componente riceve `propertyId`, `hostId`, dati pre-caricati e callback `onRefresh`.
2. **Pagina dettaglio (`/alloggi/:id`)**
   - Reintrodurre layout a tab (Tabs UI Shadcn) usando dati Firestore.
   - Query: `properties/{propertyId}` + eventuali subcollection (es. `maintenanceContacts` se necessari). Prevedere hook `usePropertyEditableState`.
   - Scrittura: aggiornare documenti su `properties` o sottocollezioni; usare `updateDoc` + `serverTimestamp`.
3. **Pagina nuovo alloggio (`/alloggi/new`)**
   - Nuova pagina `pages/AlloggiNew.tsx` con form multi-step (minimo blocco “Base” + salva).
   - Scrittura iniziale `properties` con `hostId`, `schemaVersion`, campi base.
4. **Collegamenti**
   - Aggiornare router (`App.tsx`) per `/alloggi/new`.
   - Aggiornare componenti esistenti (`PropertyCard`, dashboard, calendario) per riflettere nuove proprietà.

#### Step 2 – Impostazioni & AI ✅ completato (prima iterazione)
1. **Pagina Impostazioni**
   - Card AI Agent con toggle `aiEnabledDefault` da `hosts/{hostId}`.
   - Card Connessione Email: mostra stato da `hostEmailIntegrations`, azioni:
     - Avvia OAuth (`/auth/google/initiate`).
     - Import manuale (`/system/send-email`? da definire) e attiva notifica (`workflow-service`).
   - Ripristinare sezione PMS: per ora UI con TODO/disabled se API non pronte.
2. **Pagina AI**
   - Riportare tab Knowledge/Behavior.
   - Dati:
     - `hosts/{hostId}/knowledgeBase` (collezione Firestore) per FAQ, webs, file (con placeholder upload).
     - `hosts/{hostId}` campi `systemPrompt`, `behaviorInstructions`.
   - Implementare CRUD base (aggiungi/elimina FAQ).
3. **Pagina Test Chatbot**
   - elenco clienti + chat con endpoint `gemini-proxy-service` (`/chat` con flag `testing`).
   - Streaming: fallback append chunk (nessun SSE se non disponibile).

#### Step 3 – Refinement & QA (in corso)
1. **Cleanup stub**
   - [ ] Eliminare file `.backup` dopo validazione manuale.
   - [ ] Verificare eventuali componenti legacy ancora importati.
2. **Documentazione**
   - [ ] Aggiornare `FIRESTORE_SCHEMA_V2_MIGRATION_GUIDE.md` con mapping UI/collezioni.
   - [ ] Aggiornare README frontend con nuove variabili (`VITE_GEMINI_TEST_CHAT_ENDPOINT`).
3. **Test & lint**
   - [ ] Eseguire lint/build locale (`npm run build`).
   - [ ] Smoke test manuale: login → alloggi → nuovo/dettaglio → impostazioni → AI → chatbot.

---

### Dipendenze & API da confermare
- **Integrazione Gmail**: endpoints già esistenti in `gemini-proxy-service` (`/auth/google/initiate`, `/webhook/google/gmail-notifications`); servirà endpoint per import massivo (verificare se già implementato).
- **Workflow service**: esporre API per PMS sync/manual trigger se necessario.
- **Chat test**: definire endpoint backend per conversazioni sandbox (può usare `/chat` con flag `testing=true`).

---

### Strategia di implementazione
1. Completare Step 1 prima (uscita rapida: UI proprietà in Firestore).
2. Procedere con Step 2 in parallelo una volta validati moduli base.
3. Step 3 come wrap-up e pulizia finale.

Aggiornare questa pagina man mano che avanzano gli step (checklist, TODO, note di QA).

