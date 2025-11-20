# Core Service – Panoramica dei flussi

Questo documento racconta, con un linguaggio non tecnico, cosa fa il servizio di Giovi AI e come si coordinano i vari pezzi. Il servizio nasce per aiutare i property manager a gestire prenotazioni, conversazioni con gli ospiti e attività operative partendo da email, sistemi esterni e intelligenza artificiale.

## 1. Componenti principali

- collegare le proprie caselle mail al servizio in modo da poter automi.
- **Archivio dati (Firestore)**: raccoglie informazioni strutturate su host, proprietà, prenotazioni, clienti, conversazioni e task operativi.
- **Workflow**: sono i “percorsi guidati” che trasformano un evento (es. una nuova email) in aggiornamenti coerenti nel sistema.
- **Trasporti**: sono gli ingressi del servizio (endpoint HTTP e abbonamenti Pub/Sub) che ricevono richieste dall’esterno e avviano i workflow.

## 2. Raccolta e normalizzazione delle email

**Obiettivo**: leggere email provenienti da Airbnb, Booking, Scidoo, altri pms o da messaggi diretti degli ospiti, estrarre i dati importanti e aggiornare automaticamente prenotazioni e conversazioni.

**Come funziona**:
1. Il servizio riceve una notifica da Gmail.


2. Scarica il contenuto del messaggio e lo passa a una libreria di “parser” che riconosce il formato (es. conferma Airbnb).
3. Vengono ricostruiti i dati chiave: numero di prenotazione, ospite, date del soggiorno, conversazione, importi, ecc.
4. Il sistema aggiorna o crea:
   - l’host e la proprietà associati all’email;
   - la prenotazione (status, date, importi);
   - il profilo del cliente;
   - la conversazione, aggiungendo il nuovo messaggio, così da avere storico e anteprima.
5. Ogni email viene registrata anche in modalità “grezza” per poterla rileggere o debuggare in futuro.

**Perché è utile**: elimina l’inserimento manuale dei dati e mantiene allineato l’archivio centrale con ciò che arriva dai portali di booking e dalle caselle di posta.

## 3. Import delle prenotazioni dal PMS

**Obiettivo**: caricare rapidamente prenotazioni provenienti da sistemi gestionali (PMS) fornendo un file CSV, un JSON o direttamente via API Scidoo.

**Come funziona**:
1. Un operatore o un processo esterno invia un elenco di prenotazioni all’endpoint dedicato (`/pms/import` o `/integrations/scidoo/import`).
2. Il servizio legge i campi principali (host, proprietà, cliente, canale, date, importi).
3. Ogni prenotazione viene salvata con origine “pms-import”, in modo da distinguerla dalle email.
4. Se sono disponibili i dati cliente, viene aggiornato anche il profilo contatti.
5. Viene creata o aggiornata una conversazione “di servizio” per segnalare che la prenotazione è arrivata via PMS.

**Perché è utile**: garantisce che il sistema disponga di una base dati completa anche quando i portali non inviano email o quando si preferisce un caricamento massivo.

## 4. Conversazioni gestite dall’AI

**Obiettivo**: generare risposte automatiche e su misura per gli ospiti, mantenendo traccia dello scambio.

**Come funziona**:
1. Il frontend o un flusso Pub/Sub invia una richiesta di risposta (`/chat/respond` o messaggio `chat.request`).
2. Il servizio verifica se l’ospite ha disattivato le risposte automatiche.
3. Formula il prompt per l’AI Gemini, includendo eventuali dettagli di prenotazione.
4. A seconda del canale richiesto:
   - invia una email tramite SendGrid;
   - spedisce un messaggio WhatsApp via Meta Business.
5. Registra la risposta AI nella conversazione, così da avere uno storico completo.
6. Se l’AI suggerisce azioni operative (tool call), le invia al workflow dei task tramite Pub/Sub.

**Perché è utile**: riduce i tempi di risposta agli ospiti mantenendo una traccia ordinata di ogni scambio e collegando l’AI ai processi operativi.

## 5. Orchestrazione dei task operativi

**Obiettivo**: trasformare suggerimenti o necessità operative (es. chiamare una ditta di pulizie) in task strutturati, assegnabili e monitorabili.

**Come funziona**:
1. Riceve un evento `tasks.toolCall` da Pub/Sub, spesso generato dall’AI.
2. Recupera le informazioni della prenotazione collegata.
3. Crea o aggiorna il task (titolo, priorità, scadenze, contatti utili).
4. Registra un evento cronologico per tracciare l’origine del compito.
5. Aggiorna la conversazione della prenotazione con una nota di sistema (“Task aggiornato…”).

**Perché è utile**: collega automaticamente conversazioni e operatività, evitando che le azioni suggerite dall’AI vadano perse.

## 6. Backfill e manutenzione

- **Backfill Gmail/Scidoo**: permette di rileggere le email degli ultimi mesi per recuperare eventuali notifiche perse. Utile dopo un nuovo collegamento o una bonifica.
- **Reset Host**: cancella in blocco i dati di un host (proprietà, prenotazioni, clienti) quando si deve ripartire da zero o dismettere un account.

Questi strumenti sono controllati via endpoint dedicati e pensati per essere usati da operatori con privilegi elevati.

## 7. Monitoraggio e salute del servizio

- **`/_health`** restituisce uno stato “ok” per verificare rapidamente se l’istanza è attiva.
- **`/metrics`** espone indicatori per Prometheus (tempo di risposta HTTP, numero di eventi elaborati per tipo).
- Il logging centralizzato consente di seguire ogni passo dei workflow e indentificare facilmente errori o ritardi.

## 8. Flusso quotidiano consigliato

1. Le email e le API alimentano Firestore con prenotazioni e messaggi aggiornati.
2. Gli operatori possono verificare lo storico conversazioni e affidare richieste speciali all’AI.
3. Le risposte AI e i task generati vengono salvati automaticamente, mantenendo sempre sincronizzate conversazioni e attività.
4. In caso di problemi o nuovi collegamenti, i backfill aiutano a chiudere eventuali buchi di dati, mentre i reset consentono di ripartire da uno stato pulito.

---

Con questo schema, il core service diventa il fulcro operativo: qualsiasi informazione che entra (email, import PMS, richieste dall’AI) viene trasformata in dati coerenti e “pronti all’uso” per l’esperienza utente e per gli altri servizi dell’ecosistema Giovi AI.


