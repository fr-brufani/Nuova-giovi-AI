# 🧪 Test Suite per PMS Sync Service

Questa cartella contiene tutti i test per le varie integrazioni PMS (Property Management System).

## 📁 Struttura

```
test/
├── smoobu/           # Test per integrazione Smoobu
│   ├── test_smoobu_user.js              # Recupera info utente e appartamenti
│   ├── test_webhook_smoobu.js           # Simula webhook localmente
│   ├── test_smoobu_create_booking.js    # Crea prenotazioni via API
│   └── README_SMOOBU_TEST.md            # Guida completa test Smoobu
├── scidoo/           # Test per integrazione Scidoo (futuro)
└── README.md         # Questo file
```

## 🚀 Come Eseguire i Test

### Test Smoobu

Dalla cartella principale `pms-sync-service`:

```bash
# Test info utente e appartamenti
node test/smoobu/test_smoobu_user.js

# Test webhook locali
node test/smoobu/test_webhook_smoobu.js

# Test creazione prenotazioni
node test/smoobu/test_smoobu_create_booking.js --complete
```

### Test Scidoo

I test per Scidoo verranno aggiunti quando l'integrazione sarà implementata.

## ⚠️ Prerequisiti

1. **Installa dipendenze**: `npm install`
2. **Compila il progetto**: `npm run build`  
3. **Avvia il servizio**: `npm start`
4. **Configura credenziali** nei file di test

## 📖 Documentazione

Per istruzioni dettagliate su ogni integrazione, consulta i README specifici in ogni cartella. 