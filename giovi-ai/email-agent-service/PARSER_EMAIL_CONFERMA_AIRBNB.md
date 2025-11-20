# Parser Email Conferma Prenotazione Airbnb

## Panoramica

Il sistema utilizza **un unico parser** (`AirbnbConfirmationParser`) per processare tutte le email di conferma Airbnb, sia quelle **con messaggio guest allegato** che quelle **senza messaggio**.

## Funzionamento del Parser

### 1. Identificazione Email

Il parser riconosce le email di conferma Airbnb tramite:
- **Sender**: `automated@airbnb.com` (verificato con `is_airbnb_sender()`)
- **Subject**: contiene "prenotazione confermata" o "arriverà"

### 2. Estrazione Dati Prenotazione

Per **tutte** le email (con o senza messaggio), il parser estrae:

- **Reservation ID**: dal codice di conferma nel subject o dai link `/hosting/reservations/details/`
- **Thread ID**: dal link `/hosting/thread/`
- **Property Name**: con logica avanzata che esclude messaggi guest confusi con il nome property
- **Guest Name**: dal subject o dal testo (pattern "Nome arriverà")
- **Check-in / Check-out**: con supporto per date sulla stessa riga o su righe separate
- **Adulti**: numero ospiti
- **Importo totale**: con valuta (EUR)

### 3. Estrazione Messaggio Guest (se presente)

La funzione `extract_guest_message_from_confirmation()` cerca il messaggio:

**Pattern di ricerca:**
- Messaggio che inizia con "Ciao", "Hallo", "Siamo", "Desideriamo", "Viaggiamo", "Non vediamo l'ora"
- Il messaggio si trova **prima** del link `https://www.airbnb.it/rooms/...`
- Se presente "Tradotto automaticamente", il messaggio è prima di questa sezione

**Pulizia messaggio:**
- Rimozione spazi multipli
- Rimozione prefissi comuni ("Ciao", "Hallo")
- Rimozione suffissi comuni ("Non vediamo l'ora", "Vi salutiamo")
- Lunghezza minima: 20 caratteri

### 4. Output del Parser

Il parser restituisce sempre un `ParsedEmail` con:
- `kind = "airbnb_confirmation"`
- `reservation`: oggetto `ReservationInfo` con tutti i dati della prenotazione
- `guestMessage`: 
  - `None` se non c'è messaggio
  - `GuestMessageInfo` se c'è un messaggio (con reservationId, message, replyTo, threadId, guestName)

## Processamento Post-Parsing

### Email SENZA Messaggio

1. **Salvataggio prenotazione**: i dati vengono salvati in Firestore (property, client, reservation)
2. **Fine**: nessun ulteriore processamento

### Email CON Messaggio

1. **Salvataggio prenotazione**: come sopra
2. **Verifica auto-reply**:
   - Controlla flag host `autoReplyToNewReservations` (per nuove prenotazioni)
   - Controlla flag client `autoReplyEnabled`
3. **Se auto-reply abilitato**:
   - Estrazione contesto (property, reservation, client)
   - Salvataggio messaggio in conversazione (`conversations/{client_id}/messages`)
   - Il messaggio viene poi processato dalla pipeline AI per generare risposta

## Differenze Chiave

| Aspetto | Email SENZA Messaggio | Email CON Messaggio |
|---------|----------------------|---------------------|
| **Parser** | Stesso (`AirbnbConfirmationParser`) | Stesso (`AirbnbConfirmationParser`) |
| **Estrazione dati** | Completa | Completa + messaggio guest |
| **Salvataggio** | Solo prenotazione | Prenotazione + messaggio in conversazione |
| **Auto-reply** | Non applicabile | Condizionale (se abilitato) |

## Ottimizzazioni Parsing

### Property Name

Il parser usa pattern avanzati per evitare di confondere messaggi guest con il nome property:
- Esclude testi che contengono: "arriverà", "confermata", "Ciao", "Siamo", "Desideriamo", ecc.
- Cerca il property name **dopo** il link alla room (dove non ci sono messaggi)
- Pattern preferito: `"MAGGIORE SUITE - DUOMO DI PERUGIA"` (tutto maiuscolo con trattino)

### Date Check-in/Check-out

Gestisce vari formati:
- Stessa riga: `"Check-in gio 3 set 2026"`
- Righe separate: `"Check-in\n\ngio 3 set 2026"`
- Stessa riga con spazi multipli: `"Check-in         Check-out\ngio 3 set 2026   sab 5 set 2026"`
- Con o senza anno (se senza anno, usa anno corrente/prossimo)

## Flusso Completo

```
Email Gmail
    ↓
AirbnbConfirmationParser.parse()
    ↓
├─ Estrazione dati prenotazione (sempre)
└─ Estrazione messaggio guest (se presente)
    ↓
ParsedEmail
    ├─ reservation: ReservationInfo
    └─ guestMessage: GuestMessageInfo | None
    ↓
BackfillService / GmailWatchService
    ↓
├─ Salvataggio prenotazione (sempre)
└─ Se guestMessage presente:
    ├─ Verifica auto-reply abilitato
    ├─ Estrazione contesto
    └─ Salvataggio in conversazione
```

## Note Importanti

1. **Un solo parser**: non ci sono 2 sistemi separati, ma un unico parser che gestisce entrambi i casi
2. **Estrazione condizionale**: il messaggio guest viene estratto solo se presente, altrimenti `guestMessage = None`
3. **Processamento condizionale**: il messaggio viene processato per auto-reply solo se:
   - È presente (`guestMessage != None`)
   - L'host ha abilitato `autoReplyToNewReservations` (per nuove prenotazioni)
   - Il client ha abilitato `autoReplyEnabled`

