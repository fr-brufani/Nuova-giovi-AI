# 📧 Distinzione tra Email di Conferma e Messaggi Airbnb

## 🔍 Risposta alla Domanda

**SÌ, c'è una distinzione netta** tra come vengono processate le email di prenotazione diretta Airbnb che contengono un messaggio e quelle che non contengono un messaggio.

---

## 📋 Tipi di Email Airbnb

### **1. Email di Conferma Prenotazione** (`airbnb_confirmation`)

**Parser:** `AirbnbConfirmationParser` (`parsers/airbnb_confirm.py`)

**Identificazione:**
- Subject contiene: `"Prenotazione confermata"` o `"arriverà"`
- Mittente: `automated@airbnb.com` o `express@airbnb.com`

**Cosa viene estratto:**
- ✅ `reservationId` (codice di conferma)
- ✅ `threadId` (ID conversazione)
- ✅ `propertyName` (nome struttura)
- ✅ `guestName` (nome ospite)
- ✅ `checkIn` / `checkOut` (date)
- ✅ `adults` (numero ospiti)
- ✅ `totalAmount` (importo totale)
- ❌ **NON estrae messaggi del guest** (anche se presenti nell'email)

**Processamento nel Backfill:**
```python
# FASE 2: Processa PRIMA tutte le conferme
if parsed.kind in ["scidoo_confirmation", "airbnb_confirmation"]:
    # Salva in Firestore: properties, clients, reservations
    save_result = persistence_service.save_parsed_email(parsed_email=parsed, host_id=host_id)
```

**Salvataggio in Firestore:**
- Crea/trova `properties/{propertyId}`
- Crea/trova `clients/{clientId}`
- Crea/aggiorna `reservations/{reservationId}`

**⚠️ IMPORTANTE:** Anche se l'email di conferma contiene un messaggio del guest, **il messaggio NON viene estratto** dal parser di conferma. Solo i dati della prenotazione vengono salvati.

---

### **2. Email di Messaggio Guest** (`airbnb_message`)

**Parser:** `AirbnbMessageParser` (`parsers/airbnb_message.py`)

**Identificazione:**
- Subject contiene: `"messaggio"` o `"prenotazione per"` o `"re:"`
- Mittente: `@airbnb.com` o `@reply.airbnb.com`

**Cosa viene estratto:**
- ✅ `reservationId` (se disponibile)
- ✅ `threadId` (ID conversazione - **chiave per collegare al messaggio**)
- ✅ `message` (testo del messaggio del guest)
- ✅ `guestName` (nome ospite)
- ✅ `replyTo` (indirizzo per rispondere)
- ❌ **NON estrae dati di prenotazione** (property, date, importo, ecc.)

**Processamento nel Backfill:**
```python
# FASE 4: Processa altre email (non conferme/cancellazioni)
if parsed.kind == "airbnb_message":
    # NON viene salvato automaticamente in Firestore durante backfill
    # Solo marcato come processato
    processed_repository.mark_processed(email, message_id)
```

**⚠️ IMPORTANTE:** I messaggi **NON vengono salvati automaticamente** durante il backfill. Vengono solo marcati come processati.

**Processamento Real-time (Gmail Watch):**
Quando arriva una nuova email di messaggio (via Gmail Watch), viene processata dal `GuestMessagePipelineService`:
1. Trova il cliente usando `threadId` o `reservationId`
2. Verifica se `autoReplyEnabled` è attivo
3. Se sì, salva il messaggio in `properties/{propertyId}/conversations/{clientId}/messages`
4. Genera risposta AI tramite Gemini
5. Invia risposta via Gmail API

---

## 🔄 Flusso Completo

### **Scenario 1: Email di Conferma SENZA Messaggio**

```
Email Airbnb → Subject: "Prenotazione confermata - Francesco arriverà il 15 gen"
              → Parser: AirbnbConfirmationParser
              → Tipo: airbnb_confirmation
              → Estrae: reservationId, threadId, property, date, guest info
              → Salva: properties, clients, reservations
              → ❌ Messaggio: NON estratto (non presente)
```

### **Scenario 2: Email di Conferma CON Messaggio**

```
Email Airbnb → Subject: "Prenotazione confermata - Francesco arriverà il 15 gen"
              → Contiene anche: "Messaggio da Francesco: Ciao, vorrei..."
              → Parser: AirbnbConfirmationParser
              → Tipo: airbnb_confirmation
              → Estrae: reservationId, threadId, property, date, guest info
              → Salva: properties, clients, reservations
              → ⚠️ Messaggio: PRESENTE ma NON estratto dal parser di conferma
              → ❌ Il messaggio viene PERDUTO (non salvato)
```

**⚠️ PROBLEMA ATTUALE:** Se un'email di conferma contiene anche un messaggio del guest, il messaggio **non viene estratto** perché il `AirbnbConfirmationParser` non cerca messaggi.

### **Scenario 3: Email di Messaggio Separata**

```
Email Airbnb → Subject: "Nuovo messaggio da Francesco"
              → Parser: AirbnbMessageParser
              → Tipo: airbnb_message
              → Estrae: threadId, message, guestName, replyTo
              → Durante Backfill: Solo marcato come processato
              → Durante Watch: Processato da GuestMessagePipelineService
              → Salva: properties/{propertyId}/conversations/{clientId}/messages
```

---

## 🐛 Problema Identificato

**Le email di conferma Airbnb che contengono anche un messaggio del guest vengono trattate come email di conferma normali:**

1. ✅ I dati della prenotazione vengono estratti e salvati
2. ❌ **Il messaggio del guest viene ignorato** (non estratto dal parser)
3. ❌ Il messaggio **non viene salvato** in Firestore
4. ❌ Il messaggio **non viene processato** per generare risposta AI

**Esempio:**
```
Email Airbnb:
Subject: "Prenotazione confermata - Francesco arriverà il 15 gen"

Contenuto:
- Dati prenotazione: ✅ Estratti e salvati
- Messaggio guest: "Ciao, vorrei sapere se c'è parcheggio" ❌ PERDUTO
```

---

## 💡 Soluzione Possibile

Per gestire correttamente le email di conferma che contengono anche messaggi, ci sono due approcci:

### **Opzione 1: Estendere AirbnbConfirmationParser**

Modificare `AirbnbConfirmationParser` per estrarre anche messaggi del guest se presenti:

```python
class AirbnbConfirmationParser(EmailParser):
    def parse(self, content: EmailContent) -> ParsedEmail:
        # ... estrazione dati prenotazione ...
        
        # Estrai anche messaggio se presente
        guest_message = extract_guest_message_from_confirmation(text, soup)
        
        reservation = ReservationInfo(...)
        guest_message_info = GuestMessageInfo(...) if guest_message else None
        
        return ParsedEmail(
            kind="airbnb_confirmation",
            reservation=reservation,
            guest_message=guest_message_info,  # Aggiunto
            ...
        )
```

### **Opzione 2: Processare Messaggi nelle Conferme**

Nel `backfill_service.py`, dopo aver salvato la conferma, verificare se contiene un messaggio e processarlo:

```python
# Dopo aver salvato la conferma
if parsed.kind == "airbnb_confirmation" and has_guest_message(parsed):
    # Estrai e processa il messaggio
    guest_message = extract_message_from_confirmation(parsed)
    # Salva in conversazione o processa per AI reply
```

---

## 📊 Confronto

| Caratteristica | Email Conferma | Email Messaggio |
|---------------|----------------|-----------------|
| **Parser** | `AirbnbConfirmationParser` | `AirbnbMessageParser` |
| **Subject Pattern** | "Prenotazione confermata", "arriverà" | "messaggio", "prenotazione per", "re:" |
| **Estrae Dati Prenotazione** | ✅ Sì | ❌ No |
| **Estrae Messaggio Guest** | ❌ No | ✅ Sì |
| **Salvataggio in Backfill** | ✅ Sì (properties, clients, reservations) | ❌ No (solo marcato come processato) |
| **Processamento AI Reply** | ❌ No | ✅ Sì (solo via Gmail Watch) |
| **Gestione Messaggi in Conferma** | ❌ **PERDUTI** | N/A |

---

## 🎯 Raccomandazione

**Per gestire correttamente le email di conferma che contengono messaggi:**

1. **Estendere `AirbnbConfirmationParser`** per estrarre anche messaggi del guest se presenti
2. **Modificare `backfill_service.py`** per processare anche i messaggi estratti dalle conferme
3. **Salvare i messaggi** in `properties/{propertyId}/conversations/{clientId}/messages` anche durante il backfill
4. **Processare i messaggi** per generare risposta AI se `autoReplyEnabled` è attivo

---

## 📝 File Coinvolti

- **Parser Conferma:** `parsers/airbnb_confirm.py`
- **Parser Messaggio:** `parsers/airbnb_message.py`
- **Backfill Service:** `services/backfill_service.py`
- **Persistence Service:** `services/persistence_service.py`
- **Guest Message Pipeline:** `services/guest_message_pipeline.py`

