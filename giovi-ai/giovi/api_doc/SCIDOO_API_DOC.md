# Scidoo API - Documentazione Completa

## URL Base
```
https://www.scidoo.com/api/v1/
```

## Autenticazione
L'autenticazione viene effettuata tramite l'header http `Api-Key`, che deve essere presente su ogni chiamata

## Formato richiesta
Lo scambio dei dati avviene metodo POST in formato JSON

**Esempio:**
```
URL: https://www.scidoo.com/api/v1/esempio/get.php
DATA: <contenuto json>
```

## Gestione risposta
In caso di chiamata eseguita correttamente, il server risponde con codice http 200 insieme al contenuto del messaggio di risposta

In caso di parametri errati nella richiesta, viene ritornato un codice http di errore corrispondente (4XX) insieme al messaggio di errore

```json
{
    "message": "invalid number (day_price=<a123>)"
}
```

## Formato dati
- **date:** "YYYY-MM-DD" (es. 2020-01-21)
- **time:** "HH:MM" (es. 12:30)  
- **datetime:** "YYYY-MM-DD HH:MM"
- **number:** 123.45 (float con punto come separatore decimale)
- **boolean:** true o false
- **string:** "testo di esempio"
- **array:** [<dato1>, <dato2>, ..., <datoN>]
- **dict:** [<chiave1> => <valore1>, <chiave2> => <valore2>]

---

# Elenco endpoints

## Account

### /account/getInfo.php
Ritorna informazioni dell'account

**Risposta:**
| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| name | string | nome della licenza |
| email | string | email della licenza |
| website | string | sito internet della licenza |
| properties | array (property) | elenco delle proprietà gestite |

**property:**
| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| id | number | id proprietà |
| name | string | nome proprietà |

**Esempio risposta:**
```json
{
    "name": "Scidoo",
    "email": "abc@scidoo.com", 
    "website": "www.scidoo.com",
    "account_id": "14",
    "properties": [
        {
            "id": 0,
            "name": "Scidoo"
        },
        {
            "id": 42,
            "name": "Webcoom"
        }
    ]
}
```

### /account/request.php
Invia una richiesta di preventivo

**Richiesta:**
| Parametro | Tipo | Descrizione | Obbligatorio |
|-----------|------|-------------|--------------|
| checkin | date | Data e ora di arrivo | ✅ |
| checkout | date | Data e ora di partenza | ✅ |
| customer | customer | Informazioni sul cliente | ✅ |
| adults | number | Numero di adulti | ✅ |
| children_ages | array(number) | Elenco delle età dei bambini | ❌ |
| language | string | Lingua dell'ospite (it, en, fr, ecc.) | ❌ |
| send_hotel_email | boolean | Invia email notifica alla struttura | ❌ |
| send_guest_email | boolean | Invia email copia all'ospite | ❌ |
| additional_rooms | array(additional_room) | Camere aggiuntive | ❌ |
| supplements | array(supplements) | Servizi supplementi | ❌ |

### /account/getEstimates.php
Ritorna la lista dei preventivi

**Richiesta (almeno un parametro):**
| Parametro | Tipo | Descrizione | Obbligatorio |
|-----------|------|-------------|--------------|
| checkin_from | date | Prima data di checkin | ❌ |
| checkin_to | date | Ultima data di checkin (inclusa) | ❌ |
| creation_from | date | Data minima di creazione | ❌ |
| creation_to | date | Data massima di creazione | ❌ |

---

## Alloggi

### /rooms/getRoomTypes.php
Ritorna la lista delle categorie di alloggio

**Risposta:**
| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| id | number | id della categoria |
| name | string | nome della categoria |
| description | string | descrizione della categoria in html |
| size | number | dimensione della stanza (m²) |
| capacity | number | Numero di persone base + letti aggiuntivi |
| additional_beds | number | Numero di letti aggiuntivi |
| images | array (string) | elenco link immagini |

### /rooms/getAvailability.php
Ottiene la disponibilità per categorie in un periodo

**Richiesta:**
| Parametro | Tipo | Descrizione | Obbligatorio |
|-----------|------|-------------|--------------|
| start_date | date | data inizio ricerca | ✅ |
| end_date | date | data fine ricerca | ✅ |

**Risposta:**
```json
{
    "availability": [
        {
            "room_type_id": 1,
            "availability": [
                {
                    "date": "2025-01-01",
                    "available_count": 5,
                    "occupied_count": 2
                }
            ]
        }
    ]
}
```

### /rooms/getRooms.php
Ritorna la lista degli alloggi specifici

**Risposta:**
| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| id | number | id dell'alloggio |
| name | string | nome dell'alloggio |
| room_type_id | number | id della categoria di appartenenza |
| status | number | Stato attuale |

**Stati Camera:**
| Valore | Descrizione |
|--------|-------------|
| 0 | Alloggio Pronto |
| 1 | Alloggio Occupato |
| 2 | Alloggio da Preparare |
| 3 | Alloggio Verificato |
| 4 | Alloggio in Lavorazione |

---

## Prenotazioni

### /bookings/get.php
Ritorna la lista delle prenotazioni

**Richiesta (almeno un parametro):**
| Parametro | Tipo | Descrizione | Obbligatorio |
|-----------|------|-------------|--------------|
| last_modified | boolean | Prenotazioni create/modificate dall'ultima richiesta | ❌ |
| checkin_from | date | Prima data di checkin | ❌ |
| checkin_to | date | Ultima data di checkin (inclusa) | ❌ |
| modified_from | date | Data minima di ultima modifica | ❌ |
| modified_to | date | Data massima di ultima modifica | ❌ |
| id | number | ID della prenotazione | ❌ |

**Risposta reservation:**
| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| id | number | Numero della prenotazione |
| internal_id | number | ID interno della prenotazione |
| creation | datetime | Data di creazione |
| checkin_date | date | Data di checkin |
| checkout_date | date | Data di checkout |
| status | string | Stato della prenotazione |
| room_type_id | string | Codice del tipo di alloggio |
| guest_count | number | Numero di ospiti |
| customer | customer | Informazioni sul cliente |
| guests | array(guest) | Dettaglio degli ospiti |

### /bookings/new.php
Inserisce una o più prenotazioni

**Richiesta:**
```json
{
    "bookings": [
        {
            "external_id": "my_id_123",
            "customer": {
                "first_name": "Mario",
                "last_name": "Rossi",
                "email": "mariorossi@gmail.com",
                "phone": "+393333333333"
            },
            "rooms": [
                {
                    "checkin": "2024-02-12",
                    "checkout": "2024-02-17",
                    "adults": 2,
                    "room_type_id": 1,
                    "price": 4020
                }
            ]
        }
    ]
}
```

### /bookings/getAvailability.php
Controlla disponibilità e prezzi

**Richiesta:**
| Parametro | Tipo | Descrizione | Obbligatorio |
|-----------|------|-------------|--------------|
| checkin | date | Data di checkin | ✅ |
| checkout | date | Data di checkout | ✅ |
| adults | number | Numero di adulti | ✅ |
| children | number | Numero di bambini | ❌ |
| children_ages | array(number) | Età dei bambini | ❌ |

---

## Servizi

### /services/getServices.php
Ritorna la lista dei servizi della struttura

**Risposta:**
| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| id | number | ID del servizio |
| name | string | Nome del servizio |
| description | string | Descrizione del servizio |
| price | number | Prezzo |
| booking_engine | boolean | Servizio prenotabile online |

### /services/getSupplements.php
Ritorna la lista dei supplementi

**Risposta:**
| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| id | number | id del servizio |
| name | string | nome del servizio |

---

## Ospiti

### /guests/getGuestTypes.php
Ritorna la lista dei tipi di ospite

**Risposta:**
```json
[
    {
        "id": "3",
        "name": "Adultos", 
        "min_age": "14",
        "max_age": "60"
    },
    {
        "id": "2",
        "name": "Ragazzo 3-14 Anni",
        "min_age": "3", 
        "max_age": "14"
    }
]
```

---

## Listino

### /prices/getRates.php
Ottiene la lista delle tariffe

**Risposta:**
| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| id | number | id della retta |
| name | string | nome della retta |
| description | string | testo descrittivo della retta |
| room_type_list | array | Categorie collegate alla retta |

---

## Stati prenotazione

| Valore | Descrizione |
|--------|-------------|
| "opzione" | Prenotazione opzionata non confermata |
| "attesa_pagamento" | Prenotazione in attesa del pagamento |
| "confermata_pagamento" | Prenotazione confermata tramite pagamento |
| "confermata_carta" | Prenotazione confermata tramite carta di credito |
| "check_in" | Check-in effettuato |
| "saldo" | Prenotazione saldata |
| "confermata_manuale" | Prenotazione confermata dalla struttura |
| "check_out" | Check-out eseguito |
| "sospesa" | Prenotazione in attesa |
| "annullata" | Prenotazione annullata |
| "eliminata" | Prenotazione eliminata da Scidoo | 