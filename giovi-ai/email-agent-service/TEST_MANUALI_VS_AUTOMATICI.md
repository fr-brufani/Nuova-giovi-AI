# 🧪 Test: Manuali vs Automatici - Guida Completa

**Scopo:** Definire quando fare test automatici vs test manuali per integrazione Booking.com

---

## 📊 Overview

### **Test Automatici (80% del lavoro)**
- ✅ **Quando:** Durante tutto lo sviluppo
- ✅ **Chi:** Sistema automatico / CI/CD
- ✅ **Cosa:** Unit tests, integration tests con mock, business logic
- ✅ **Come:** `pytest` o script Python

### **Test Manuali (20% del lavoro)**
- ⚠️ **Quando:** Solo quando necessario (vedi sezione seguente)
- ⚠️ **Chi:** Tu (sviluppatore) con credenziali reali
- ⚠️ **Cosa:** Verifica API reali, end-to-end, certificazione
- ⚠️ **Come:** Script manuali, Postman, Browser

---

## 🤖 TEST AUTOMATICI - Cosa e Quando

### **✅ FASE 1: Setup e Client Base** (GIÀ FATTI)

**Cosa testare automaticamente:**
- ✅ Modelli dati (BookingMessage, BookingReservation)
- ✅ Client API con mock mode
- ✅ Conversione formati
- ✅ Error handling base

**Come eseguire:**
```bash
# Test rapidi (senza dipendenze)
cd email-agent-service
python3 tests/quick_test_booking.py

# Test completi (con pytest)
pytest tests/unit/test_booking_*.py -v

# Test specifici
pytest tests/unit/test_booking_models.py -v
pytest tests/unit/test_booking_messaging_client.py -v
pytest tests/unit/test_booking_reservation_client.py -v
```

**Quando eseguire:**
- ✅ Durante sviluppo (automatically via IDE)
- ✅ Prima di ogni commit
- ✅ In CI/CD pipeline

**Cosa NON serve testare manualmente:**
- ❌ Verifica credenziali reali (non le hai ancora)
- ❌ Test con API reali (non le hai ancora)
- ❌ End-to-end completo (non pronto ancora)

---

### **✅ FASE 2A: Import Prenotazioni** (SVILUPPO IN CORSO)

**Cosa testare automaticamente:**
- ✅ Parser XML OTA (con XML di esempio)
- ✅ Estrazione dati (reservation_id, property_id, guest info)
- ✅ Conversione BookingReservation → Firestore format
- ✅ Polling service logic (con mock client)
- ✅ Persistence service (con Firestore emulator o mock)

**Come eseguire:**
```bash
# Test parser
pytest tests/unit/test_booking_reservation_parser.py -v

# Test polling service
pytest tests/unit/test_booking_reservation_polling.py -v

# Test persistence
pytest tests/unit/test_persistence_service.py -v
```

**Quando eseguire:**
- ✅ Durante sviluppo
- ✅ Prima di commit
- ✅ In CI/CD

**Cosa NON serve testare manualmente ANCORA:**
- ❌ Import prenotazioni reali (non hai credenziali)
- ❌ Verifica XML reali (non hai credenziali)

---

### **✅ FASE 2B: Messaging** (SVILUPPO IN CORSO)

**Cosa testare automaticamente:**
- ✅ Message Processor (conversione Booking → interno)
- ✅ Filtri messaggi (solo GUEST, escludi template)
- ✅ Estrazione reservation_id da conversation_reference
- ✅ GuestMessagePipeline estensioni
- ✅ Reply Service logic (con mock client)

**Come eseguire:**
```bash
# Test message processor
pytest tests/unit/test_booking_message_processor.py -v

# Test pipeline
pytest tests/unit/test_guest_message_pipeline.py -v

# Test reply service
pytest tests/unit/test_booking_reply_service.py -v
```

**Quando eseguire:**
- ✅ Durante sviluppo
- ✅ Prima di commit
- ✅ In CI/CD

**Cosa NON serve testare manualmente ANCORA:**
- ❌ Invio messaggi reali (non hai credenziali)
- ❌ Risposta guest reali (non hai credenziali)

---

### **✅ FASE 3: Integrazione End-to-End** (FUTURO)

**Cosa testare automaticamente:**
- ✅ Flusso completo con mock (polling → processamento → risposta)
- ✅ Edge cases (messaggio senza reservation, duplicate, etc.)
- ✅ Error handling completo
- ✅ Logging e monitoring

**Come eseguire:**
```bash
# Test integrazione
pytest tests/integration/test_booking_flow.py -v

# Test end-to-end con mock
pytest tests/integration/test_booking_e2e_mock.py -v
```

**Quando eseguire:**
- ✅ Durante sviluppo
- ✅ Prima di commit
- ✅ In CI/CD

**Cosa NON serve testare manualmente ANCORA:**
- ❌ Flusso completo con API reali (non hai credenziali)
- ❌ Verifica risposte reali guest (non hai credenziali)

---

## 👤 TEST MANUALI - Quando e Come

### **⚠️ IMPORTANTE: Test Manuali SOLO quando necessario!**

**Regola d'oro:**
> **Non fare test manuali durante sviluppo normale!**
> 
> I test automatici coprono l'80% dei casi.
> I test manuali servono solo per verificare integrazione con API reali
> e casi d'uso specifici che richiedono credenziali reali.

---

### **🎯 SCENARIO 1: Hai appena ottenuto credenziali Booking.com**

**Quando:** Dopo aver completato T0.1 (ottenute credenziali)

**Cosa testare manualmente:**

1. **Verifica Autenticazione API**
   ```bash
   # Test Messaging API
   curl -u "USERNAME:PASSWORD" \
        -H "Accept-Version: 1.2" \
        https://supply-xml.booking.com/messaging/messages/latest
   
   # Test Reservation API
   curl -u "USERNAME:PASSWORD" \
        https://secure-supply-xml.booking.com/hotels/ota/OTA_HotelResNotif
   ```
   
   **Verifica:**
   - ✅ Status 200 (non 401 o 403)
   - ✅ Response JSON/XML valido
   - ✅ Formato response corrisponde a mock

2. **Test Recupero Messaggi Reali**
   - Creare test message come guest su Booking.com
   - Eseguire polling con credenziali reali
   - Verificare formato response reale vs mock
   - Aggiustare mock se necessario

3. **Test Recupero Prenotazioni Reali**
   - Creare test reservation su Booking.com
   - Eseguire polling con credenziali reali
   - Verificare formato XML reale vs mock
   - Aggiustare parser se necessario

**Quanto tempo:** 1-2 ore (solo verifica base)

---

### **🎯 SCENARIO 2: Prima integrazione end-to-end completa**

**Quando:** Dopo Fase 3 (integrazione completa)

**Cosa testare manualmente:**

1. **Test Flusso Completo Messaggi**
   ```
   Step 1: Creare test reservation su Booking.com
   Step 2: Inviare messaggio come guest
   Step 3: Verificare che sistema:
           - Recupera messaggio via API
           - Processa messaggio
           - Genera risposta AI
           - Invia risposta via API
   Step 4: Verificare che guest riceve risposta
   ```

2. **Test Flusso Completo Prenotazioni**
   ```
   Step 1: Creare test reservation su Booking.com
   Step 2: Verificare che sistema:
           - Recupera prenotazione via API entro 20s
           - Parse XML correttamente
           - Salva in Firestore
           - Conferma via acknowledgement
   Step 3: Verificare dati in Firestore Console
   ```

3. **Test Edge Cases Reali**
   - Messaggio senza reservation associata
   - Prenotazione modificata
   - Prenotazione cancellata
   - Rate limiting reale
   - Errori API reali

**Quanto tempo:** 2-4 ore (test completo)

**Script da eseguire:**
```bash
# Avvia polling service con credenziali reali
python3 scripts/test_manual_polling.py

# Monitora logs
tail -f logs/booking-integration.log
```

---

### **🎯 SCENARIO 3: Prima di deploy produzione**

**Quando:** Dopo Fase 4 (testing e refinement)

**Cosa testare manualmente:**

1. **Certificazione Booking.com**
   - Completare Self-Assessment Tutorial
   - Raccogliere RUID per ogni richiesta
   - Screenshot per Booking.com
   - Verificare tutti i requisiti

2. **Test Performance**
   - Test con molte prenotazioni simultanee
   - Test con molti messaggi simultanei
   - Verificare rate limiting handling
   - Verificare memory/CPU usage

3. **Test Produzione**
   - Deploy su staging
   - Test completo su staging
   - Verificare monitoring
   - Test rollback procedure

**Quanto tempo:** 1 giorno (certificazione + test)

---

### **🎯 SCENARIO 4: Debug problemi specifici**

**Quando:** Quando trovi un bug o problema specifico

**Cosa testare manualmente:**

1. **Riprodurre problema**
   - Usa script di test manuale
   - Raccogli logs dettagliati
   - Verifica con API reali

2. **Verifica fix**
   - Testa fix con API reali
   - Verifica che problema risolto
   - Aggiungi test automatico per prevenire regression

**Quanto tempo:** Variabile (quando necessario)

---

## 📋 Checklist Test per Ogni Fase

### **Fase 0-1: Setup Preliminare** ✅
- [x] Test automatici: Modelli, Client mock → **FATTI**
- [ ] Test manuali: **NON NECESSARI** (non hai credenziali)

### **Fase 2A: Import Prenotazioni** 
- [ ] Test automatici: Parser XML, Polling logic, Persistence → **DA FARE**
- [ ] Test manuali: **DOPO aver ottenuto credenziali**

### **Fase 2B: Messaging**
- [ ] Test automatici: Message Processor, Pipeline, Reply Service → **DA FARE**
- [ ] Test manuali: **DOPO aver ottenuto credenziali**

### **Fase 3: Integrazione**
- [ ] Test automatici: Flusso completo mock → **DA FARE**
- [ ] Test manuali: **DOPO aver completato integrazione + credenziali**

### **Fase 4: Testing**
- [ ] Test automatici: Tutti i test unit + integration → **DA FARE**
- [ ] Test manuali: Edge cases reali → **DOPO credenziali**

### **Fase 5: Deployment**
- [ ] Test automatici: CI/CD pipeline → **DA FARE**
- [ ] Test manuali: Certificazione Booking.com → **PRIMA DI PRODUZIONE**

---

## 🚀 Comandi Rapidi

### **Test Automatici**
```bash
# Tutti i test Booking
pytest tests/unit/test_booking_*.py -v

# Test rapidi (senza pytest)
python3 tests/quick_test_booking.py

# Test specifici
pytest tests/unit/test_booking_models.py::test_booking_message_from_api_response -v

# Con coverage
pytest tests/unit/test_booking_*.py --cov=email_agent_service --cov-report=html
```

### **Test Manuali (quando hai credenziali)**
```bash
# Test autenticazione
python3 scripts/test_manual_auth.py

# Test polling manuale
python3 scripts/test_manual_polling.py --messages
python3 scripts/test_manual_polling.py --reservations

# Test end-to-end
python3 scripts/test_manual_e2e.py
```

---

## ⏰ Timeline Test Manuali

**Quando iniziare test manuali:**

1. **NON ADESSO** ❌
   - Stai ancora sviluppando
   - Non hai credenziali
   - Non serve

2. **QUANDO OTTIENI CREDENZIALI** ✅ (Scenario 1)
   - Verifica autenticazione (1-2 ore)
   - Verifica formato response (1 ora)
   - Aggiustamento mock se necessario

3. **DOPO INTEGRAZIONE COMPLETA** ✅ (Scenario 2)
   - Test flusso completo (2-4 ore)
   - Test edge cases (2 ore)

4. **PRIMA DI PRODUZIONE** ✅ (Scenario 3)
   - Certificazione Booking.com (4-8 ore)
   - Test performance (2 ore)

**Totale test manuali stimati:** 10-20 ore (vs 100+ ore di sviluppo)

---

## 💡 Raccomandazioni Finali

### **✅ FAI:**
- ✅ Test automatici per tutto ciò che puoi
- ✅ Test manuali solo quando hai credenziali
- ✅ Test manuali solo per verifiche API reali
- ✅ Aggiungi test automatici dopo ogni bug trovato manualmente

### **❌ NON FARE:**
- ❌ Test manuali durante sviluppo normale
- ❌ Test manuali senza credenziali (inutile)
- ❌ Test manuali per cose che puoi testare automaticamente
- ❌ Dimenticare di aggiungere test automatici dopo test manuali

---

## 📚 Riferimenti

- `tests/quick_test_booking.py` - Script test rapido
- `tests/unit/test_booking_*.py` - Test unit completi
- `tests/fixtures/booking_api_responses.py` - Mock responses
- `PIANO_SVILUPPO_ORDINATO.md` - Piano sviluppo completo

---

**Ricorda:** 🚀 **Sviluppa con mock mode, testa automaticamente tutto ciò che puoi, e usa test manuali SOLO quando hai credenziali e serve verificare API reali!**

