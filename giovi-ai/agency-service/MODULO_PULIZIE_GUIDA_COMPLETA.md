# 🧽 Modulo Agenzie di Pulizie - Guida Completa

**Data:** 20 Novembre 2025  
**Versione:** 0.1.0 (MVP)

---

## 📋 Indice

1. [Panoramica](#panoramica)
2. [Architettura](#architettura)
3. [Backend - Agency Service](#backend---agency-service)
4. [Frontend - UI Agenzie](#frontend---ui-agenzie)
5. [Modelli Dati Firestore](#modelli-dati-firestore)
6. [Flussi Utente](#flussi-utente)
7. [API Endpoints](#api-endpoints)
8. [Setup e Deploy](#setup-e-deploy)
9. [Testing](#testing)
10. [Prossimi Sviluppi](#prossimi-sviluppi)

---

## Panoramica

Il **Modulo Agenzie di Pulizie** è un sistema dedicato che permette alle agenzie partner di gestire operativamente:
- **Staff** (operatori e loro competenze)
- **Lavori** (pulizie programmate, in corso, completate)
- **Pianificazione** (generazione automatica di piani giornalieri ottimizzati)
- **Percorsi** (rotte geolocalizzate per minimizzare tempi e distanze)
- **Competenze** (catalogo skill richieste e certificate)

### Caratteristiche Chiave

- ✅ **Separazione ruoli**: Property Manager vedono la UI standard, Agenzie vedono `/agency/*`
- ✅ **Stesso database**: Condivide Firestore con il resto della piattaforma
- ✅ **Stack unificato**: React + FastAPI + Firebase (come email-agent-service)
- ✅ **Sicurezza**: Guardie di ruolo lato frontend + regole Firestore isolate per `agencyId`

---

## Architettura

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                          │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │ Property Manager │         │ Cleaning Agency  │         │
│  │   UI Standard    │         │   UI /agency/*    │         │
│  └──────────────────┘         └──────────────────┘         │
│         │                              │                     │
│         └──────────────┬──────────────┘                     │
│                        │                                      │
│                        ▼                                      │
│              ┌─────────────────┐                             │
│              │  React Router   │                             │
│              │  Role Guards    │                             │
│              └─────────────────┘                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTP (X-Agency-Id header)
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Agency Service (FastAPI)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Stats   │  │  Staff   │  │  Jobs    │  │  Plans   │ │
│  │  Routes  │  │  Skills  │  │          │  │          │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Firebase Admin SDK
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Firestore                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ cleaningAgencies/{agencyId}                          │   │
│  │ cleaningStaff/{staffId}                             │   │
│  │ cleaningJobs/{jobId}                                 │   │
│  │ cleaningPlans/{planId}                               │   │
│  │ cleaningRoutes/{routeId}                             │   │
│  │ cleaningSkills/{skillId}                             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ properties/{propertyId}  (condiviso)                │   │
│  │ reservations/{reservationId}  (condiviso)            │   │
│  │ hosts/{hostId}  (condiviso)                          │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## Backend - Agency Service

### Struttura Progetto

```
giovi-ai/agency-service/
├── main.py                          # Entry point FastAPI
├── pyproject.toml                   # Dipendenze Python
├── README.md                        # Setup e istruzioni
├── src/
│   └── agency_service/
│       ├── __init__.py
│       ├── config.py                # Settings (Firebase, CORS, ecc.)
│       ├── firestore.py             # Client Firestore helper
│       ├── models.py                # Pydantic models (Staff, Job, Plan, ecc.)
│       ├── services/
│       │   └── planning.py          # Motore pianificazione (placeholder VRP)
│       └── routes/
│           ├── __init__.py         # Router principale
│           ├── dependencies.py     # require_agency_id() guard
│           ├── stats.py             # GET /api/stats
│           ├── staff.py             # GET/POST/PATCH /api/staff
│           ├── jobs.py              # GET/POST/PATCH /api/jobs
│           ├── plans.py             # GET/POST /api/plans
│           ├── routes_board.py      # GET /api/routes
│           └── skills.py             # GET/POST /api/skills
└── tests/
    └── test_health.py               # Test health check
```

### Configurazione

Il servizio legge variabili d'ambiente da `.env`:

```bash
# Opzionale: se non impostato usa il project del service account Google
AGENCY_FIREBASE_PROJECT_ID=your-project-id

# Credenziali Firebase (stesso service account degli altri servizi)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# CORS (default: *)
AGENCY_ALLOWED_ORIGINS=http://localhost:8080,https://yourdomain.com

# Versione algoritmo pianificazione (default: "simple")
AGENCY_DEFAULT_PLAN_VERSION=simple
```

**Nota importante**: Se `AGENCY_FIREBASE_PROJECT_ID` non è impostato, il client Firestore usa automaticamente il project definito nel service account JSON. Questo permette di condividere lo stesso database senza configurazione aggiuntiva.

### Autenticazione e Sicurezza

Tutti gli endpoint richiedono l'header `X-Agency-Id` che identifica l'agenzia. Il middleware `require_agency_id()` in `routes/dependencies.py`:

1. Estrae `X-Agency-Id` dall'header
2. Verifica che esista un documento `cleaningAgencies/{agencyId}`
3. Inietta `agency_id` come dependency nei route handlers

**Esempio**:
```python
@router.get("/staff")
def list_staff(agency_id: str = Depends(require_agency_id)):
    # agency_id è garantito valido e autorizzato
    docs = client.collection("cleaningStaff").where("agencyId", "==", agency_id).stream()
    return [serialize_document(doc) for doc in docs]
```

### Modelli Pydantic

I modelli in `src/agency_service/models.py` definiscono:

- **StaffBase/StaffCreate/StaffUpdate/StaffResponse**: Operatori
- **JobBase/JobCreate/JobUpdate/JobResponse**: Lavori di pulizia
- **PlanBase/PlanCreate/PlanResponse**: Piani giornalieri
- **RouteBase/RouteResponse**: Percorsi ottimizzati
- **SkillBase/SkillCreate/SkillResponse**: Competenze

Tutti i modelli includono validazione automatica e serializzazione per Firestore.

---

## Frontend - UI Agenzie

### Struttura Progetto

```
giovi-ai/giovi/frontend/giovi-ai-working-app/src/
├── pages/
│   └── agency/
│       ├── AgencyLayout.tsx        # Layout con sidebar + guardia ruolo
│       ├── Dashboard.tsx            # Dashboard con KPI
│       ├── Staff.tsx                # CRUD operatori
│       ├── Jobs.tsx                 # Lista lavori (pending/in corso/completati)
│       ├── Planning.tsx             # Generazione piano giornaliero
│       ├── Routes.tsx               # Visualizzazione percorsi
│       └── Skills.tsx                # Catalogo competenze
├── components/
│   └── agency/
│       ├── AgencySidebar.tsx        # Sidebar navigazione + logout
│       └── AgencyDashboard.tsx       # Componente dashboard riutilizzabile
└── services/
    └── api/
        └── agency.ts                 # Client API centralizzato
```

### Routing e Guardie

In `App.tsx`:

```tsx
<Route path="/agency" element={<AgencyLayout />}>
  <Route index element={<Dashboard />} />
  <Route path="staff" element={<Staff />} />
  <Route path="jobs" element={<Jobs />} />
  <Route path="planning" element={<Planning />} />
  <Route path="routes" element={<Routes />} />
  <Route path="skills" element={<Skills />} />
</Route>
```

`AgencyLayout.tsx` implementa la guardia di ruolo:

```tsx
if (role !== 'cleaning_agency') {
  return <Navigate to="/" replace />;
}
```

Se l'utente non è un'agenzia, viene reindirizzato alla UI standard.

### Client API

Il file `services/api/agency.ts` centralizza tutte le chiamate al backend:

```typescript
const API_BASE = import.meta.env.VITE_AGENCY_API_BASE ?? 'http://localhost:8050/api';

async function request<T>(path: string, agencyId: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  headers.set('X-Agency-Id', agencyId);
  // ... fetch logic
}

export const agencyApi = {
  getStats: (agencyId: string) => request<AgencyStats>('/stats', agencyId),
  listStaff: (agencyId: string) => request<AgencyStaff[]>('/staff', agencyId),
  createStaff: (agencyId: string, payload: Partial<AgencyStaff>) => ...,
  // ... altri metodi
};
```

**Nota**: `agencyId` viene estratto da `useAuth().profile.id` (coincide con l'UID Firebase dell'utente agenzia).

### React Query Hooks

Ogni pagina usa React Query per gestire stato e cache:

```tsx
const { data: stats, isLoading } = useQuery({
  queryKey: ['agency-stats', user?.id],
  queryFn: () => agencyApi.getStats(user!.id),
  enabled: !!user,
});
```

---

## Modelli Dati Firestore

### Collection: `cleaningAgencies/{agencyId}`

**Path**: `cleaningAgencies/{agencyId}` (dove `agencyId` = UID Firebase dell'utente)

**Campi**:
- `agencyId` (string) - UID Firebase
- `hostId` (string | null) - Property manager collegato (opzionale)
- `displayName` (string) - Nome agenzia
- `email` (string)
- `phone` (string)
- `baseLocation` (map) - `{ address, city, country, lat, lng }`
- `skillsOffered` (array<string>) - Competenze offerte
- `defaultShiftStart` / `defaultShiftEnd` (string HH:mm)
- `schemaVersion` (number, default 1)
- `createdAt` / `updatedAt` (Timestamp)

**Query tipica**: `cleaningAgencies.where("agencyId", "==", uid)`

---

### Collection: `cleaningStaff/{staffId}`

**Path**: `cleaningStaff/{staffId}`

**Campi**:
- `agencyId` (string) - Riferimento agenzia
- `displayName` (string)
- `email` (string)
- `phone` (string)
- `status` (string) - `active | inactive | invited`
- `skills` (array<string>) - Riferimenti a `cleaningSkills`
- `homeBase` (map) - `{ lat, lng }` - Posizione base per calcolo rotte
- `availability` (map) - Es: `{ monday: ['08:00-12:00', '15:00-18:00'] }`
- `lastAssignmentAt` (Timestamp | null)
- `createdAt` / `updatedAt` (Timestamp)

**Indice consigliato**: `(agencyId ASC, status ASC)`

**Query tipica**: `cleaningStaff.where("agencyId", "==", agencyId).where("status", "==", "active")`

---

### Collection: `cleaningJobs/{jobId}`

**Path**: `cleaningJobs/{jobId}`

**Campi**:
- `agencyId` (string)
- `hostId` (string) - Property manager che ha richiesto il lavoro
- `propertyId` (string) - Riferimento a `properties/{propertyId}`
- `reservationId` (string | null) - Riferimento a `reservations/{reservationId}` (se collegato a prenotazione)
- `status` (string) - `pending | scheduled | in_progress | completed | cancelled`
- `scheduledDate` (string YYYY-MM-DD)
- `plannedStart` / `plannedEnd` (Timestamp) - Orari pianificati
- `actualStart` / `actualEnd` (Timestamp) - Orari effettivi (timbrature)
- `estimatedDurationMinutes` (number) - Calcolato automaticamente da caratteristiche property
- `skillsRequired` (array<string>) - Competenze richieste
- `notes` (string)
- `source` (string) - `email_agent | manual | sync` - Fonte del lavoro
- `planId` (string | null) - Riferimento a `cleaningPlans/{planId}` se incluso in un piano
- `createdAt` / `updatedAt` (Timestamp)

**Indice consigliato**: `(agencyId ASC, scheduledDate DESC, status ASC)`

**Query tipica**: `cleaningJobs.where("agencyId", "==", agencyId).where("scheduledDate", "==", today).where("status", "==", "pending")`

---

### Collection: `cleaningPlans/{planId}`

**Path**: `cleaningPlans/{planId}`

**Campi**:
- `agencyId` (string)
- `date` (string YYYY-MM-DD) - Data del piano
- `status` (string) - `draft | processing | ready | published`
- `solverVersion` (string) - Versione algoritmo usato (es: "simple", "vrp-v1")
- `inputJobs` (array<string>) - Lista `jobId` in input
- `assignments` (array<map>) - `[{ jobId, staffId, startTime, endTime, travelMinutes }]`
- `metrics` (map) - `{ totalDistanceKm, utilisation, totalTravelTimeMinutes }`
- `createdAt` / `updatedAt` (Timestamp)

**Subcollections**:
- `cleaningPlans/{planId}/events/{eventId}` - Log di generazione piano

**Query tipica**: `cleaningPlans.where("agencyId", "==", agencyId).where("date", "==", today).order_by("createdAt", direction=firestore.Query.DESCENDING)`

---

### Collection: `cleaningRoutes/{routeId}`

**Path**: `cleaningRoutes/{routeId}`

**Campi**:
- `agencyId` (string)
- `planId` (string) - Riferimento a `cleaningPlans/{planId}`
- `staffId` (string) - Riferimento a `cleaningStaff/{staffId}`
- `date` (string YYYY-MM-DD)
- `stops` (array<map>) - `[{ jobId, propertyId, eta, lat, lng }]` - Ordine ottimizzato
- `distanceKm` (number) - Distanza totale stimata
- `travelTimeMinutes` (number) - Tempo viaggio totale
- `generatedAt` (Timestamp)

**Query tipica**: `cleaningRoutes.where("agencyId", "==", agencyId).where("date", "==", today)`

---

### Collection: `cleaningSkills/{skillId}`

**Path**: `cleaningSkills/{skillId}`

**Campi**:
- `agencyId` (string | null) - `null` per skill globali (condivise tra tutte le agenzie)
- `name` (string) - Es: "Pulizia Standard", "Lavanderia", "Sanificazione Certificata"
- `description` (string)
- `icon` (string) - Nome icona (es: "ribbon", "sparkles")
- `createdAt` / `updatedAt` (Timestamp)

**Query tipica**: 
- Skill globali: `cleaningSkills.where("agencyId", "==", null)`
- Skill agenzia: `cleaningSkills.where("agencyId", "==", agencyId)`

---

## Flussi Utente

### 1. Registrazione e Login

1. Utente si registra su `/auth` selezionando ruolo **"Agenzia di Pulizie"**
2. `AuthProvider` crea documento `hosts/{uid}` con `role: "cleaning_agency"`
3. Utente viene automaticamente creato anche in `cleaningAgencies/{uid}` (se non esiste)
4. Dopo login, `Index.tsx` verifica il ruolo:
   - Se `role === 'cleaning_agency'` → redirect a `/agency`
   - Altrimenti → mostra `Dashboard` standard

### 2. Dashboard Agenzia

**Percorso**: `/agency` (index route)

**Cosa mostra**:
- **4 KPI card**:
  - Staff Attivo (operatori disponibili oggi)
  - Lavori Oggi (interventi programmati)
  - Percorsi Ottimizzati (rotte generate oggi)
  - Completati (interventi completati)
- **Lavori in Attesa**: Lista lavori con `status: "pending"` da assegnare
- **Staff Disponibile**: Lista operatori con `status: "active"` e disponibilità oggi

**API chiamate**:
- `GET /api/stats` → KPI aggregati
- `GET /api/jobs?status=pending` → Lavori in attesa
- `GET /api/staff?status=active` → Staff disponibile

### 3. Gestione Staff

**Percorso**: `/agency/staff`

**Funzionalità**:
- **Lista operatori**: Tabella con nome, email, telefono, competenze, stato
- **Aggiungi operatore**: Form modale con campi (nome, email, telefono, competenze selezionabili)
- **Modifica operatore**: Edit inline o modale
- **Filtri**: Per stato (active/inactive), competenze

**API chiamate**:
- `GET /api/staff` → Lista completa
- `POST /api/staff` → Crea nuovo operatore
- `PATCH /api/staff/{staffId}` → Aggiorna operatore

### 4. Gestione Lavori

**Percorso**: `/agency/jobs`

**Funzionalità**:
- **Card riepilogo**: In Attesa, In Corso, Completati Oggi (contatori)
- **Lista lavori**: Tabella con property, data, orario, stato, competenze richieste
- **Filtri**: Per stato, data, property
- **Dettaglio lavoro**: Modale con info complete (property, reservation, note, timbrature)

**API chiamate**:
- `GET /api/jobs?status=pending` → Lavori in attesa
- `GET /api/jobs?status=in_progress` → Lavori in corso
- `GET /api/jobs?status=completed&scheduledDate={today}` → Completati oggi
- `POST /api/jobs` → Crea lavoro manuale
- `PATCH /api/jobs/{jobId}` → Aggiorna stato/note

### 5. Pianificazione

**Percorso**: `/agency/planning`

**Funzionalità**:
- **Genera Piano Giornaliero**: Bottone che triggera `POST /api/plans/generate`
- **Timeline assegnazioni**: Visualizzazione del piano generato con assegnazioni staff → lavori
- **Stato piano**: Draft, Processing, Ready, Published

**Flusso generazione piano**:
1. Utente clicca "Genera Piano Giornaliero" selezionando una data
2. Frontend chiama `POST /api/plans/generate` con `{ agencyId, date }`
3. Backend:
   - Recupera tutti i lavori `pending` per quella data
   - Recupera staff `active` con disponibilità
   - Esegue algoritmo VRP semplificato (placeholder)
   - Crea documento `cleaningPlans/{planId}` con `status: "ready"`
   - Crea assegnazioni `cleaningRoutes/{routeId}` per ogni operatore
4. Frontend mostra piano generato con assegnazioni

**API chiamate**:
- `GET /api/plans?date={date}` → Piano esistente per data
- `POST /api/plans/generate` → Genera nuovo piano

### 6. Percorsi Ottimizzati

**Percorso**: `/agency/routes`

**Funzionalità**:
- **Lista percorsi**: Per ogni operatore, mostra rotta ottimizzata con stops ordinati
- **Dettaglio percorso**: Mappa (futura) o lista con ETA, distanza, tempo viaggio
- **Export**: (Futuro) Export PDF o CSV per operatore

**API chiamate**:
- `GET /api/routes?date={date}` → Percorsi per data

### 7. Competenze

**Percorso**: `/agency/skills`

**Funzionalità**:
- **Catalogo competenze**: Grid di card con icona, nome, descrizione
- **Skill globali**: Competenze condivise (es: "Pulizia Standard", "Lavanderia")
- **Skill agenzia**: Competenze custom dell'agenzia
- **Aggiungi competenza**: Form per creare nuova skill

**API chiamate**:
- `GET /api/skills` → Lista competenze (globali + agenzia)
- `POST /api/skills` → Crea nuova skill

---

## API Endpoints

### Base URL

- **Locale**: `http://localhost:8050/api`
- **Produzione**: (da configurare in Cloud Run o simile)

### Autenticazione

Tutti gli endpoint richiedono header:
```
X-Agency-Id: {agencyId}
```

### Endpoints Disponibili

#### Stats

**GET** `/api/stats`

Risposta:
```json
{
  "staff_active": 5,
  "jobs_today": 12,
  "routes_optimized": 3,
  "jobs_completed": 8
}
```

---

#### Staff

**GET** `/api/staff`

Risposta: Array di `StaffResponse`

**POST** `/api/staff`

Body:
```json
{
  "displayName": "Mario Rossi",
  "email": "mario@example.com",
  "phone": "+39 123 456 7890",
  "status": "active",
  "skills": ["skill-id-1", "skill-id-2"]
}
```

**PATCH** `/api/staff/{staffId}`

Body: (stessi campi di POST, tutti opzionali)

---

#### Jobs

**GET** `/api/jobs?status={status}&scheduledDate={date}`

Query params:
- `status` (opzionale): `pending | scheduled | in_progress | completed | cancelled`
- `scheduledDate` (opzionale): `YYYY-MM-DD`

Risposta: Array di `JobResponse`

**POST** `/api/jobs`

Body:
```json
{
  "propertyId": "prop-123",
  "hostId": "host-456",
  "scheduledDate": "2025-11-21",
  "estimatedDurationMinutes": 120,
  "skillsRequired": ["skill-id-1"],
  "notes": "Check-out alle 11:00"
}
```

**PATCH** `/api/jobs/{jobId}`

Body: (campi opzionali per aggiornare)

---

#### Plans

**GET** `/api/plans?date={date}`

Query params:
- `date` (opzionale): `YYYY-MM-DD` (default: oggi)

Risposta: Array di `PlanResponse`

**POST** `/api/plans/generate`

Body:
```json
{
  "agencyId": "agency-123",
  "date": "2025-11-21"
}
```

Risposta: `PlanResponse` con `status: "ready"` e `assignments` popolati

---

#### Routes

**GET** `/api/routes?date={date}`

Query params:
- `date` (opzionale): `YYYY-MM-DD` (default: oggi)

Risposta: Array di `RouteResponse`

---

#### Skills

**GET** `/api/skills`

Risposta: Array di `SkillResponse` (globali + agenzia)

**POST** `/api/skills`

Body:
```json
{
  "name": "Sanificazione Certificata",
  "description": "Pulizia con prodotti certificati COVID-19",
  "icon": "shield-check"
}
```

---

## Setup e Deploy

### Setup Locale

#### 1. Backend (Agency Service)

```bash
cd giovi-ai/agency-service

# Crea .env
cat > .env << EOF
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
AGENCY_ALLOWED_ORIGINS=http://localhost:8080
AGENCY_DEFAULT_PLAN_VERSION=simple
EOF

# Installa dipendenze (se non già fatto)
python3 -m pip install -e '.[dev]'

# Avvia server
uvicorn main:app --reload --port 8050
```

Il server sarà disponibile su `http://localhost:8050`

#### 2. Frontend

```bash
cd giovi-ai/giovi/frontend/giovi-ai-working-app

# Crea .env.local (se non esiste)
cat > .env.local << EOF
VITE_FIREBASE_API_KEY=your-key
VITE_FIREBASE_AUTH_DOMAIN=your-domain.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-bucket.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
VITE_FIREBASE_APP_ID=your-app-id
VITE_AGENCY_API_BASE=http://localhost:8050/api
EOF

# Installa dipendenze
npm install

# Avvia dev server (porta 8080)
npm run dev
```

Il frontend sarà disponibile su `http://localhost:8080`

#### 3. Test Login

1. Vai su `http://localhost:8080/auth`
2. Registra nuovo utente selezionando **"Agenzia di Pulizie"**
3. Dopo login, verrai reindirizzato automaticamente a `/agency`
4. Se vedi la dashboard agenzia, tutto funziona! 🎉

---

### Deploy Produzione

#### Backend (Cloud Run)

```bash
cd giovi-ai/agency-service

# Build Docker image
docker build -t gcr.io/YOUR_PROJECT/agency-service:latest .

# Push to GCR
docker push gcr.io/YOUR_PROJECT/agency-service:latest

# Deploy to Cloud Run
gcloud run deploy agency-service \
  --image gcr.io/YOUR_PROJECT/agency-service:latest \
  --platform managed \
  --region europe-west1 \
  --set-env-vars AGENCY_ALLOWED_ORIGINS=https://yourdomain.com \
  --set-secrets GOOGLE_APPLICATION_CREDENTIALS=service-account:latest
```

#### Frontend (Firebase Hosting)

```bash
cd giovi-ai/giovi/frontend/giovi-ai-working-app

# Build produzione
npm run build

# Deploy su Firebase Hosting
firebase deploy --only hosting
```

**Nota**: Aggiorna `VITE_AGENCY_API_BASE` nel build con l'URL Cloud Run del backend.

---

## Testing

### Test Backend

```bash
cd giovi-ai/agency-service

# Run tests
python3 -m pytest

# Con coverage
python3 -m pytest --cov=agency_service --cov-report=html
```

### Test Frontend

```bash
cd giovi-ai/giovi/frontend/giovi-ai-working-app

# Lint
npm run lint

# Build test
npm run build
```

### Test Manuali End-to-End

1. **Registrazione agenzia**: Crea account con ruolo `cleaning_agency`
2. **Dashboard**: Verifica KPI (dovrebbero essere 0 inizialmente)
3. **Staff**: Aggiungi almeno 2 operatori con competenze
4. **Skills**: Crea alcune competenze (es: "Pulizia Standard", "Lavanderia")
5. **Jobs**: Crea manualmente alcuni lavori per oggi
6. **Planning**: Genera piano giornaliero e verifica assegnazioni
7. **Routes**: Verifica percorsi generati per ogni operatore

---

## Prossimi Sviluppi

### Fase 1 (MVP Completo)

- [ ] **Integrazione email-agent-service**: Hook per creare automaticamente `cleaningJobs` quando arrivano nuove prenotazioni con checkout
- [ ] **Calcolo tempi stimati**: Algoritmo che calcola `estimatedDurationMinutes` basato su metri quadri, numero bagni, tipo pulizia
- [ ] **Algoritmo VRP reale**: Sostituire placeholder con OR-Tools o algoritmo custom che rispetta vincoli temporali (check-out) e competenze

### Fase 2 (Ottimizzazione)

- [ ] **PWA Operatore**: App mobile per timbrature inizio/fine lavoro
- [ ] **Map view percorsi**: Visualizzazione geografica delle rotte su mappa
- [ ] **Notifiche real-time**: Push notifications per nuovi lavori o assegnazioni
- [ ] **Export PDF**: Generazione report giornalieri per operatore

### Fase 3 (Avanzato)

- [ ] **Machine Learning**: Predizione tempi effettivi basata su storico
- [ ] **Multi-agenzia**: Supporto per agenzie che servono più property manager
- [ ] **Integrazione PMS esterni**: Sync automatico con altri sistemi di gestione

---

## Note Tecniche

### Sicurezza Firestore

Le regole Firestore devono essere aggiornate per isolare i dati per `agencyId`:

```javascript
match /cleaningStaff/{staffId} {
  allow read, write: if request.auth != null && 
    resource.data.agencyId == request.auth.uid;
}

match /cleaningJobs/{jobId} {
  allow read, write: if request.auth != null && 
    resource.data.agencyId == request.auth.uid;
}
// ... stesso pattern per altre collezioni
```

### Performance

- **Indici Firestore**: Assicurati di creare indici composti per query frequenti (es: `agencyId + scheduledDate + status`)
- **Paginazione**: Endpoint `GET /api/jobs` e `/api/staff` dovrebbero supportare paginazione per dataset grandi
- **Cache**: React Query cache automaticamente le risposte API per 5 minuti (configurabile)

### Monitoring

- **Logging**: Tutti gli endpoint loggano richieste/errori
- **Telemetria**: (Futuro) Metriche su generazione piani, tempi di risposta, errori

---

**Ultimo Aggiornamento**: 20 Novembre 2025  
**Versione Documento**: 1.0

