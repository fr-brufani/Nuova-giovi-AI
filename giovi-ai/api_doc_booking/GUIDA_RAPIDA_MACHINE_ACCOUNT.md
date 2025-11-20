# 🎯 Guida Rapida: Trovare Machine Account (Provider Portal)

**Per utenti già nel Provider Portal Booking.com**

---

## 📍 Dove Sei Ora

Sei nella **Homepage di Gruppo** - questo è corretto! ✅

Vedi nel menu:
- Homepage di Gruppo (dove sei ora)
- Prenotazioni
- Guadagni da strategia tariffaria
- Recensioni
- Contabilità
- Novità
- Modifiche in blocco
- **Altro** ← **Qui potrebbe essere!**

---

## 🔍 STEP 1: Cerca "Machine Account" o "Connectivity"

### **Metodo 1: Menu "Altro"**

1. **Clicca su "Altro"** nel menu in alto (ultimo elemento a destra)
2. **Cerca nei sottomenu:**
   - **"Connectivity"** o
   - **"API"** o
   - **"Machine account"** o
   - **"Amministrazione"** o **"Administration"**

### **Metodo 2: Barra di Ricerca**

1. **Usa la barra di ricerca in alto a destra:**
   - Cerca: **"machine account"**
   - O cerca: **"connectivity"**
   - O cerca: **"API"**
2. **Clicca sul risultato** che appare

### **Metodo 3: Menu Amministrazione**

1. **Cerca nel menu:**
   - Potresti vedere un'icona **⚙️** (impostazioni)
   - O testo **"Amministrazione"** / **"Administration"**
2. **Clicca** e cerca **"Machine account"**

---

## 🎯 STEP 2: Se Trovi "Machine Account"

### **Scenario A: Vedi Lista Machine Account**

Se vedi una lista (anche vuota), significa che:
- ✅ Hai accesso alla sezione
- ✅ Puoi creare/modificare Machine Account

**Cosa fare:**
1. **Se la lista è vuota:**
   - Cerca pulsante **"Crea machine account"** o **"New machine account"** o **"Add machine account"**
   - Clicca e procedi con STEP 3

2. **Se vedi Machine Account(s):**
   - Clicca su uno esistente per vedere credenziali
   - Oppure crea uno nuovo se vuoi separare per questo progetto

### **Scenario B: Vedi "Machine Account" con Pulsante "Create"**

1. **Clicca "Crea machine account"** o **"New machine account"**
2. **Compila form:**
   - **Nome:** `Giovi AI Email Agent` (o nome che preferisci)
   - **Descrizione:** `API access for automated messaging and reservation import` (opzionale)
3. **Clicca "Crea"** o **"Save"**
4. **Attendi:**
   - Potrebbe essere approvato immediatamente
   - O potrebbe richiedere 1-2 giorni lavorativi
   - Controllerai lo stato nella lista

---

## ❌ STEP 3: Se NON Trovi "Machine Account"

### **Problema: Non vedo la sezione**

**Possibili cause:**
1. **Permessi insufficienti**
   - Il tuo account potrebbe non avere accesso a questa sezione
   - **Soluzione:** Contatta Booking.com Support per richiedere accesso

2. **Sezione chiamata diversamente**
   - Cerca: **"Connectivity"** o **"API Settings"** o **"Integration"**
   - O cerca: **"Amministrazione"** → **"Impostazioni API"**

3. **Account non abilitato**
   - Il tuo account provider potrebbe non avere accesso alle API
   - **Soluzione:** Contatta Booking.com Connectivity Support

### **Cosa fare:**
1. **Prova ricerca:**
   - Usa la barra di ricerca per cercare **"API"** o **"connectivity"**
   - Vedrai tutti i risultati disponibili

2. **Contatta Support:**
   - **Email:** Cerca "Connectivity Support" nel Provider Portal
   - **Messaggio:** "Salve, ho bisogno di accesso al Machine Account per configurare le API. Il mio account è: [Nome account]"
   - **Risposta attesa:** 1-2 giorni lavorativi

---

## ✅ STEP 4: Quando Trovi/Crei Machine Account

### **Cosa Vedrai:**

1. **Pagina Machine Account con:**
   - **Nome:** Nome che hai scelto
   - **Status:** "Active" o "Pending"
   - **Tab/Categorie:**
     - **"Credentials"** o **"API Credentials"** ← **Qui sono username/password**
     - **"Endpoint access"** o **"API Settings"** ← **Qui abiliti endpoint**
     - **"Features"** (opzionale)

### **STEP 4A: Ottieni Credenziali**

1. **Clicca tab "Credentials"** o **"API Credentials"**
2. **Trova:**
   - **Username:** Esempio `partner_12345` o simile
   - **Password:** 
     - Se vedi testo: ✅ Copialo subito!
     - Se vedi `••••••••`: Clicca **"Show"** o **"Reveal"**
     - Se non c'è password: Clicca **"Reset Password"** o **"Generate Password"**

3. **⚠️ IMPORTANTE:** Salva subito username e password!

### **STEP 4B: Abilita Endpoint API**

1. **Clicca tab "Endpoint access"** o **"API Settings"**
2. **Cerca e abilita (spunta checkbox o clicca "Enable"):**
   - ✅ `GET /messages/latest` (Messaging API)
   - ✅ `GET /OTA_HotelResNotif` (Reservation API - nuove)
   - ✅ `GET /OTA_HotelResModifyNotif` (Reservation API - modifiche)

3. **Salva** o **"Apply changes"**

4. **Verifica:** Status dovrebbe essere **"Enabled"** o **"Active"**

---

## 📝 STEP 5: Configura Credenziali nel Sistema

Una volta ottenute username e password:

1. **Vai al progetto:**
   ```bash
   cd email-agent-service
   ```

2. **Apri/crea file `.env`** nella root del progetto

3. **Aggiungi:**
   ```bash
   BOOKING_API_USERNAME=partner_12345  # Sostituisci con il tuo username reale
   BOOKING_API_PASSWORD=your_password_here  # Sostituisci con la tua password reale
   ```

4. **Salva** il file

---

## ✅ STEP 6: Test Rapido Credenziali

Esegui questo test per verificare che funzionino:

```bash
cd email-agent-service
python3 -c "
import requests, base64, os
username = os.getenv('BOOKING_API_USERNAME')
password = os.getenv('BOOKING_API_PASSWORD')
if not username or not password:
    print('❌ Configura BOOKING_API_USERNAME e BOOKING_API_PASSWORD nel file .env')
    exit(1)
auth = base64.b64encode(f'{username}:{password}'.encode()).decode()
response = requests.get('https://supply-xml.booking.com/messaging/messages/latest',
                       headers={'Authorization': f'Basic {auth}'}, timeout=10)
print(f'Status: {response.status_code}')
if response.status_code == 200:
    print('✅ CREDENZIALI OK!')
    data = response.json()
    print(f'Messages in queue: {data.get(\"data\", {}).get(\"number_of_messages\", 0)}')
else:
    print(f'❌ Errore: {response.text}')
"
```

Se vedi **"✅ CREDENZIALI OK!"** → tutto funziona! 🎉

---

## 🆘 Se Non Funziona

### **Errore 401 (Unauthorized):**
- Verifica username/password sono corretti
- Rileggili dal Provider Portal

### **Errore 403 (Forbidden):**
- Verifica che endpoint `GET /messages/latest` sia abilitato
- Rivedi STEP 4B

### **Errore 404 (Not Found):**
- Verifica che URL API sia corretto
- Verifica che Machine Account sia attivo

---

## 📞 Supporto

**Booking.com Connectivity Support:**
- Cerca "Connectivity Support" nel Provider Portal
- Include: Machine Account name, descrizione problema

---

## ✅ Checklist Finale

- [ ] Trovata sezione "Machine Account" o "Connectivity"
- [ ] Machine Account creato/attivato
- [ ] Username e Password ottenuti e salvati
- [ ] Endpoint API abilitati (`GET /messages/latest`, etc.)
- [ ] Credenziali salvate in `.env`
- [ ] Test rapido passato (200 OK)

---

**Ultima modifica:** 2025-01-20

