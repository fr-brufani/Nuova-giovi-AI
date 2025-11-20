# 🧪 Test Manuali vs Test Automatizzati - Guida Booking.com Integration

**Data creazione:** 2025-01-15  
**Obiettivo:** Definire quando fare test manuali e quando automatizzare

---

## 📊 Overview: Cosa Testare e Come

### **Test Automatizzati (Eseguiti da CI/CD e Locale)**
- ✅ **Unit Tests** - Test singole funzioni/moduli con mock
- ✅ **Integration Tests** - Test integrazione componenti con mock API
- ✅ **Parser Tests** - Test parsing XML/JSON con dati di esempio
- ✅ **Conversion Tests** - Test conversioni formati

### **Test Manuali (Eseguiti da Te)**
- 🔧 **Integration con API Reali** - Quando hai le credenziali Booking.com
- 🔧 **End-to-End Completo** - Flusso completo con dati reali
- 🔧 **Certificazione Booking.com** - Self-assessment tutorial
- 🔧 **Edge Cases Reali** - Casi limite con dati reali

---

## 🤖 Test Automatizzati: Cosa Viene Testato Automaticamente

### **1. Unit Tests (Eseguiti da pytest)**

#### **Test Modelli Dati**
```bash
# Test modelli BookingMessage e BookingReservation
pytest tests/unit/test_booking_models.py -v
```

**Cosa testa:**
- ✅ Creazione modelli da API response
- ✅ Conversione formato interno
- ✅ Conversione formato Firestore
- ✅ Validazione dati

**Quando eseguire:**
- Prima di ogni commit
- Durante sviluppo (automatically via IDE/watch mode)
- In CI/CD pipeline

#### **Test Client API (Mock Mode)**
```bash
# Test Messaging Client
pytest tests/unit/test_booking_messaging_client.py -v

# Test Reservation Client
pytest tests/unit/test_booking_reservation_client.py -v
```

**Cosa testa:**
- ✅ Inizializzazione client (mock mode)
- ✅ Metodi API con mock responses
- ✅ Gestione errori
- ✅ Conversione formati

**Quando eseguire:**
- Durante sviluppo
- Dopo modifiche ai client
- Prima di commit

#### **Test Parser XML (quando creato)**
```bash
# Test parser OTA XML
pytest tests/unit/test_booking_reservation_parser.py -v
```

**Cosa testa:**
- ✅ Parsing XML OTA
- ✅ Estrazione dati prenotazione
- ✅ Gestione multi-room
- ✅ Edge cases (campi mancanti, etc.)

**Quando eseguire:**
- Durante sviluppo parser
- Dopo modifiche al parser

---

### **2. Integration Tests (Eseguiti da pytest con mock)**

#### **Test Polling Service (con mock client)**
```bash
# Test polling service con mock
pytest tests/integration/test_booking_polling_service.py -v
```

**Cosa testa:**
- ✅ Polling loop con mock client
- ✅ Processamento messaggi/prenotazioni
- ✅ Persistence in Firestore (con test DB)
- ✅ Deduplicazione

**Quando eseguire:**
- Dopo implementazione polling service
- Dopo modifiche al polling logic

---

## 👤 Test Manuali: Quando È Necessario Che Tu Testi

### **1. Integration con API Booking.com Reali (Dopo T0.1)**

**Quando fare:**
- ✅ Dopo aver ottenuto credenziali Machine Account
- ✅ Dopo aver configurato Provider Portal
- ✅ Prima di deploy produzione

**Come fare:**
```bash
# 1. Configura credenziali reali in .env
export BOOKING_API_USERNAME="your-username"
export BOOKING_API_PASSWORD="your-password"

# 2. Test manuale client con API reali
python3 -c "
from email_agent_service.services.integrations.booking_messaging_client import BookingMessagingClient

client = BookingMessagingClient(mock_mode=False)
response = client.get_latest_messages()
print('✅ API reale funziona!')
print(f'Messages: {response[\"data\"][\"number_of_messages\"]}')
"
```

**Cosa verificare:**
- ✅ Autenticazione funziona
- ✅ Response format corretto
- ✅ Rate limiting funziona
- ✅ Error handling corretto (401, 403, 429)

---

### **2. Test End-to-End Completo (Dopo Fase 3)**

**Quando fare:**
- ✅ Dopo aver completato tutti i componenti (Fase 2A + 2B + 3)
- ✅ Prima di deploy produzione
- ✅ Dopo modifiche significative

**Come fare:**

#### **Test 1: Import Prenotazione Reale**
1. Crea test reservation su Booking.com:
   - Usa URL: `https://secure.booking.com/book.html?test=1;hotel_id={property_id}`
   - Completa prenotazione test

2. Avvia polling service:
   ```bash
   # In un terminale, avvia polling
   python3 -m email_agent_service.services.booking_reservation_polling_service
   ```

3. Verifica:
   - ✅ Prenotazione importata entro 20-40 secondi
   - ✅ Dati corretti in Firestore
   - ✅ Client creato automaticamente
   - ✅ Reservation collegata correttamente

#### **Test 2: Risposta Messaggio Reale**
1. Invia messaggio come guest da Booking.com app/desktop

2. Avvia polling service messaggi:
   ```bash
   # In un terminale, avvia polling messaggi
   python3 -m email_agent_service.services.booking_message_polling_service
   ```

3. Verifica:
   - ✅ Messaggio recuperato entro 60 secondi
   - ✅ Risposta AI generata (Gemini)
   - ✅ Risposta inviata via API
   - ✅ Guest riceve risposta

#### **Test 3: Modifica/Cancellazione Prenotazione**
1. Modifica test reservation su Booking.com
2. Verifica:
   - ✅ Modifica importata
   - ✅ Dati aggiornati in Firestore

1. Cancella test reservation
2. Verifica:
   - ✅ Status aggiornato a "cancelled"

---

### **3. Certificazione Booking.com (Self-Assessment Tutorial)**

**Quando fare:**
- ✅ Dopo aver completato integrazione end-to-end
- ✅ Prima di deploy produzione
- ✅ Come prerequisito per certificazione Booking.com

**Come fare:**
1. Segui tutorial nella documentazione Booking.com
2. Raccogli RUID (Request Unique IDs) per ogni richiesta
3. Fai screenshot di ogni step
4. Documenta risultati

**Checklist Certificazione:**
- [ ] Test reservation creation
- [ ] Test message retrieval
- [ ] Test message sending
- [ ] Test self-service requests (v1.2)
- [ ] Test acknowledgement reservations
- [ ] Test error handling
- [ ] RUID collection
- [ ] Screenshot documentation

---

### **4. Edge Cases Reali (Dopo Fase 4)**

**Quando fare:**
- ✅ Dopo test base completati
- ✅ Prima di deploy produzione
- ✅ Per verificare robustezza sistema

**Edge Cases da Testare Manualmente:**

#### **Edge Case 1: Messaggio prima di import prenotazione**
1. Invia messaggio come guest per reservation che non esiste ancora
2. Verifica:
   - ✅ Sistema gestisce gracefully
   - ✅ Messaggio salvato in coda
   - ✅ Quando prenotazione importata, messaggio collegato

#### **Edge Case 2: Rate Limiting**
1. Fai molte richieste API simultanee
2. Verifica:
   - ✅ Exponential backoff funziona
   - ✅ Sistema non crasha
   - ✅ Logging corretto

#### **Edge Case 3: Multi-room Reservation**
1. Crea prenotazione multi-room
2. Verifica:
   - ✅ Parser gestisce correttamente
   - ✅ Dati corretti in Firestore

#### **Edge Case 4: Prenotazione con Payment Clarity**
1. Crea prenotazione con VCC
2. Verifica:
   - ✅ Payment info parsato correttamente
   - ✅ Dati sicuri in Firestore

#### **Edge Case 5: Self-Service Requests (v1.2)**
1. Guest invia self-service request (check-in time, etc.)
2. Verifica:
   - ✅ Request riconosciuta (message_type, attributes)
   - ✅ Risposta AI adeguata

---

### **5. Performance e Stress Testing**

**Quando fare:**
- ✅ Dopo test funzionali completati
- ✅ Prima di deploy produzione

**Come fare:**
1. Crea molte test reservations simultanee
2. Invia molti messaggi simultanei
3. Verifica:
   - ✅ Sistema gestisce load
   - ✅ Nessun memory leak
   - ✅ Performance accettabili
   - ✅ Firestore non supera quote

---

## 📋 Checklist Test per Ogni Fase

### **Fase 1: Client API Base** ✅
- [x] **Automatico:** Unit test modelli dati
- [x] **Automatico:** Unit test client (mock mode)
- [ ] **Manuale:** Test client con API reali (DOPO T0.1)

### **Fase 2A: Import Prenotazioni**
- [ ] **Automatico:** Test parser XML
- [ ] **Automatico:** Test polling service (mock)
- [ ] **Automatico:** Test persistence
- [ ] **Manuale:** Test import prenotazione reale (DOPO credenziali)

### **Fase 2B: Messaging**
- [ ] **Automatico:** Test message processor
- [ ] **Automatico:** Test polling service (mock)
- [ ] **Automatico:** Test reply service (mock)
- [ ] **Manuale:** Test invio messaggio reale (DOPO credenziali)

### **Fase 3: Integrazione End-to-End**
- [ ] **Automatico:** Test integrazione componenti (mock)
- [ ] **Manuale:** Test end-to-end completo con dati reali

### **Fase 4: Testing e Refinement**
- [ ] **Automatico:** Tutti unit/integration test
- [ ] **Manuale:** Edge cases reali
- [ ] **Manuale:** Performance testing

### **Fase 5: Certificazione**
- [ ] **Manuale:** Self-assessment tutorial Booking.com
- [ ] **Manuale:** RUID collection
- [ ] **Manuale:** Documentazione screenshot

---

## 🚀 Come Eseguire Test Automatizzati

### **Tutti i test:**
```bash
cd /Users/francesco/Desktop/vecchio_giovi_ai/giovi-ai/email-agent-service
pytest tests/ -v
```

### **Solo test Booking.com:**
```bash
pytest tests/unit/test_booking_*.py tests/integration/test_booking_*.py -v
```

### **Solo unit test:**
```bash
pytest tests/unit/test_booking_*.py -v
```

### **Con coverage:**
```bash
pytest tests/unit/test_booking_*.py --cov=email_agent_service --cov-report=html
```

### **Watch mode (auto-run su cambiamenti):**
```bash
pytest-watch tests/unit/test_booking_*.py
```

---

## 📝 Quando È Utile Che Tu Faccia Test Manuali

### **✅ FAI Test Manuali Quando:**

1. **Hai appena ottenuto credenziali Booking.com**
   - Test immediato autenticazione
   - Verifica response format reale
   - Confronta con mock responses

2. **Hai completato un componente nuovo**
   - Test end-to-end del componente
   - Verifica integrazione con altri componenti
   - Edge cases specifici

3. **Prima di deploy produzione**
   - Test completo end-to-end
   - Performance testing
   - Certificazione Booking.com

4. **Dopo bug fix**
   - Verifica fix funziona con dati reali
   - Test regression

5. **Per certificazione Booking.com**
   - Self-assessment tutorial
   - RUID collection
   - Screenshot documentation

### **❌ NON Serve Test Manuale Quando:**

1. **Durante sviluppo normale**
   - Test automatizzati sono sufficienti
   - Mock mode copre la maggior parte dei casi

2. **Per validare parsing/conversioni**
   - Unit test con fixture sono sufficienti
   - Mock responses coprono formati

3. **Per test business logic**
   - Unit test con mock sono sufficienti
   - Integration test con mock coprono casi

---

## 🎯 Raccomandazioni

### **Durante Sviluppo:**
1. ✅ **Rilascia spesso** - Test automatizzati dopo ogni componente
2. ✅ **Usa mock mode** - Sviluppa senza credenziali
3. ✅ **Test locali** - Esegui pytest prima di commit

### **Prima di Credenziali:**
1. ✅ **Sviluppa tutto con mock** - 80% del lavoro
2. ✅ **Test automatizzati completi** - Verifica logica
3. ⏳ **Attendi credenziali** - Per test reali

### **Dopo Credenziali:**
1. ✅ **Test immediato autenticazione** - Verifica funziona
2. ✅ **Test end-to-end** - Flusso completo
3. ✅ **Certificazione** - Self-assessment tutorial
4. ✅ **Deploy staging** - Test su ambiente reale
5. ✅ **Deploy produzione** - Solo dopo tutti i test

---

## 📞 Supporto

**Domande sui test?**
- Consulta documentazione Booking.com
- Verifica test esistenti come esempio
- Controlla log per debugging

**Problemi con test automatizzati?**
- Verifica dipendenze installate: `pip install -e ".[dev]"`
- Verifica pytest config: `pytest --version`
- Controlla log errori

---

## ✅ Summary

**Test Automatizzati:**
- ✅ Eseguiti da pytest (CI/CD + locale)
- ✅ Usano mock responses
- ✅ Coprono 80% dei casi
- ✅ Esegui prima di ogni commit

**Test Manuali:**
- ✅ Fai QUANDO hai credenziali Booking.com
- ✅ Fai PER certificazione e edge cases
- ✅ Fai PRIMA di deploy produzione
- ⏳ NON serve durante sviluppo normale con mock

**Workflow Consigliato:**
1. Sviluppa con mock → Test automatizzati
2. Ottieni credenziali → Test manuali autenticazione
3. Test end-to-end → Test manuali completi
4. Certificazione → Test manuali tutorial
5. Deploy → Solo dopo tutti i test passati

