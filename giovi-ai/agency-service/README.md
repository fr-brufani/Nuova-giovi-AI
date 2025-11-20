# Agency Service

Servizio FastAPI che espone le API per il nuovo portale dedicato alle agenzie di pulizie. Condivide lo stesso progetto Firebase/Firestore del resto della piattaforma e fornisce endpoint per:

- KPI di dashboard (staff attivo, lavori del giorno, percorsi, completati).
- Gestione staff e relative competenze.
- CRUD dei lavori di pulizia provenienti dal `email-agent-service` o inseriti manualmente.
- Generazione del piano giornaliero e delle rotte ottimizzate (placeholder VRP).
- Catalogo competenze specifico per ogni agenzia.

## Requisiti

- Python 3.11+
- Stesso progetto Firebase/Firestore già usato dal resto di Giovi AI. Basta puntare alle stesse credenziali service account (`GOOGLE_APPLICATION_CREDENTIALS` o `FIREBASE_CREDENTIALS_PATH`). Se `AGENCY_FIREBASE_PROJECT_ID` non è impostato, il client riutilizza il project ID presente nelle credenziali.
- Variabili d'ambiente principali (vedi `.env.example`):
  - `AGENCY_FIREBASE_PROJECT_ID` *(opzionale)* — forza un project specifico solo se necessario.
  - `AGENCY_DEFAULT_PLAN_VERSION`
  - `AGENCY_ALLOWED_ORIGINS`

## Setup locale

```bash
cd giovi-ai/agency-service
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env  # aggiorna con i valori reali
uvicorn main:app --reload --port 8050
```

## Struttura

```
agency-service/
 ├── main.py                  # entrypoint FastAPI
 ├── src/agency_service
 │   ├── config.py            # gestione settings/env
 │   ├── firestore.py         # helper per Firestore
 │   ├── models.py            # schemi Pydantic condivisi
 │   ├── services/planning.py # motore di pianificazione placeholder
 │   └── routes/              # router modulari (stats, staff, jobs, plans, skills)
 └── tests/                   # test API e servizi
```

## Convenzioni

- Tutti gli endpoint richiedono l'header `X-Agency-Id` (UID Firebase del tenant).
- I timestamp vengono serializzati in ISO8601 UTC.
- Le operazioni scrivono sempre anche `updatedAt` per semplificare la sincronizzazione lato frontend.

## Integrazione con altri servizi

- `email-agent-service` pubblica i lavori pulizia su `cleaningJobs`.
- Il worker di pianificazione in questo servizio aggiorna `cleaningPlans` e `cleaningRoutes`.
- Il frontend accede agli endpoint tramite `VITE_AGENCY_API_BASE`.

## TODO

- Integrare algoritmo VRP definitivo (es. Google OR-Tools).
- Scheduler periodico per refresh dei piani.
- Telemetria e metriche dettagliate.

