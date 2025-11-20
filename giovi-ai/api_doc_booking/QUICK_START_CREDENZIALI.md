# 🚀 Quick Start: Setup Credenziali Booking.com (Account Aziendale Esistente)

**Per utenti con account Booking.com già esistente**

---

## ✅ STEP 1: Accedi al Provider Portal

1. **Vai a:** https://admin.booking.com/
2. **Login** con le tue credenziali aziendali Booking.com
3. **Verifica accesso:**
   - Se vedi dashboard con "Properties", "Reservations", "Reports" → ✅ Hai accesso
   - Se non vedi queste sezioni → Contatta Booking.com Support

---

## 🔍 STEP 2: Trova Machine Account

### **Metodo A: Verifica se esiste già**

1. Nel menu laterale, cerca: **"Administration"** o **"Connectivity"** o **"API"**
2. Clicca su **"Machine account"** (o **"Machine accounts"**)
3. **Se vedi una lista:**
   - ✅ Hai già Machine Account(s)
   - Prosegui a **STEP 3**
4. **Se vedi "No machine accounts"** o pagina vuota:
   - → Vai a **Metodo B**

### **Metodo B: Crea nuovo Machine Account**

1. Nella pagina "Machine account", cerca pulsante:
   - **"Create machine account"** o
   - **"New machine account"** o
   - **"Add machine account"**
2. **Compila form:**
   - **Name:** `Giovi AI Email Agent` (o nome che preferisci)
   - **Description:** `API access for automated messaging and reservation import` (opzionale)
3. **Clicca "Create"** o "Save"
4. **Attendi:**
   - Potrebbe essere approvato immediatamente
   - O potrebbe richiedere 1-2 giorni lavorativi
   - Controllerai lo stato nella lista Machine Accounts

---

## 🔑 STEP 3: Ottieni Credenziali (Username e Password)

### **Dove trovarle:**

1. **Vai a:** `Administration` → `Machine account` → `[Nome del tuo Machine Account]`
2. **Cerca tab o sezione:**
   - **"Credentials"** o
   - **"API Credentials"** o
   - **"Access"** o
   - **"Authentication"**

### **Cosa vedrai:**

- **Username:** Esempio `partner_12345` o `yourcompany_api_001`
- **Password:** 
  - Se vedi testo: ✅ Copialo subito!
  - Se vedi `••••••••`: Clicca **"Show"** o **"Reveal"**
  - Se non c'è password: Clicca **"Reset Password"** o **"Generate Password"**

### **⚠️ IMPORTANTE:**
- **Salva subito username e password** in un posto sicuro
- La password potrebbe non essere mostrata di nuovo
- Se perdi la password, dovrai resettarla

---

## ⚙️ STEP 4: Abilita Endpoint API

### **Dove andare:**

1. Nella stessa pagina del Machine Account:
   - Cerca tab **"Endpoint access"** o **"API Settings"** o **"Permissions"**
2. **Se non vedi questo tab:**
   - Cerca link **"Configure endpoints"** o simile
   - O vai a: `Connectivity` → `Endpoint Access`

### **Cosa abilitare:**

Cerca e abilita (spunta checkbox o clicca "Enable"):

1. ✅ **`GET /messages/latest`** 
   - Descrizione: "Retrieve messages" o "Messaging API"
   - Questo abilita la coda messaggi

2. ✅ **`GET /OTA_HotelResNotif`**
   - Descrizione: "Retrieve new reservations" o "Reservation API - New"
   - Questo abilita recupero nuove prenotazioni

3. ✅ **`GET /OTA_HotelResModifyNotif`**
   - Descrizione: "Retrieve modified/cancelled reservations" o "Reservation API - Modified"
   - Questo abilita recupero modifiche/cancellazioni

### **Come abilitare:**

- **Metodo 1:** Spunta checkbox accanto a ciascun endpoint
- **Metodo 2:** Clicca "Enable" o "Activate" per ciascun endpoint
- **Salva** o clicca "Apply changes"

### **Verifica:**

Dopo aver salvato, verifica che status sia:
- ✅ **"Enabled"** o **"Active"** o **"✓"**

---

## 📝 STEP 5: Configura Credenziali nel Sistema

### **Crea/Modifica file `.env`**

Nel progetto `email-agent-service`, crea/modifica file `.env`:

```bash
# Booking.com API Credentials
BOOKING_API_USERNAME=partner_12345
BOOKING_API_PASSWORD=your_secret_password_here

# Booking.com API URLs (opzionale, già configurati di default)
BOOKING_MESSAGING_API_BASE_URL=https://supply-xml.booking.com/messaging
BOOKING_RESERVATION_API_BASE_URL=https://secure-supply-xml.booking.com/hotels/ota/

# Booking.com API Version (1.0 o 1.2)
BOOKING_API_VERSION=1.2

# Polling Intervals (in secondi)
BOOKING_POLLING_INTERVAL_RESERVATIONS=20
BOOKING_POLLING_INTERVAL_MESSAGES=60
```

**Sostituisci:**
- `partner_12345` con il tuo **Username** reale
- `your_secret_password_here` con la tua **Password** reale

### **⚠️ SICUREZZA:**

- **Non committare** il file `.env` nel repository!
- Il file `.env` dovrebbe già essere in `.gitignore`
- Usa variabili d'ambiente per produzione

---

## ✅ STEP 6: Test Rapido Credenziali

### **Test 1: Verifica credenziali funzionano**

Crea un file `test_credentials.py`:

```python
#!/usr/bin/env python3
"""Test rapido credenziali Booking.com API"""

import os
import requests
import base64

# Leggi credenziali da .env o variabili ambiente
username = os.getenv("BOOKING_API_USERNAME")
password = os.getenv("BOOKING_API_PASSWORD")

if not username or not password:
    print("❌ ERRORE: BOOKING_API_USERNAME e BOOKING_API_PASSWORD devono essere configurate")
    print("   Aggiungile al file .env o esportale:")
    print("   export BOOKING_API_USERNAME='your-username'")
    print("   export BOOKING_API_PASSWORD='your-password'")
    exit(1)

# Basic Auth
auth_string = f"{username}:{password}"
auth_bytes = auth_string.encode('ascii')
auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

headers = {
    "Authorization": f"Basic {auth_b64}",
    "Content-Type": "application/json"
}

print("🧪 Test connessione Booking.com API...")
print(f"   Username: {username}")

# Test Messaging API
try:
    response = requests.get(
        "https://supply-xml.booking.com/messaging/messages/latest",
        headers=headers,
        timeout=10
    )
    
    print(f"\n📡 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ SUCCESSO! Credenziali funzionano!")
        data = response.json()
        messages_count = data.get("data", {}).get("number_of_messages", 0)
        print(f"   Messages in queue: {messages_count}")
    elif response.status_code == 401:
        print("❌ ERRORE 401: Credenziali non valide")
        print("   Verifica username e password nel Provider Portal")
    elif response.status_code == 403:
        print("❌ ERRORE 403: Accesso negato")
        print("   Verifica che endpoint GET /messages/latest sia abilitato")
    else:
        print(f"❌ ERRORE {response.status_code}: {response.text}")
        
except Exception as e:
    print(f"❌ ERRORE: {e}")
```

Esegui:

```bash
cd email-agent-service
export BOOKING_API_USERNAME="your-username"
export BOOKING_API_PASSWORD="your-password"
python3 test_credentials.py
```

**Se vedi "✅ SUCCESSO!"** → Credenziali OK! Puoi procedere.

**Se vedi errore 401** → Verifica username/password nel Provider Portal

**Se vedi errore 403** → Verifica che endpoint sia abilitato (STEP 4)

---

## 🗺️ STEP 7: Configura Mapping Property → Host (OPZIONALE per ora)

Per test iniziali, puoi saltare questo step. 

Per il sistema multi-host funzionante, devi configurare mapping in Firestore:

1. **Vai a Firestore Console:** https://console.firebase.google.com/
2. **Crea collection:** `bookingPropertyMappings`
3. **Aggiungi documenti:**
   ```json
   {
     "bookingPropertyId": "8011855",
     "hostId": "your-host-id",
     "propertyName": "Nome Property"
   }
   ```

**Come trovare `bookingPropertyId`:**
- Nel Provider Portal: `Properties` → `[Nome Property]` → `Details`
- Cerca campo "Hotel Code" o "Property ID"

---

## ✅ Checklist Finale

Prima di procedere con test completi:

- [ ] ✅ Login Provider Portal funziona
- [ ] ✅ Machine Account trovato/creato
- [ ] ✅ Username e Password ottenuti e salvati
- [ ] ✅ Endpoint `GET /messages/latest` abilitato
- [ ] ✅ Endpoint `GET /OTA_HotelResNotif` abilitato
- [ ] ✅ Endpoint `GET /OTA_HotelResModifyNotif` abilitato
- [ ] ✅ Credenziali salvate in `.env`
- [ ] ✅ Test rapido credenziali passato (200 OK)

---

## 🎯 Prossimi Step

Una volta completato setup:

1. **Test Client Singolo** (30 min)
   - Verifica che API funzionano
   - Vedere: `TEST_MANUALI_VS_AUTOMATICI.md`

2. **Test Polling Singolo** (1 ora)
   - Test reservation polling
   - Test messaging polling

3. **Test End-to-End** (2-3 ore)
   - Flusso completo

---

## 🆘 Problemi Comuni

### **"Non vedo sezione Machine account"**
- Verifica di essere loggato con account corretto
- Alcuni account potrebbero non avere accesso a questa sezione
- Contatta Booking.com Support

### **"Password non visibile"**
- Clicca "Show" o "Reveal"
- O "Reset Password" per generarne una nuova
- Salva subito!

### **"Endpoint non disponibile"**
- Verifica che Machine Account sia completamente attivato
- Potrebbe richiedere approvazione (1-2 giorni)
- Contatta Booking.com Connectivity Support

### **"401 Unauthorized" nel test**
- Verifica username e password sono corretti
- Verifica formato Base64 encoding
- Rileggi credenziali dal Provider Portal

### **"403 Forbidden" nel test**
- Verifica che endpoint sia "Enabled" nel Provider Portal
- Rivedi STEP 4

---

## 📞 Supporto

**Booking.com Connectivity Support:**
- Email: Cerca "Connectivity Support" nel Provider Portal
- Include: Machine Account name, RUID (se disponibile), descrizione problema

---

**Ultima modifica:** 2025-01-20

