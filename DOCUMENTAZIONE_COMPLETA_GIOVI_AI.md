# 📘 Documentazione Completa - Giovi AI

**Versione:** 1.0  
**Data:** Gennaio 2025  
**Scopo:** Documentazione esaustiva del sistema Giovi AI per la costruzione del sito web

---

## 📋 Indice

1. [Panoramica Generale](#panoramica-generale)
2. [Architettura del Sistema](#architettura-del-sistema)
3. [Frontend - Applicazione Web](#frontend---applicazione-web)
4. [Email Agent Service](#email-agent-service)
5. [Agency Service](#agency-service)
6. [Database Firestore](#database-firestore)
7. [Integrazioni Esterne](#integrazioni-esterne)
8. [Flussi Principali](#flussi-principali)
9. [Stack Tecnologico](#stack-tecnologico)
10. [Ruoli e Permessi](#ruoli-e-permessi)

---

## Panoramica Generale

**Giovi AI** è una piattaforma SaaS completa per la gestione di alloggi turistici (short-term rentals) che automatizza:

- **Importazione automatica delle prenotazioni** da piattaforme OTA (Booking.com, Airbnb) e PMS (Scidoo, Smoobu)
- **Gestione clienti e comunicazioni** con risposte AI automatiche
- **Pianificazione e ottimizzazione delle pulizie** tramite agenzie partner
- **Dashboard operativa** per property manager e agenzie di pulizie

### Utenti Target

1. **Property Manager (Host)** - Gestisce proprietà, prenotazioni, clienti
2. **Cleaning Agency** - Gestisce staff, lavori di pulizia, pianificazione
3. **Test User** - Utenti per testing e sviluppo

### Valore Proposto

- **Automazione completa** dell'import prenotazioni da email e API
- **AI Concierge** che risponde automaticamente ai messaggi degli ospiti
- **Ottimizzazione operativa** delle pulizie con rotte geolocalizzate
- **Dashboard unificata** per gestire tutto in un unico posto

---

## Architettura del Sistema

### Componenti Principali

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                        │
│  ┌──────────────────────┐         ┌──────────────────────┐    │
│  │ Property Manager UI   │         │ Cleaning Agency UI    │    │
│  │  (Dashboard, Alloggi, │         │  (/agency/* routes)   │    │
│  │   Clienti, Calendario)│         │  (Staff, Jobs, Plans) │    │
│  └──────────────────────┘         └──────────────────────┘    │
└────────────┬──────────────────────────────┬─────────────────────┘
             │                               │
             │ HTTP/REST                     │ HTTP/REST
             │                               │
    ┌────────▼────────┐            ┌─────────▼─────────┐
    │ Email Agent      │            │ Agency Service    │
    │ Service (FastAPI)│            │ (FastAPI)         │
    │ Port: 8000       │            │ Port: 8050       │
    └────────┬─────────┘            └─────────┬─────────┘
             │                               │
             │ Firebase Admin SDK            │
             │                               │
    ┌────────▼───────────────────────────────▼────────┐
    │              Firestore Database                   │
    │  - properties, reservations, clients, hosts       │
    │  - cleaningAgencies, cleaningStaff, cleaningJobs│
    │  - hostEmailIntegrations, oauthStates             │
    └───────────────────────────────────────────────────┘
             │
             │ External APIs
             │
    ┌────────▼────────┬──────────────┬──────────────┐
    │ Gmail API       │ Scidoo API    │ Smoobu API    │
    │ Booking API     │ Gemini AI     │               │
    └─────────────────┴───────────────┴───────────────┘
```

### Pattern Architetturali

- **Microservizi**: Email Agent Service e Agency Service sono servizi FastAPI indipendenti
- **Repository Pattern**: Separazione logica business da accesso dati
- **Dependency Injection**: Servizi e repository iniettati via FastAPI Depends
- **Multi-tenant**: Isolamento dati per `hostId` e `agencyId` in Firestore

---

## Frontend - Applicazione Web

### Tecnologie

- **Framework**: React 18.3 + TypeScript
- **Build Tool**: Vite 5.4
- **Routing**: React Router DOM 6.26
- **State Management**: TanStack Query (React Query) 5.90
- **UI Components**: Radix UI + shadcn/ui
- **Styling**: Tailwind CSS 3.4
- **Authentication**: Firebase Auth
- **Database Client**: Firebase SDK (Firestore)

### Struttura Progetto

```
giovi-ai/giovi/frontend/giovi-ai-working-app/
├── src/
│   ├── pages/                    # Pagine principali
│   │   ├── Index.tsx            # Dashboard principale
│   │   ├── Auth.tsx             # Login/Registrazione
│   │   ├── Alloggi.tsx          # Lista proprietà
│   │   ├── AlloggiDetail.tsx    # Dettaglio proprietà
│   │   ├── Clienti.tsx           # Gestione clienti e chat
│   │   ├── Calendario.tsx        # Calendario prenotazioni
│   │   ├── Impostazioni.tsx     # Configurazioni e integrazioni
│   │   ├── AI.tsx                # Interfaccia AI chatbot
│   │   └── agency/               # UI per agenzie pulizie
│   │       ├── Dashboard.tsx
│   │       ├── Staff.tsx
│   │       ├── Jobs.tsx
│   │       ├── Planning.tsx
│   │       ├── Routes.tsx
│   │       └── Skills.tsx
│   ├── components/               # Componenti riutilizzabili
│   │   ├── layout/              # Layout, Sidebar, Navbar
│   │   ├── properties/          # Card proprietà
│   │   ├── settings/            # Card integrazioni
│   │   └── agency/              # Componenti agenzie
│   ├── services/
│   │   ├── firestore/           # Hook e client Firestore
│   │   │   ├── properties.ts
│   │   │   ├── reservations.ts
│   │   │   ├── clients.ts
│   │   │   └── chat.ts
│   │   └── api/                 # Client API backend
│   │       ├── agency.ts
│   │       └── testConversations.ts
│   ├── hooks/
│   │   ├── useAuth.ts           # Hook autenticazione
│   │   └── useUserRole.tsx      # Hook ruolo utente
│   └── providers/
│       └── AuthProvider.tsx     # Context autenticazione
```

### Pagine Principali - Property Manager

#### 1. **Dashboard (Index.tsx)**
- **Funzionalità**: Vista principale con KPI e overview
- **Dati mostrati**:
  - Numero proprietà gestite
  - Prenotazioni attive/in arrivo
  - Occupazione mensile
  - Ultime attività
- **Routing**: `/` (redirect in base al ruolo)

#### 2. **Alloggi (Alloggi.tsx)**
- **Funzionalità**: Gestione proprietà/alloggi
- **Operazioni**:
  - Lista tutte le proprietà dell'host
  - Creazione nuova proprietà
  - Visualizzazione dettagli proprietà
- **Dati Firestore**: `properties/` filtrate per `hostId`
- **Routing**: `/alloggi`, `/alloggi/new`, `/alloggi/:id`

#### 3. **Clienti (Clienti.tsx)**
- **Funzionalità**: Gestione clienti e comunicazioni
- **Operazioni**:
  - Lista prenotazioni con dettagli cliente
  - Chat con ospiti (messaggi AI)
  - Toggle auto-reply per cliente
  - Filtri per stato prenotazione
- **Dati Firestore**: 
  - `reservations/` per hostId
  - `clients/` per clientId
  - `gioviAiChatDataset/` per messaggi
- **Routing**: `/clienti`

#### 4. **Calendario (Calendario.tsx)**
- **Funzionalità**: Vista calendario settimanale prenotazioni
- **Operazioni**:
  - Navigazione settimane
  - Visualizzazione prenotazioni per giorno
  - Filtro per proprietà
  - Click su prenotazione per dettagli
- **Dati Firestore**: `reservations/` con date check-in/out
- **Routing**: `/calendario`

#### 5. **Impostazioni (Impostazioni.tsx)**
- **Funzionalità**: Configurazione integrazioni e mapping proprietà
- **Sezioni**:
  - **Integrazione Gmail**: OAuth, backfill email, watch
  - **Integrazione PMS**: Scidoo, Smoobu, Booking
  - **Property Mappings**: Matching proprietà importate vs gestite
- **API chiamate**: Email Agent Service endpoints
- **Routing**: `/impostazioni`

#### 6. **AI (AI.tsx)**
- **Funzionalità**: Interfaccia per testare AI chatbot
- **Operazioni**:
  - Invio messaggi di test
  - Visualizzazione risposte AI
  - Selezione proprietà e cliente
- **Backend**: Firebase Cloud Functions `getAiChatResponse`

### Pagine Agenzie Pulizie (/agency/*)

#### 1. **Agency Dashboard**
- **KPI**: Staff attivo, lavori oggi, percorsi ottimizzati, completati
- **Widget**: Lavori pending, staff disponibile
- **API**: `GET /api/stats`

#### 2. **Staff Management**
- **CRUD**: Creazione, modifica, disattivazione operatori
- **Campi**: Nome, email, telefono, competenze, status
- **API**: `GET/POST/PATCH /api/staff`

#### 3. **Jobs Management**
- **Lista lavori**: Pending, scheduled, in_progress, completed
- **Filtri**: Data, status, proprietà
- **Creazione**: Manuale o da prenotazioni
- **API**: `GET/POST/PATCH /api/jobs`

#### 4. **Planning**
- **Generazione piano**: Piano giornaliero ottimizzato
- **Algoritmo**: VRP (Vehicle Routing Problem) placeholder
- **Output**: Assegnazioni staff → jobs con orari
- **API**: `POST /api/plans/generate`

#### 5. **Routes**
- **Visualizzazione**: Percorsi ottimizzati per staff
- **Dati**: Stops geolocalizzati, distanze, tempi viaggio
- **API**: `GET /api/routes`

#### 6. **Skills**
- **Catalogo**: Competenze richieste per lavori
- **CRUD**: Creazione skill globali o per agenzia
- **API**: `GET/POST /api/skills`

### Autenticazione e Routing

- **Firebase Auth**: Login/Registrazione con email/password
- **Ruoli**: `property_manager`, `cleaning_agency`, `test_user`
- **Guards**: Redirect automatico in base al ruolo
- **Session**: Persistenza via Firebase Auth state

---

## Email Agent Service

### Panoramica

Servizio FastAPI che gestisce:
1. **Importazione email** da Gmail (Booking, Airbnb, Scidoo)
2. **Parsing email** per estrarre prenotazioni
3. **Persistenza automatica** in Firestore
4. **Integrazioni PMS** (Scidoo, Smoobu)
5. **AI Reply** automatico ai messaggi ospiti
6. **Gmail Watch** per notifiche real-time

### Tecnologie

- **Framework**: FastAPI 0.115+
- **Database**: Firebase Admin SDK + Firestore
- **APIs**: Gmail API, Gemini AI, Scidoo API, Smoobu API
- **Crypto**: Fernet per cifratura token
- **Parsing**: BeautifulSoup4 per HTML email

### Endpoint Principali

#### Integrazioni Gmail

- `POST /integrations/gmail/start` - Inizia OAuth flow
- `POST /integrations/gmail/callback` - Completa OAuth
- `POST /integrations/gmail/{email}/backfill` - Import email ultimi 6 mesi
- `POST /integrations/gmail/{email}/backfill/preview` - Preview email da importare
- `POST /integrations/gmail/{email}/watch` - Setup Gmail watch
- `POST /integrations/gmail/notifications` - Handler notifiche Pub/Sub
- `DELETE /integrations/gmail/{email}` - Rimuovi integrazione

#### Integrazioni Scidoo

- `POST /integrations/scidoo/{host_id}/configure` - Configura credenziali
- `POST /integrations/scidoo/{host_id}/sync` - Sincronizza prenotazioni
- `POST /integrations/scidoo/{host_id}/test` - Test connessione
- `GET /integrations/scidoo/{host_id}/room-types` - Lista room types
- `DELETE /integrations/scidoo/{host_id}` - Rimuovi integrazione

#### Integrazioni Smoobu

- `POST /integrations/smoobu/webhook` - Webhook prenotazioni
- `POST /integrations/smoobu/import` - Import manuale
- `POST /integrations/smoobu/test` - Test API key
- `GET /integrations/smoobu/status` - Stato integrazione
- `DELETE /integrations/smoobu` - Rimuovi integrazione

#### Property Mappings

- `GET /property-mappings/hosts/{host_id}/property-match` - Matching proprietà
- `POST /property-mappings/hosts/{host_id}/property-match/batch` - Batch matching
- `GET /property-mappings/hosts/{host_id}/property-mappings` - Lista mappings
- `POST /property-mappings/hosts/{host_id}/property-mappings` - Crea mapping
- `PATCH /property-mappings/hosts/{host_id}/property-mappings/{mapping_id}` - Aggiorna
- `DELETE /property-mappings/hosts/{host_id}/property-mappings/{mapping_id}` - Rimuovi

#### Clients

- `PATCH /clients/{client_id}/auto-reply` - Toggle auto-reply
- `PATCH /clients/auto-reply/bulk` - Bulk toggle

#### Host Settings

- `PATCH /integrations/hosts/{host_id}/airbnb-only` - Modalità solo Airbnb
- `PATCH /integrations/hosts/{host_id}/auto-reply-to-new-reservations` - Auto-reply nuove prenotazioni

### Flusso OAuth Gmail

1. **Frontend** chiama `POST /integrations/gmail/start` con `hostId` e `email`
2. **Backend** genera URL OAuth Google e salva state in `oauthStates/`
3. **Utente** autorizza su Google
4. **Google** redirecta a callback con `code` e `state`
5. **Frontend** chiama `POST /integrations/gmail/callback`
6. **Backend** scambia code per token, cifra con Fernet, salva in `hostEmailIntegrations/`

### Flusso Backfill Email

1. **Frontend** chiama `POST /integrations/gmail/{email}/backfill?host_id=...`
2. **Backend**:
   - Recupera token cifrato da Firestore
   - Chiama Gmail API con query: `(from:@mchat.booking.com OR from:@reply.airbnb.com OR from:reservation@scidoo.com) AND after:{6mesi}`
   - Per ogni email:
     - Verifica deduplica in `processedMessageIds/`
     - Passa ai parser (Booking, Airbnb, Scidoo)
     - Estrae dati prenotazione/cliente
     - Salva in Firestore via `PersistenceService`
     - Marca come processata

### Parser Email Implementati

#### Booking.com
- **BookingConfirmationParser**: Estrae `reservationId`, `propertyName`, `checkIn`, `checkOut`, `guestName`, `guestEmail`, `totalAmount`
- **BookingMessageParser**: Estrae `reservationId`, `message`, `replyTo`

#### Airbnb
- **AirbnbConfirmationParser**: Estrae `threadId`, `propertyName`, `checkIn`, `checkOut`, `guestName`, `totalAmount`
- **AirbnbMessageParser**: Estrae `threadId`, `message`, `replyTo`
- **AirbnbCancellationParser**: Estrae `reservationId` per cancellazione

#### Scidoo
- **ScidooConfirmationParser**: Estrae `voucherId`, `reservationId`, `propertyName`, `checkIn`, `checkOut`
- **ScidooCancellationParser**: Estrae `voucherId` per cancellazione

### Persistenza Automatica

Il `PersistenceService` salva automaticamente:

1. **Properties** in `properties/`:
   - Cerca per `name` e `hostId`
   - Se non esiste, crea nuovo documento
   - Campi: `name`, `hostId`, `address`, `city`, `bedrooms`, `bathrooms`, `capacity`

2. **Clients** in `clients/`:
   - Cerca per `email` (lowercase) e `assignedHostId`
   - Se non esiste, crea nuovo documento
   - Campi: `name`, `email`, `whatsappPhoneNumber`, `assignedHostId`, `assignedPropertyId`, `reservationId`

3. **Reservations** in `reservations/`:
   - Cerca per `reservationId` e `hostId`
   - Se esiste, aggiorna; altrimenti crea
   - Campi: `hostId`, `propertyId`, `clientId`, `startDate`, `endDate`, `status`, `totalPrice`, `importedFrom`

### Integrazione Scidoo

- **Polling Service**: Controlla nuove prenotazioni ogni X minuti
- **API Client**: Chiama Scidoo Reservation API
- **Room Types**: Mapping room types Scidoo → properties
- **Property Mappings**: Risoluzione automatica proprietà

### Integrazione Smoobu

- **Webhook**: Riceve notifiche prenotazioni in real-time
- **API Import**: Import manuale prenotazioni
- **Property Mappings**: Mapping automatico proprietà

### AI Reply (Gemini)

- **GeminiService**: Chiama Gemini 2.5 Flash API
- **Prompt Building**: Costruisce prompt con contesto property, prenotazione, conversazione
- **Guest Message Pipeline**: Processa messaggi ospiti, verifica `autoReplyEnabled`, genera risposta
- **Gmail Send**: Invia risposta via Gmail API

### Gmail Watch

- **Setup**: Chiama Gmail `users().watch()` con Pub/Sub topic
- **Notifications**: Handler Pub/Sub riceve notifiche nuove email
- **Refresh**: Watch scade dopo 7 giorni, serve refresh automatico

---

## Agency Service

### Panoramica

Servizio FastAPI dedicato alle agenzie di pulizie che gestisce:
1. **Staff Management** - Operatori e competenze
2. **Jobs Management** - Lavori di pulizia
3. **Planning** - Generazione piani giornalieri ottimizzati
4. **Routes** - Percorsi geolocalizzati
5. **Skills** - Catalogo competenze

### Tecnologie

- **Framework**: FastAPI 0.115+
- **Database**: Firebase Admin SDK + Firestore
- **Python**: 3.11+

### Endpoint Principali

#### Stats
- `GET /api/stats` - KPI dashboard (staff attivo, lavori oggi, percorsi, completati)

#### Staff
- `GET /api/staff` - Lista operatori
- `POST /api/staff` - Crea operatore
- `PATCH /api/staff/{staff_id}` - Aggiorna operatore

#### Jobs
- `GET /api/jobs` - Lista lavori (filtri: status, scheduledDate)
- `POST /api/jobs` - Crea lavoro
- `PATCH /api/jobs/{job_id}` - Aggiorna lavoro (status, orari)

#### Plans
- `GET /api/plans` - Lista piani
- `POST /api/plans/generate` - Genera piano giornaliero

#### Routes
- `GET /api/routes` - Lista percorsi ottimizzati

#### Skills
- `GET /api/skills` - Lista competenze
- `POST /api/skills` - Crea competenza

### Autenticazione

- **Header richiesto**: `X-Agency-Id` (UID Firebase agenzia)
- **Middleware**: `require_agency_id()` verifica esistenza `cleaningAgencies/{agencyId}`
- **Isolamento**: Tutte le query filtrano per `agencyId`

### Planning Engine

- **Algoritmo**: VRP (Vehicle Routing Problem) placeholder
- **Input**: Jobs pending per data, staff disponibile, skills richieste
- **Output**: Assegnazioni staff → jobs con orari ottimizzati
- **Metriche**: Distanza totale, utilizzo staff, tempi viaggio

### Integrazione con Email Agent Service

- **Jobs Creation**: Email Agent Service crea `cleaningJobs/` quando importa prenotazioni
- **Source**: Campo `source: "email_agent"` vs `"manual"`
- **Linking**: `reservationId` collega job a prenotazione

---

## Database Firestore

### Collections Principali

#### 1. `properties/` (Root Collection)
Gestisce le proprietà/alloggi.

**Campi principali**:
- `hostId` (string) - ID proprietario
- `name` (string) - Nome proprietà
- `address`, `city`, `country` (string)
- `bedrooms`, `bathrooms`, `capacity` (number)
- `checkInTime`, `checkOutTime` (string)
- `accessCode`, `accessInstructions` (string)
- `cleaningContactName`, `cleaningContactPhone` (string)
- `createdAt`, `updatedAt` (Timestamp)

**Query tipica**: `properties.where("hostId", "==", hostId)`

#### 2. `reservations/` (Root Collection)
Gestisce le prenotazioni.

**Campi principali**:
- `hostId`, `propertyId`, `clientId` (string)
- `propertyName`, `clientName` (string, denormalizzato)
- `startDate`, `endDate` (Timestamp)
- `status` (string) - "confirmed", "cancelled"
- `totalPrice` (number)
- `adults`, `children` (number)
- `importedFrom` (string) - "scidoo_email", "smoobu", "booking", "airbnb"
- `createdAt`, `lastUpdatedAt` (Timestamp)

**Query tipica**: `reservations.where("hostId", "==", hostId)`

#### 3. `clients/` (Root Collection)
Gestisce i clienti/ospiti.

**Campi principali**:
- `name`, `email` (string)
- `whatsappPhoneNumber` (string)
- `assignedHostId`, `assignedPropertyId`, `reservationId` (string)
- `autoReplyEnabled` (boolean) - Flag per AI reply
- `importedFrom` (string)
- `createdAt`, `lastUpdatedAt` (Timestamp)

**Query tipica**: `clients.where("email", "==", email).where("assignedHostId", "==", hostId)`

#### 4. `hosts/` (Root Collection)
Gestisce i property manager.

**Campi principali**:
- `hostId`, `email`, `displayName` (string)
- `role` (string) - "host"
- `behaviorInstructions`, `systemPrompt` (string, opzionale)
- `airbnbOnly` (boolean) - Modalità solo Airbnb
- `autoReplyToNewReservations` (boolean)
- `createdAt`, `lastLoginAt` (Timestamp)

#### 5. `hostEmailIntegrations/` (Root Collection)
Gestisce le integrazioni Gmail.

**Campi principali**:
- `emailAddress` (string) - Email Gmail
- `hostId` (string)
- `provider` (string) - "gmail"
- `pmsProvider` (string) - "scidoo", "booking", "airbnb", "other"
- `status` (string) - "connected", "disconnected"
- `encryptedAccessToken`, `encryptedRefreshToken` (string)
- `tokenExpiryDate` (Timestamp)
- `watchSubscription` (map) - Info Gmail watch

**Subcollection**: `processedMessageIds/{messageId}` - Email già processate

#### 6. `cleaningAgencies/` (Root Collection)
Gestisce le agenzie di pulizie.

**Campi principali**:
- `agencyId` (string) - UID Firebase
- `hostId` (string | null) - Property manager collegato
- `displayName`, `email`, `phone` (string)
- `baseLocation` (map) - `{address, city, country, lat, lng}`
- `skillsOffered` (array<string>)
- `defaultShiftStart`, `defaultShiftEnd` (string)
- `createdAt`, `updatedAt` (Timestamp)

#### 7. `cleaningStaff/` (Root Collection)
Gestisce gli operatori delle agenzie.

**Campi principali**:
- `agencyId` (string)
- `displayName`, `email`, `phone` (string)
- `status` (string) - "active", "inactive", "invited"
- `skills` (array<string>) - Riferimenti a `cleaningSkills`
- `homeBase` (map) - `{lat, lng}`
- `availability` (map) - `{monday: ['08:00-12:00']}`
- `createdAt`, `updatedAt` (Timestamp)

#### 8. `cleaningJobs/` (Root Collection)
Gestisce i lavori di pulizia.

**Campi principali**:
- `agencyId`, `hostId`, `propertyId` (string)
- `reservationId` (string | null)
- `status` (string) - "pending", "scheduled", "in_progress", "completed", "cancelled"
- `scheduledDate` (string) - YYYY-MM-DD
- `plannedStart`, `plannedEnd` (Timestamp)
- `actualStart`, `actualEnd` (Timestamp)
- `estimatedDurationMinutes` (number)
- `skillsRequired` (array<string>)
- `source` (string) - "email_agent", "manual", "sync"
- `planId` (string | null)
- `createdAt`, `updatedAt` (Timestamp)

#### 9. `cleaningPlans/` (Root Collection)
Gestisce i piani giornalieri.

**Campi principali**:
- `agencyId` (string)
- `date` (string) - YYYY-MM-DD
- `status` (string) - "draft", "processing", "ready", "published"
- `solverVersion` (string)
- `inputJobs` (array<string>)
- `assignments` (array<map>) - `[{jobId, staffId, startTime, endTime, travelMinutes}]`
- `metrics` (map) - `{totalDistanceKm, utilisation}`
- `createdAt`, `updatedAt` (Timestamp)

#### 10. `cleaningRoutes/` (Root Collection)
Gestisce i percorsi ottimizzati.

**Campi principali**:
- `agencyId`, `planId`, `staffId` (string)
- `date` (string)
- `stops` (array<map>) - `[{jobId, propertyId, eta, lat, lng}]`
- `distanceKm`, `travelTimeMinutes` (number)
- `generatedAt` (Timestamp)

#### 11. `cleaningSkills/` (Root Collection)
Gestisce le competenze.

**Campi principali**:
- `agencyId` (string | null) - null per skill globali
- `name`, `description`, `icon` (string)
- `createdAt`, `updatedAt` (Timestamp)

#### 12. `gioviAiChatDataset/` (Root Collection)
Gestisce i messaggi chat AI.

**Campi principali**:
- `userId`, `propertyId`, `hostId` (string)
- `userMessage`, `aiResponse` (string)
- `channel` (string)
- `timestamp` (Timestamp)
- `promptSent` (string)
- `wasBlocked` (boolean)

### Relazioni tra Collections

```
hosts/{hostId}
  ├─> properties/{propertyId} (via hostId)
  ├─> reservations/{reservationId} (via hostId)
  └─> clients/{clientId} (via assignedHostId)

reservations/{reservationId}
  ├─> propertyId → properties/{propertyId}
  └─> clientId → clients/{clientId}

cleaningAgencies/{agencyId}
  ├─> cleaningStaff/{staffId} (via agencyId)
  ├─> cleaningJobs/{jobId} (via agencyId)
  ├─> cleaningPlans/{planId} (via agencyId)
  └─> cleaningRoutes/{routeId} (via agencyId)

cleaningJobs/{jobId}
  ├─> propertyId → properties/{propertyId}
  ├─> reservationId → reservations/{reservationId}
  └─> planId → cleaningPlans/{planId}
```

---

## Integrazioni Esterne

### 1. Gmail API
- **Scopo**: Import email prenotazioni e messaggi ospiti
- **OAuth**: OAuth 2.0 flow per autorizzazione
- **Scopes**: `gmail.readonly`, `gmail.modify`, `gmail.send`
- **Operazioni**: List messages, get message, send reply, watch
- **Rate Limits**: 250 quota units/second

### 2. Gemini AI (Google)
- **Scopo**: Generazione risposte AI automatiche
- **Model**: Gemini 2.5 Flash
- **API**: REST `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent`
- **Prompt**: Contesto property + prenotazione + conversazione
- **Safety**: HARM_CATEGORY blocking configurato

### 3. Scidoo API
- **Scopo**: Sincronizzazione prenotazioni da PMS Scidoo
- **Auth**: API key + secret
- **Endpoints**: Reservation API, Room Types API
- **Polling**: Service controlla nuove prenotazioni periodicamente
- **Property Mapping**: Mapping room types → properties

### 4. Smoobu API
- **Scopo**: Sincronizzazione prenotazioni da PMS Smoobu
- **Auth**: API key
- **Webhook**: Notifiche real-time nuove prenotazioni
- **Endpoints**: Reservations API, Properties API
- **Property Mapping**: Mapping automatico proprietà

### 5. Booking.com Messaging API
- **Scopo**: Invio risposte ai messaggi ospiti Booking
- **Auth**: OAuth 2.0
- **Endpoints**: Send message, Get conversation
- **Status**: Parzialmente implementato

### 6. Firebase Services
- **Firebase Auth**: Autenticazione utenti
- **Firestore**: Database NoSQL
- **Cloud Functions**: `getAiChatResponse` per AI chatbot
- **Storage**: (opzionale) per allegati

---

## Flussi Principali

### Flusso 1: Onboarding Property Manager

1. **Registrazione**: Utente si registra su `/auth` con email/password
2. **Creazione Host**: Firebase Auth crea utente, Firestore crea `hosts/{uid}`
3. **Setup Integrazione Gmail**: 
   - Vai su `/impostazioni`
   - Inserisci email Gmail
   - Clicca "Collega Gmail" → OAuth flow
   - Autorizza su Google
4. **Backfill Email**: 
   - Clicca "Importa email prenotazioni"
   - Sistema importa ultimi 6 mesi
   - Parser estrae prenotazioni
   - Salva in Firestore: `properties/`, `clients/`, `reservations/`
5. **Property Mapping**: 
   - Sistema mostra proprietà importate vs gestite
   - Utente fa matching manuale
   - Salva mappings in `propertyMappings/`

### Flusso 2: Import Prenotazione da Email

1. **Gmail Watch** notifica nuova email
2. **Email Agent Service** riceve notifica Pub/Sub
3. **Gmail API** recupera email
4. **Parser** identifica tipo (Booking/Airbnb/Scidoo)
5. **Estrae dati**: reservationId, propertyName, guestName, dates, amount
6. **PersistenceService**:
   - Trova/crea property in `properties/`
   - Trova/crea client in `clients/`
   - Crea/aggiorna reservation in `reservations/`
7. **Linking**: Collega reservation → propertyId, clientId
8. **Frontend**: Aggiorna in real-time via Firestore listeners

### Flusso 3: Messaggio Ospite → AI Reply

1. **Ospite** invia messaggio via Booking/Airbnb
2. **Gmail Watch** notifica nuova email
3. **Email Agent Service** processa email
4. **Parser** identifica come messaggio guest (non conferma)
5. **Guest Message Pipeline**:
   - Estrae reservationId/threadId
   - Trova client in Firestore
   - Verifica `autoReplyEnabled`
   - Se true, procede
6. **GeminiService**:
   - Costruisce prompt con contesto property + prenotazione
   - Chiama Gemini API
   - Riceve risposta AI
7. **Gmail Send**: Invia risposta via Gmail API
8. **Salvataggio**: Salva in `gioviAiChatDataset/`

### Flusso 4: Creazione Lavoro Pulizia

1. **Email Agent Service** importa nuova prenotazione
2. **PersistenceService** salva reservation
3. **Job Creation** (opzionale):
   - Calcola data pulizia (check-out day)
   - Crea `cleaningJob/` con `source: "email_agent"`
   - Collega a `reservationId` e `propertyId`
4. **Agency Service** vede nuovo job pending
5. **Planning**: Genera piano giornaliero con VRP
6. **Assegnazione**: Assegna job a staff con skills richieste
7. **Route Optimization**: Calcola percorso ottimizzato
8. **Frontend Agency**: Mostra job assegnato a staff

### Flusso 5: Onboarding Cleaning Agency

1. **Registrazione**: Utente si registra con ruolo `cleaning_agency`
2. **Creazione Agency**: Firestore crea `cleaningAgencies/{uid}`
3. **Redirect**: Frontend redirecta a `/agency`
4. **Setup Staff**: 
   - Crea operatori in `/agency/staff`
   - Assegna competenze
   - Imposta disponibilità
5. **Collegamento Host** (opzionale):
   - Property manager collega agenzia
   - Jobs vengono creati automaticamente da prenotazioni
6. **Planning**: Genera piani giornalieri ottimizzati

---

## Stack Tecnologico

### Frontend
- **React** 18.3.1
- **TypeScript** 5.5.3
- **Vite** 5.4.1
- **React Router** 6.26.2
- **TanStack Query** 5.90.7
- **Firebase SDK** 10.13.1
- **Tailwind CSS** 3.4.11
- **Radix UI** + shadcn/ui
- **date-fns** 3.6.0
- **Zod** 3.23.8

### Backend - Email Agent Service
- **Python** 3.9+
- **FastAPI** 0.115+
- **Firebase Admin SDK** 6.5.0
- **Google Cloud Firestore** 2.16.0
- **Google API Python Client** 2.187.0
- **BeautifulSoup4** 4.14.2
- **Cryptography (Fernet)** per cifratura
- **Pydantic** per validazione
- **Uvicorn** come ASGI server

### Backend - Agency Service
- **Python** 3.11+
- **FastAPI** 0.115+
- **Firebase Admin SDK**
- **Pydantic** 2.8.0
- **Uvicorn**

### Database & Infrastructure
- **Firestore** (NoSQL database)
- **Firebase Auth** (autenticazione)
- **Firebase Cloud Functions** (serverless)
- **Google Cloud Run** (deploy servizi)
- **Google Cloud Pub/Sub** (notifiche Gmail)
- **Google Secret Manager** (credenziali)

### External APIs
- **Gmail API** (Google)
- **Gemini AI API** (Google)
- **Scidoo API** (PMS)
- **Smoobu API** (PMS)
- **Booking.com Messaging API**

---

## Ruoli e Permessi

### 1. Property Manager (host)
- **Ruolo**: `property_manager` o `host`
- **Accesso**: Tutte le pagine tranne `/agency/*`
- **Permessi Firestore**:
  - Read/Write su `properties/` dove `hostId == uid`
  - Read/Write su `reservations/` dove `hostId == uid`
  - Read/Write su `clients/` dove `assignedHostId == uid`
  - Read/Write su `hostEmailIntegrations/` dove `hostId == uid`
- **Funzionalità**:
  - Gestione proprietà
  - Visualizzazione prenotazioni
  - Chat con clienti
  - Configurazione integrazioni
  - Toggle auto-reply per clienti

### 2. Cleaning Agency
- **Ruolo**: `cleaning_agency`
- **Accesso**: Solo `/agency/*` routes
- **Permessi Firestore**:
  - Read/Write su `cleaningAgencies/{uid}`
  - Read/Write su `cleaningStaff/` dove `agencyId == uid`
  - Read/Write su `cleaningJobs/` dove `agencyId == uid`
  - Read/Write su `cleaningPlans/` dove `agencyId == uid`
  - Read su `properties/` (solo per jobs)
- **Funzionalità**:
  - Gestione staff
  - Gestione jobs
  - Generazione piani
  - Visualizzazione rotte

### 3. Test User
- **Ruolo**: `test_user`
- **Accesso**: `/test` per testing
- **Permessi**: Limitati a dati di test
- **Funzionalità**: Creazione dati mock per testing

### Sicurezza

- **Firebase Security Rules**: Regole Firestore per isolamento dati
- **CORS**: Configurato su backend per origini specifiche
- **Token Encryption**: Token OAuth cifrati con Fernet
- **API Keys**: Gestite via Secret Manager o env vars
- **Authentication**: Firebase Auth con email/password
- **Authorization**: Header `X-Agency-Id` per Agency Service

---

## Note Finali

### Stato Implementazione

**Completato**:
- ✅ OAuth Gmail e backfill email
- ✅ Parsing email Booking/Airbnb/Scidoo
- ✅ Persistenza automatica in Firestore
- ✅ Integrazioni Scidoo e Smoobu
- ✅ UI Property Manager completa
- ✅ UI Cleaning Agency completa
- ✅ AI Reply con Gemini (parziale)

**In Sviluppo**:
- ⏳ Gmail Watch real-time
- ⏳ Pipeline completa AI Reply
- ⏳ VRP algorithm per ottimizzazione rotte
- ⏳ Booking.com Messaging API integration

### Deployment

- **Frontend**: Firebase Hosting
- **Email Agent Service**: Google Cloud Run (porta 8000)
- **Agency Service**: Google Cloud Run (porta 8050)
- **Cloud Functions**: Firebase Functions (europe-west1)

### Variabili Ambiente Principali

**Frontend** (`giovi-ai/giovi/frontend/giovi-ai-working-app/.env.local`):
- `VITE_FIREBASE_API_KEY` - Firebase Web App API key
- `VITE_FIREBASE_AUTH_DOMAIN` - Firebase Auth domain
- `VITE_FIREBASE_PROJECT_ID` - Firebase project ID
- `VITE_FIREBASE_STORAGE_BUCKET` - Firebase Storage bucket
- `VITE_FIREBASE_MESSAGING_SENDER_ID` - Firebase messaging sender ID
- `VITE_FIREBASE_APP_ID` - Firebase app ID
- `VITE_EMAIL_AGENT_SERVICE_URL` - URL Email Agent Service (default: Cloud Run URL)
- `VITE_AGENCY_API_BASE` - URL Agency Service (default: http://localhost:8050/api)
- `VITE_FIREBASE_FUNCTIONS_REGION` - Cloud Functions region (default: europe-west1)

**Email Agent Service** (`.env` o Cloud Run env vars):
- `TOKEN_ENCRYPTION_KEY` - Chiave Fernet per cifratura token (32 bytes base64)
- `GOOGLE_OAUTH_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_OAUTH_CLIENT_SECRET` - Google OAuth client secret
- `GOOGLE_OAUTH_REDIRECT_URI` - OAuth redirect URI
- `FIREBASE_PROJECT_ID` - Firebase project ID
- `FIREBASE_CREDENTIALS_PATH` - Path a service account JSON
- `GEMINI_API_KEY` - Google Gemini API key
- `GOOGLE_APPLICATION_CREDENTIALS` - Path a service account (alternativa a FIREBASE_CREDENTIALS_PATH)

**Agency Service** (`.env` o Cloud Run env vars):
- `AGENCY_FIREBASE_PROJECT_ID` - Firebase project ID (opzionale, usa quello del service account se non specificato)
- `AGENCY_DEFAULT_PLAN_VERSION` - Versione algoritmo planning (default: "simple")
- `AGENCY_ALLOWED_ORIGINS` - CORS allowed origins (comma-separated)
- `GOOGLE_APPLICATION_CREDENTIALS` - Path a service account JSON

### API Endpoints Summary

#### Email Agent Service (Port 8000)
- **Health**: `GET /health/live`, `GET /health/ready`
- **Gmail OAuth**: `POST /integrations/gmail/start`, `POST /integrations/gmail/callback`
- **Gmail Backfill**: `POST /integrations/gmail/{email}/backfill`
- **Gmail Watch**: `POST /integrations/gmail/{email}/watch`
- **Scidoo**: `POST /integrations/scidoo/{host_id}/configure`, `POST /integrations/scidoo/{host_id}/sync`
- **Smoobu**: `POST /integrations/smoobu/webhook`, `POST /integrations/smoobu/import`
- **Property Mappings**: `GET /property-mappings/hosts/{host_id}/property-match`
- **Clients**: `PATCH /clients/{client_id}/auto-reply`

#### Agency Service (Port 8050)
- **Health**: `GET /health`
- **Stats**: `GET /api/stats`
- **Staff**: `GET /api/staff`, `POST /api/staff`, `PATCH /api/staff/{staff_id}`
- **Jobs**: `GET /api/jobs`, `POST /api/jobs`, `PATCH /api/jobs/{job_id}`
- **Plans**: `GET /api/plans`, `POST /api/plans/generate`
- **Routes**: `GET /api/routes`
- **Skills**: `GET /api/skills`, `POST /api/skills`

### UI Components Principali

#### Property Manager UI
- **Dashboard**: Cards con KPI, grafici occupazione, ultime prenotazioni
- **Alloggi List**: Grid di PropertyCard con filtri e search
- **Alloggi Detail**: Tabs per info base, accesso, check-in/out, pulizia, emergenze, parcheggio, zona
- **Clienti**: Split view con lista prenotazioni a sinistra, chat a destra
- **Calendario**: Vista settimanale con navigazione, colori per proprietà
- **Impostazioni**: Cards per integrazioni Gmail e PMS, property matching

#### Cleaning Agency UI
- **Agency Dashboard**: KPI cards, pending jobs, available staff
- **Staff Management**: Table con CRUD, filtri per status, skills
- **Jobs Management**: Table con filtri status/date, creazione manuale
- **Planning**: Form per generazione piano, visualizzazione assegnazioni
- **Routes Board**: Mappa o lista percorsi con stops geolocalizzati
- **Skills Catalog**: Lista competenze con creazione/modifica

### Caratteristiche UI/UX

- **Design System**: shadcn/ui components con Tailwind CSS
- **Dark Mode**: Supporto tema scuro via next-themes
- **Responsive**: Mobile-first, breakpoints Tailwind
- **Loading States**: Skeleton loaders, spinners
- **Error Handling**: Toast notifications, error boundaries
- **Form Validation**: Zod schemas con react-hook-form
- **Real-time Updates**: Firestore onSnapshot listeners
- **Optimistic Updates**: React Query con cache invalidation

---

## Appendice: File Chiave del Progetto

### Frontend - File Importanti
- `src/App.tsx` - Router principale e route configuration
- `src/providers/AuthProvider.tsx` - Context autenticazione Firebase
- `src/hooks/useAuth.ts` - Hook per accesso utente e profilo
- `src/services/firestore/*.ts` - Client Firestore e custom hooks
- `src/services/api/agency.ts` - Client API Agency Service
- `src/pages/Impostazioni.tsx` - Configurazione integrazioni
- `src/components/settings/GmailIntegrationCard.tsx` - UI integrazione Gmail
- `src/components/settings/PmsIntegrationCard.tsx` - UI integrazioni PMS

### Email Agent Service - File Importanti
- `src/email_agent_service/app.py` - FastAPI app factory
- `src/email_agent_service/api/routes/integrations.py` - Endpoint Gmail/Scidoo/Smoobu
- `src/email_agent_service/services/backfill_service.py` - Logica import email
- `src/email_agent_service/services/persistence_service.py` - Salvataggio Firestore
- `src/email_agent_service/parsers/engine.py` - Email parsing engine
- `src/email_agent_service/services/gemini_service.py` - AI reply generation
- `src/email_agent_service/repositories/*.py` - Repository pattern per Firestore

### Agency Service - File Importanti
- `src/agency_service/routes/*.py` - Endpoint API modulari
- `src/agency_service/services/planning.py` - VRP planning engine
- `src/agency_service/models.py` - Pydantic models
- `src/agency_service/firestore.py` - Firestore client helper

---

**Fine Documentazione**

*Questo documento fornisce una panoramica completa del sistema Giovi AI, inclusa architettura, funzionalità, API, database, integrazioni e flussi utente. Può essere utilizzato come riferimento per la costruzione del sito web pubblico o per onboarding di nuovi sviluppatori.*

