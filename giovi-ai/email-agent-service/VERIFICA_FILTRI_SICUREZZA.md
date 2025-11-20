# 🔒 Verifica Filtri di Sicurezza - Gmail Watch

**IMPORTANTE:** Prima di testare con email reali, verifica che il sistema risponda SOLO alle email previste.

---

## 📋 Filtri Attivi nel Sistema

### **Filtro 1: Email Rilevanti (_is_email_relevant)**

Il sistema processa SOLO queste email:

#### ✅ Se `pmsProvider = "scidoo"`:
- **Email conferma Scidoo:** `from:reservation@scidoo.com` + subject inizia con `"Confermata - Prenotazione"`
- **Email cancellazione Scidoo:** `from:reservation@scidoo.com` + subject inizia con `"Cancellata - Prenotazione"`
- **Messaggi guest Booking:** `from:@guest.booking.com`
- **Messaggi guest Airbnb:** `from:express@airbnb.com`

#### ✅ Se `pmsProvider = "booking"` o `"airbnb"`:
- **Messaggi guest Booking:** `from:@guest.booking.com`
- **Messaggi guest Airbnb:** `from:express@airbnb.com`

#### ❌ **Email IGNORATE:**
- Email da qualsiasi altro mittente
- Email da amici/famiglia
- Newsletter
- Email promozionali
- Email da provider non previsti

---

### **Filtro 2: Solo Messaggi Guest → AI Reply**

Il sistema invia risposte AI SOLO se:

1. ✅ Email è di tipo `booking_message` o `airbnb_message`
2. ✅ Cliente esiste in Firestore (`clients`)
3. ✅ Cliente ha `autoReplyEnabled: true` (default: `true`)
4. ✅ Reservation esiste per quel cliente

---

### **Filtro 3: autoReplyEnabled**

**Default:** `true` (risposte automatiche abilitate per default)

**Come disabilitare per un cliente:**
- Frontend: Toggle AI on/off nella pagina Clienti
- Backend: Campo `autoReplyEnabled: false` in `clients/{clientId}`

---

## ✅ Verifica Filtri Attivi

### **Test 1: Verifica che email non rilevanti siano ignorate**

**Come testare:**

1. Invia email NON rilevanti alla casella Gmail:
   - Email da amico/famiglia
   - Newsletter
   - Email promozionali
   - Email da provider diversi

2. Monitora log Cloud Run:
   ```bash
   gcloud run services logs read email-agent-service \
     --region europe-west1 \
     --project giovi-ai \
     --limit 100 \
     --follow | grep "WATCH"
   ```

3. **Risultato atteso:**
   - ❌ Nessuna risposta inviata
   - ✅ Log: `[WATCH] Email {messageId} non rilevante per pmsProvider=scidoo, skip`
   - ✅ Email marcata come processata (per evitare riprocessamento)

---

### **Test 2: Verifica che solo messaggi guest attivino AI reply**

**Come testare:**

1. Invia email conferma Scidoo (`reservation@scidoo.com`)
   - ✅ Email viene processata e salvata
   - ❌ Nessuna risposta AI generata (non è un messaggio guest)

2. Invia messaggio guest Booking (`@guest.booking.com`)
   - ✅ Email viene processata
   - ✅ Risposta AI generata SOLO se cliente esiste e `autoReplyEnabled=true`

---

### **Test 3: Verifica autoReplyEnabled**

**Come testare:**

1. **Cliente con `autoReplyEnabled: true`:**
   - Invia messaggio guest
   - ✅ Risposta AI generata e inviata

2. **Cliente con `autoReplyEnabled: false`:**
   - Disabilita AI per un cliente (Frontend → Clienti → Toggle AI off)
   - Invia messaggio guest a quel cliente
   - ❌ Nessuna risposta AI generata
   - ✅ Log: `[PIPELINE] Auto-reply disabilitato per cliente {clientId}`

---

## 🔍 Cosa Verificare nel Codice

### **Funzione `_is_email_relevant()` (gmail_watch_service.py)**

```python
def _is_email_relevant(self, parsed: ParsedEmail, pms_provider: str | None) -> bool:
    """
    Verifica se un'email è rilevante per il pmsProvider.
    
    Regole:
    - Scidoo: solo reservation@scidoo.com (conferme/cancellazioni) + messaggi guest
    - Booking/Airbnb: solo messaggi guest
    - Tutti gli altri: ignorati
    """
```

**Email rilevanti:**
- `scidoo_confirmation`: Se `pmsProvider == "scidoo"`
- `scidoo_cancellation`: Se `pmsProvider == "scidoo"`
- `booking_message`: SEMPRE (indipendentemente da pmsProvider)
- `airbnb_message`: SEMPRE (indipendentemente da pmsProvider)

**Email ignorate:**
- `unhandled`: Tutte le altre email
- Email da mittenti non previsti

---

### **Funzione `should_process_message()` (guest_message_pipeline.py)**

```python
def should_process_message(...) -> tuple[bool, Optional[str]]:
    """
    Verifica se un messaggio guest deve essere processato per AI reply.
    
    Controlli:
    1. Email deve essere booking_message o airbnb_message
    2. Cliente deve esistere in Firestore
    3. autoReplyEnabled deve essere true
    """
```

**Condizioni per AI reply:**
1. ✅ `parsed.kind in ["booking_message", "airbnb_message"]`
2. ✅ Cliente trovato in `clients` (per `reservationId` o `guestEmail`)
3. ✅ `clients/{clientId}.autoReplyEnabled == true`

---

## 🛡️ Protezioni Attive

### **1. Filtro per Mittente**
- Solo email da domini specifici vengono processate
- Email da mittenti sconosciuti sono automaticamente ignorate

### **2. Filtro per Tipo Email**
- Solo `booking_message` e `airbnb_message` possono attivare AI reply
- Email conferma/cancellazione NON generano risposte

### **3. Filtro per Cliente**
- Solo clienti esistenti in Firestore possono ricevere risposte
- Cliente deve avere una reservation attiva

### **4. Filtro autoReplyEnabled**
- Default: `true` (risposte abilitate)
- Può essere disabilitato per cliente specifico
- Controllo eseguito PRIMA di generare risposta AI

---

## 📊 Flusso di Controllo Completo

```
1. Email ricevuta via Gmail Watch
   ↓
2. Email parsata (determina tipo: booking_message, scidoo_confirmation, etc.)
   ↓
3. Filtro _is_email_relevant()
   - Se NON rilevante → SKIP (nessuna risposta)
   - Se rilevante → Continua
   ↓
4. Email salvata in Firestore (se rilevante)
   ↓
5. Se email è booking_message o airbnb_message:
   ↓
6. Verifica should_process_message()
   - Cliente esiste?
   - autoReplyEnabled = true?
   - Se NO → SKIP (nessuna risposta)
   - Se SÌ → Continua
   ↓
7. Genera risposta AI (Gemini)
   ↓
8. Invia email risposta
```

---

## ✅ Checklist Sicurezza

Prima di iniziare i test, verifica:

- [ ] **Email non rilevanti vengono ignorate** (test con email casuali)
- [ ] **Solo messaggi guest attivano AI reply** (test con email conferma)
- [ ] **autoReplyEnabled funziona** (test con cliente con AI disabilitato)
- [ ] **Log mostrano correttamente email ignorate** (`non rilevante`, `skip`)
- [ ] **Nessuna risposta inviata a email non previste**

---

## 🔧 Come Testare in Sicurezza

### **Test Safe (Nessun Risiko di Risposta):**

1. **Test con email conferma Scidoo:**
   - ✅ Viene processata e salvata
   - ❌ Nessuna risposta (non è messaggio guest)

2. **Test con email casuali:**
   - ❌ Vengono ignorate
   - ❌ Nessuna risposta

3. **Test con cliente con autoReplyEnabled=false:**
   - ✅ Messaggio ricevuto
   - ❌ Nessuna risposta

### **Test con Risposta AI (Da fare con cautela):**

1. **Test con messaggio guest** (solo dopo aver verificato i filtri)
   - Assicurati che il cliente esista
   - Assicurati che `autoReplyEnabled=true`
   - Verifica che sia un messaggio reale da Booking/Airbnb

---

## ⚠️ Attenzione

**Per sicurezza:**
1. **Testa prima con email conferma** (non generano risposte)
2. **Verifica i log** per vedere quali email vengono processate
3. **Testa con cliente con autoReplyEnabled=false** per verificare il filtro
4. **Solo dopo** testa con messaggi guest reali

**Il sistema è configurato per rispondere SOLO a:**
- Messaggi guest da `@guest.booking.com` o `express@airbnb.com`
- Cliente deve esistere e avere `autoReplyEnabled=true`
- Cliente deve avere una reservation attiva

