# 🔑 Guida Setup Credenziali Booking.com - Machine Account

**Data creazione:** 2025-01-20  
**Obiettivo:** Guida passo-passo per ottenere e configurare credenziali Booking.com API

---

## 📋 Panoramica

Per usare le API Booking.com, devi:
1. **Avere accesso al Provider Portal** (account Booking.com provider)
2. **Creare/attivare Machine Account** (credenziali API)
3. **Configurare endpoint access** (abilitare Messaging e Reservation API)
4. **Ottenere credenziali** (username e password)
5. **Configurare mapping** (booking_property_id → host_id)

---

## 🚀 Step 1: Accesso Provider Portal

### **Prerequisiti**
- ✅ Account Booking.com provider esistente
- ✅ Accesso admin al Provider Portal
- ✅ Permessi per configurazione API

### **Come accedere**

1. **Vai al Provider Portal:**
   - URL: `https://admin.booking.com/` (o il link specifico per il tuo paese)
   - Login con credenziali provider

2. **Verifica permessi:**
   - Devi avere accesso alla sezione "Connectivity" o "API"
   - Se non vedi questa sezione, contatta Booking.com Support

---

## 🔧 Step 2: Creare/Attivare Machine Account

### **Opzione A: Machine Account Esistente**

Se hai già un Machine Account:

1. **Vai a:**
   - `Administration` → `Machine account`
   - O cerca "Machine account" nel menu

2. **Trova il tuo Machine Account:**
   - Dovresti vedere lista di Machine Accounts
   - Se ne hai già uno, vai al prossimo step

### **Opzione B: Creare Nuovo Machine Account**

Se non hai un Machine Account:

1. **Vai a:**
   - `Administration` → `Machine account`
   - Clicca "Create new machine account" (o simile)

2. **Compila form:**
   - **Name:** Nome identificativo (es. "Giovi AI Email Agent")
   - **Description:** Descrizione opzionale
   - **Email:** Email per notifiche (opzionale)

3. **Salva:**
   - Booking.com creerà il Machine Account
   - Nota: potrebbe richiedere approvazione (1-2 giorni lavorativi)

### **Credenziali Machine Account**

Una volta creato/attivato, avrai:
- **Username:** Identificatore univoco (es. "partner_12345")
- **Password:** Password generata (salva subito!)
- **API Base URLs:**
  - Messaging: `https://supply-xml.booking.com/messaging`
  - Reservation: `https://secure-supply-xml.booking.com/hotels/ota/`

⚠️ **IMPORTANTE:** Salva subito username e password! La password potrebbe non essere mostrata di nuovo.

---

## ⚙️ Step 3: Configurare Endpoint Access

### **3.1 Abilitare Messaging API**

1. **Vai a:**
   - `Administration` → `Machine account` → `[Il tuo Machine Account]`
   - Tab: `Endpoint access` o `API Settings`

2. **Abilita Messaging API:**
   - Trova: `GET /messages/latest`
   - Clicca "Enable" o attiva checkbox
   - Questo crea la coda messaggi per il Machine Account

3. **Verifica:**
   - Status dovrebbe essere "Enabled" o "Active"

### **3.2 Abilitare Reservation API**

1. **Nello stesso tab `Endpoint access`:**

2. **Abilita Reservation API:**
   - Trova: `GET /OTA_HotelResNotif` (nuove prenotazioni)
   - Trova: `GET /OTA_HotelResModifyNotif` (modifiche/cancellazioni)
   - Clicca "Enable" per entrambi

3. **Verifica:**
   - Entrambi dovrebbero essere "Enabled"

### **3.3 Features Opzionali (Consigliate)**

Abilita anche queste features se disponibili:

- ✅ **Enable special and structured requests (enable_self_services_messaging)**
  - Per ricevere self-service requests nei messaggi

- ✅ **Include Preferred language in Customer (res_customer_preferred_lang)**
  - Per ricevere lingua preferita del guest

- ✅ **Get extra information for reservations (res_extra_info)**
  - Per dettagli extra sulle prenotazioni

**Come abilitare:**
- `Administration` → `Machine account` → `Features` (o `Settings`)
- Attiva le features desiderate
- Salva

---

## 📝 Step 4: Ottenere Credenziali

### **Dove trovare Username e Password**

1. **Vai a:**
   - `Administration` → `Machine account` → `[Il tuo Machine Account]`
   - Tab: `Credentials` o `Access` o `API Credentials`

2. **Trova:**
   - **Username:** Identificatore (es. `partner_12345`)
   - **Password:** Password API (se non la vedi, potrebbe essere nascosta)

3. **Se Password non visibile:**
   - Cerca pulsante "Show Password" o "Reveal"
   - O "Reset Password" (genera nuova password)
   - ⚠️ Salva subito la password!

### **Salvare Credenziali in .env**

Una volta ottenute, aggiungi al file `.env`:

```bash
# Booking.com API Credentials
BOOKING_API_USERNAME=partner_12345
BOOKING_API_PASSWORD=your_secret_password_here

# Booking.com API URLs (già configurati di default)
BOOKING_MESSAGING_API_BASE_URL=https://supply-xml.booking.com/messaging
BOOKING_RESERVATION_API_BASE_URL=https://secure-supply-xml.booking.com/hotels/ota/

# Booking.com API Version (1.0 o 1.2)
BOOKING_API_VERSION=1.2

# Polling Intervals (in secondi)
BOOKING_POLLING_INTERVAL_RESERVATIONS=20
BOOKING_POLLING_INTERVAL_MESSAGES=60
```

⚠️ **SICUREZZA:** Non committare `.env` nel repository! Già incluso in `.gitignore`.

---

## 🗺️ Step 5: Configurare Mapping Property → Host

### **Perché serve**

Il sistema è **MULTI-HOST**: un Machine Account gestisce più host. Ogni prenotazione deve essere mappata al corretto host usando `booking_property_id` → `host_id`.

### **Come configurare**

#### **Metodo 1: Via API (quando implementato)**

```python
# Script per creare mapping iniziali
# (da implementare - vedi T2A.6)
```

#### **Metodo 2: Manualmente in Firestore (Temporaneo)**

1. **Vai a Firestore Console:**
   - `https://console.firebase.google.com/`
   - Seleziona il tuo progetto

2. **Crea Collection:**
   - Collection: `bookingPropertyMappings`
   - Document ID: `auto-generated`

3. **Crea Mapping per ogni property:**
   ```json
   {
     "bookingPropertyId": "8011855",
     "hostId": "host-abc123",
     "internalPropertyId": "property-xyz789",
     "propertyName": "Villa Bella Vista",
     "createdAt": "2025-01-20T10:00:00Z"
   }
   ```

   Dove:
   - `bookingPropertyId`: ID property Booking.com (HotelCode)
   - `hostId`: ID host interno (dal tuo sistema)
   - `internalPropertyId`: ID property interno (opzionale, se già esiste)
   - `propertyName`: Nome property (per riferimento)

4. **Ripeti per tutte le properties di ogni host**

#### **Come trovare booking_property_id**

1. **Dal Provider Portal:**
   - `Properties` → `[Nome Property]` → `Details`
   - Cerca campo "Hotel Code" o "Property ID"

2. **Dalle API:**
   - Usa `GET /properties` (se disponibile)
   - O controlla reservation XML: campo `HotelCode`

---

## ✅ Step 6: Verifica Setup

### **Test 1: Verifica Credenziali**

```bash
# Test connessione API (senza dipendenze pesanti)
python3 -c "
import requests
import base64

username = 'YOUR_USERNAME'
password = 'YOUR_PASSWORD'

# Basic Auth
auth = base64.b64encode(f'{username}:{password}'.encode()).decode()

# Test Messaging API
response = requests.get(
    'https://supply-xml.booking.com/messaging/messages/latest',
    headers={'Authorization': f'Basic {auth}'},
    timeout=10
)

print(f'Status: {response.status_code}')
if response.status_code == 200:
    print('✅ Credenziali OK!')
    data = response.json()
    print(f'Messages in queue: {data.get(\"data\", {}).get(\"number_of_messages\", 0)}')
else:
    print(f'❌ Errore: {response.text}')
"
```

### **Test 2: Verifica Endpoint Access**

Controlla nel Provider Portal:
- ✅ `GET /messages/latest` è "Enabled"
- ✅ `GET /OTA_HotelResNotif` è "Enabled"
- ✅ `GET /OTA_HotelResModifyNotif` è "Enabled"

---

## 🆘 Problemi Comuni

### **Problema 1: "Machine Account non trovato"**

**Soluzione:**
- Verifica di essere loggato con account provider corretto
- Contatta Booking.com Support per verificare permessi
- Potrebbe richiedere approvazione (1-2 giorni)

### **Problema 2: "Password non visibile"**

**Soluzione:**
- Usa "Reset Password" per generare nuova password
- Salva subito (non viene mostrata di nuovo)

### **Problema 3: "Endpoint access non disponibile"**

**Soluzione:**
- Verifica che il Machine Account sia completamente attivato
- Alcune features richiedono approvazione separata
- Contatta Booking.com Connectivity Support

### **Problema 4: "401 Unauthorized"**

**Soluzione:**
- Verifica username e password sono corretti
- Verifica formato Base64 encoding
- Controlla che credenziali siano attive nel Provider Portal

### **Problema 5: "403 Forbidden"**

**Soluzione:**
- Verifica che endpoint sia "Enabled" nel Provider Portal
- Verifica che Machine Account abbia accesso alle properties richieste
- Potrebbe richiedere configurazione aggiuntiva

---

## 📞 Supporto

### **Booking.com Connectivity Support**

Se hai problemi:

1. **Contatta Support:**
   - Email: Connectivity Support (tramite Provider Portal)
   - Includi: Machine Account name, RUID (se disponibile), descrizione problema

2. **RUID (Request Unique ID):**
   - Ogni API request ha un RUID in response
   - Salva questo per supporto tecnico

3. **Documentazione:**
   - Provider Portal ha link a documentazione API
   - Vedere: `api_doc_booking/` in questo progetto

---

## ✅ Checklist Finale

Prima di iniziare test:

- [ ] Machine Account creato/attivato
- [ ] Username e Password ottenuti
- [ ] Username e Password salvati in `.env`
- [ ] Messaging API endpoint abilitato
- [ ] Reservation API endpoints abilitati
- [ ] Features opzionali abilitate (se necessario)
- [ ] Mapping `booking_property_id` → `host_id` configurati in Firestore
- [ ] Test credenziali passato (200 OK)
- [ ] Provider Portal verificato

---

## 🎯 Prossimi Step

Una volta completato setup:

1. ✅ **Fase 1: Test Client** (30 min)
   - Verifica credenziali funzionano
   - Test chiamata singola API

2. ✅ **Fase 2: Test Polling Singolo** (1 ora)
   - Test reservation polling
   - Test messaging polling

3. ✅ **Fase 3: Test End-to-End** (2-3 ore)
   - Flusso completo
   - Verifica integrazione

Vedi: `TEST_MANUALI_VS_AUTOMATICI.md` per dettagli test.

---

**Ultima modifica:** 2025-01-20

