# 🏨 giovi_ai - AI Assistant per Gestioni Alberghiere

**giovi_ai** è una piattaforma AI completa per la gestione automatizzata di strutture ricettive, con integrazioni avanzate per i principali sistemi PMS (Property Management System).

## 🎯 **Panoramica del Progetto**

La piattaforma offre:
- 🤖 **Chatbot AI** per assistenza clienti automatizzata
- 🔗 **Integrazioni PMS** real-time con Smoobu e Scidoo  
- 📊 **Dashboard unificato** per gestione proprietà e prenotazioni
- 📱 **App Flutter** multi-piattaforma (Web, iOS, Android)
- ☁️ **Backend Cloud** scalabile su Google Cloud Platform

---

## 🏗️ **Architettura del Sistema**

### **Frontend (Flutter)**
- **Framework:** Flutter 3.x con Dart
- **Piattaforme:** Web, iOS, Android, Desktop
- **Autenticazione:** Firebase Auth
- **Stato:** Provider pattern

### **Backend Services**
- **pms-sync-service:** Gestione integrazioni PMS (Node.js/TypeScript)
- **gemini-proxy-service:** Proxy per Gemini AI
- **workflow-service:** Orchestrazione workflow
- **Firebase Functions:** Servizi serverless

### **Database & Storage**
- **Firebase Firestore:** Database principale NoSQL
- **Firebase Storage:** File e media
- **Cloud Run:** Deploy container services

---

# 🔗 **Integrazioni PMS - Documentazione Tecnica**

## 📊 **Panoramica Integrazioni Supportate**

| PMS | Tipo Integrazione | Status | Sincronizzazione |
|-----|------------------|--------|------------------|
| **Smoobu** | Webhook Real-time | ✅ Produzione | Istantanea |
| **Scidoo** | API Polling | ✅ Implementata | 10-15 minuti |
| **CSV Import** | Upload File | ✅ Disponibile | Manuale |

---

## 🚀 **Integrazione Scidoo - Implementazione Dettagliata**

### **🔍 Analisi Strategica dell'API Scidoo**

**Differenze chiave vs Smoobu:**
- ❌ **Nessun sistema webhook** disponibile
- ✅ **API REST completa** con autenticazione via API-Key
- ✅ **Endpoint `last_modified`** per sincronizzazione ottimizzata
- ✅ **Struttura dati simile** a Smoobu (compatibilità database)

**Strategia adottata:**
- **Import iniziale:** Configurazione one-click come Smoobu
- **Aggiornamenti:** Sistema polling periodico ogni 10-15 minuti
- **Ottimizzazione:** Usa `last_modified=true` per recuperare solo modifiche

### **🛠️ Implementazione Backend (pms-sync-service)**

#### **1. Modelli TypeScript**

```typescript
// Strutture dati complete per API Scidoo v1
interface ScidooAccountInfo {
    name: string;
    email: string;
    account_id: string;
    properties: ScidooProperty[];
}

interface ScidooReservation {
    id: number;                    // ID esterno
    internal_id: number;           // ID interno Scidoo
    checkin_date: string;          // "YYYY-MM-DD"
    checkout_date: string;         // "YYYY-MM-DD"
    status: string;                // Stato prenotazione
    room_type_id: string;          // Categoria alloggio
    guest_count: number;           // Numero ospiti
    customer: ScidooCustomer;      // Dati cliente
    // ... altri campi
}
```

#### **2. Servizio API**

```typescript
class ScidooService {
    private baseUrl = 'https://www.scidoo.com/api/v1';
    
    // Test connessione e recupero account
    async testConnection(apiKey: string): Promise<ScidooAccountInfo>
    
    // Import room types (categorie alloggio → proprietà)
    async getRoomTypes(apiKey: string): Promise<ScidooRoomType[]>
    
    // Import prenotazioni con filtri avanzati
    async getReservations(apiKey: string, params: ScidooGetBookingsRequest): Promise<ScidooReservation[]>
    
    // Sincronizzazione ottimizzata (solo modifiche)
    async getModifiedReservations(apiKey: string): Promise<ScidooReservation[]>
}
```

#### **3. Endpoints REST Implementati**

**Configurazione Automatica:**
```
POST /config/scidoo
- Test API Key con Scidoo
- Import automatico room types → proprietà
- Import prenotazioni recenti (30 giorni)
- Salvataggio configurazione in Firebase
```

**Test Connessione:**
```
POST /config/scidoo/test
- Verifica API Key senza salvare
- Preview proprietà disponibili
- Usato dal frontend per validazione
```

**Stato Integrazione:**
```
GET /config/scidoo/status
- Informazioni account configurato
- Statistiche sincronizzazione
- Timestamp ultima sync
```

**Sincronizzazione Manuale:**
```
POST /config/scidoo/sync-properties  # Sync solo proprietà
POST /config/scidoo/sync-now        # Sync prenotazioni modificate
```

#### **4. Logica di Sincronizzazione**

**Mapping Dati Scidoo → giovi_ai:**

```typescript
async function processScidooReservation(hostId: string, reservation: ScidooReservation) {
    // 1. CLIENTE: Trova/crea usando email
    const { clientId } = await findOrCreateClientForScidoo({
        hostId,
        email: reservation.customer.email,
        firstName: reservation.customer.first_name,
        lastName: reservation.customer.last_name,
        scidooGuestId: reservation.customer.guest_id,
        source: 'scidoo_api'
    });

    // 2. PROPRIETÀ: Trova/crea usando room_type_id
    const { propertyId } = await findOrCreatePropertyForScidoo({
        hostId,
        roomTypeName: `Room Type ${reservation.room_type_id}`,
        scidooRoomTypeId: parseInt(reservation.room_type_id),
        source: 'scidoo_api'
    });

    // 3. PRENOTAZIONE: Salva con ID univoco
    await firestore.collection('reservations').doc(`scidoo_${reservation.internal_id}`).set({
        hostId,
        propertyId,
        clientId,
        startDate: parseDateToTimestamp(reservation.checkin_date),
        endDate: parseDateToTimestamp(reservation.checkout_date),
        status: mapScidooStatus(reservation.status),
        scidooReservationId: reservation.internal_id,
        scidooExternalId: reservation.id,
        importedFrom: 'scidoo_api',
        // ... altri campi
    }, { merge: true });
}
```

**Mapping Stati Prenotazione:**
```typescript
function mapScidooStatus(scidooStatus: string): GioviAiStatus {
    const statusMap = {
        'opzione': 'pending',
        'attesa_pagamento': 'awaiting_payment',
        'confermata_pagamento': 'confirmed',
        'confermata_carta': 'confirmed',
        'check_in': 'checked_in',
        'check_out': 'checked_out',
        'annullata': 'cancelled',
        'eliminata': 'deleted'
    };
    return statusMap[scidooStatus] || 'unknown';
}
```

### **🎨 Implementazione Frontend (Flutter)**

#### **1. Modello Dati**

Il frontend era già predisposto per multiple integrazioni PMS:

```dart
enum PMSProvider {
    smoobu('Smoobu', 'smoobu'),
    scidoo('Scidoo', 'scidoo'),    // ✅ Già presente
    // altri provider...
}
```

#### **2. Servizio di Integrazione**

```dart
class PMSIntegrationService {
    // Test connessione senza salvare
    Future<PMSTestResponse> testPMSConnection(PMSProvider.scidoo, apiKey);
    
    // Configurazione completa
    Future<PMSConfigResponse> configurePMSIntegration(PMSProvider.scidoo, apiKey);
    
    // Stato attuale
    Future<PMSIntegrationConfig?> getPMSStatus(PMSProvider.scidoo);
    
    // Sincronizzazione proprietà
    Future<PMSPropertiesSyncResult?> syncPMSProperties(PMSProvider.scidoo);
}
```

#### **3. Interfaccia Utente**

**Settings Page - Sezione PMS:**
- ✅ Dropdown con Scidoo pre-configurato
- ✅ Campo API Key con validazione
- ✅ Bottone "Testa Connessione" → Preview proprietà
- ✅ Bottone "Configura" → Import automatico completo
- ✅ Card stato integrazione con statistiche
- ✅ Bottone "Sincronizza" per sync manuale

**Adattamenti specifici per Scidoo:**
- 🔧 Testo descrittivo: "sincronizzazione periodica" vs "webhook real-time"
- 🔧 Nascosto bottone "Webhook" (non applicabile a Scidoo)
- 🔧 Statistiche adattate per polling mode

### **📊 Struttura Database**

**Collection: `users` (Host)**
```firestore
{
    "uid": "host_id",
    "role": "host",
    
    // Configurazione Scidoo
    "scidooApiKey": "api_key_encrypted",
    "scidooAccountId": "account_id",
    "scidooAccountName": "Nome Hotel",
    "scidooAccountEmail": "email@hotel.com",
    "scidooConfiguredAt": Timestamp,
    
    // Statistiche sync
    "scidooSyncStats": {
        "totalRoomTypes": 5,
        "totalRecentReservations": 127,
        "lastSyncAt": Timestamp,
        "lastManualSyncAt": Timestamp
    }
}
```

**Collection: `properties`**
```firestore
{
    "id": "property_id",
    "name": "Room Type Deluxe",
    "hostId": "host_id",
    
    // Dati specifici Scidoo
    "scidooRoomTypeId": 123,
    "importedFrom": "scidoo_config",
    
    "createdAt": Timestamp,
    "lastSyncAt": Timestamp
}
```

**Collection: `reservations`**
```firestore
{
    "id": "scidoo_12345",  // Formato: scidoo_{internal_id}
    "hostId": "host_id",
    "propertyId": "property_id",
    "clientId": "client_id",
    
    "startDate": Timestamp,
    "endDate": Timestamp,
    "status": "confirmed",
    "guests": 2,
    
    // Dati specifici Scidoo
    "scidooReservationId": 12345,     // internal_id
    "scidooExternalId": 67890,        // id esterno
    "scidooRoomTypeId": "123",
    "scidooOrigin": "Booking.com",
    "scidooStatus": "confermata_pagamento",
    
    "importedFrom": "scidoo_api",
    "createdAt": Timestamp,
    "lastSyncAt": Timestamp
}
```

**Collection: `users` (Cliente)**
```firestore
{
    "uid": "client_id",
    "email": "cliente@email.com",
    "name": "Mario Rossi",
    "role": "client",
    
    "assignedHostId": "host_id",
    "assignedPropertyId": "property_id",
    
    // ID Scidoo per tracking
    "scidooGuestId": 789,
    "importedFrom": "scidoo_api"
}
```

### **🔄 Flusso Completo di Integrazione**

#### **Fase 1: Configurazione Iniziale (Frontend)**
1. Host va in **Impostazioni** → **Integrazioni PMS**
2. Seleziona **"Scidoo"** dal dropdown
3. Inserisce **API Key Scidoo**
4. Clicca **"Testa Connessione"**
   - Frontend → `POST /config/scidoo/test`
   - Preview proprietà trovate (room types)
5. Clicca **"Configura"**
   - Frontend → `POST /config/scidoo`
   - Import automatico completo

#### **Fase 2: Import Automatico (Backend)**
```
POST /config/scidoo
├── 1. Test API Key con Scidoo
├── 2. Recupero account info
├── 3. Import room types → creazione proprietà
├── 4. Import prenotazioni recenti (30 giorni)
├── 5. Salvataggio configurazione host
└── 6. Risposta con statistiche import
```

#### **Fase 3: Sincronizzazione Continua**
**Attualmente manuale**, futuro polling automatico:
- Host clicca **"Sincronizza"** → `POST /config/scidoo/sync-now`
- Sistema chiama `getModifiedReservations(apiKey)` 
- Processa solo prenotazioni modificate dall'ultima sync
- Aggiorna timestamp `lastSyncAt`

### **⚡ Prestazioni e Scalabilità**

**Ottimizzazioni implementate:**
- ✅ **Chiamate API minimizzate** usando `last_modified=true`
- ✅ **Cache proprietà** per evitare ricreazioni
- ✅ **Batch operations** per database writes
- ✅ **Merge updates** per prenotazioni esistenti
- ✅ **Error handling robusto** con retry logic

**Scalabilità futura (polling automatico):**
- 📊 **Polling interval dinamico** basato su attività host
- 📊 **Batch processing** per multiple host
- 📊 **Rate limiting** per API Scidoo
- 📊 **Circuit breaker** pattern per resilienza

### **🧪 Testing e Validazione**

**Backend Testing:**
```bash
# Build e deploy
cd pms-sync-service
npm run build
gcloud run deploy pms-sync-service --source . --region europe-west1
```

**Frontend Testing:**
```bash
# Avvio app Flutter
flutter run -d chrome --web-port 3000

# Test flow completo:
# 1. Accedi come host
# 2. Impostazioni → Integrazioni PMS  
# 3. Scidoo → Inserisci API Key → Testa → Configura
# 4. Verifica Firebase: users, properties, reservations
```

**Validazione Database:**
- Controlla collection `users` → campi `scidoo*`
- Controlla collection `properties` → `importedFrom: "scidoo_config"`
- Controlla collection `reservations` → `id: "scidoo_*"`

---

## 🚀 **Come Iniziare**

### **Prerequisiti**
- Flutter 3.x
- Node.js 18+
- Google Cloud account
- Firebase project configurato

### **Setup Locale**
```bash
# Clone repository
git clone [repository-url]
cd giovi_ai_demo_3

# Frontend Flutter
flutter pub get
flutter run -d chrome

# Backend Services
cd pms-sync-service
npm install
npm run build
npm start  # Locale su :8080
```

### **Deploy Produzione**
```bash
# Deploy pms-sync-service
cd pms-sync-service
gcloud run deploy pms-sync-service \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated

# Deploy altri servizi
cd ../gemini-proxy-service
gcloud run deploy gemini-proxy-service \
  --source . \
  --region europe-west1

# Deploy functions
cd ../functions
firebase deploy --only functions
```

---

## 📋 **Roadmap Integrazioni PMS**

### **Implementate ✅**
- **Smoobu** - Webhook real-time completo
- **Scidoo** - API polling con configurazione automatica
- **CSV Import** - Upload manuale per qualsiasi PMS

### **In Sviluppo 🚧**
- **Polling automatico Scidoo** - Sistema background job
- **Kross Booking** - API REST integration
- **Booking.com Partner API** - Direct integration

### **Pianificate 📋**
- **Airbnb API** - OAuth2 integration  
- **Expedia Partner Central** - XML/REST hybrid
- **Channel Manager APIs** - Aggregatori principali

---

## 🤝 **Contributi**

Per contribuire al progetto:
1. Fork del repository
2. Crea feature branch (`git checkout -b feature/nome-feature`)
3. Commit delle modifiche (`git commit -am 'Aggiunge feature'`)
4. Push al branch (`git push origin feature/nome-feature`)
5. Crea Pull Request

---

## 📝 **Licenza**

Questo progetto è sotto licenza proprietaria. Tutti i diritti riservati.

---

## 📞 **Supporto**

Per supporto tecnico o domande:
- 📧 Email: [supporto@giovi.ai]
- 📱 Documentazione: [docs.giovi.ai]
- 🐛 Issues: [GitHub Issues]
