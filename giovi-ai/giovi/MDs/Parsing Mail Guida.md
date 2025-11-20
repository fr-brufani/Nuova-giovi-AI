# Guida Parsing Email OTA

## Obiettivo
Questa guida descrive come identificare e normalizzare i dati chiave provenienti dalle email generate dai diversi canali OTA (Airbnb, Booking.com, Scidoo). L’obiettivo è fornire agli agenti un riferimento unificato per estrarre le informazioni necessarie e popolare lo schema Firestore v2.

## Flusso di parsing (alto livello)
1. **Identifica il canale** in base al dominio mittente / pattern destinatario.
2. **Estrai il payload raw** (plain text o HTML) e applica i parser specifici.
3. **Normalizza i dati** in un oggetto intermedio (`ParsedEmailPayload`).
4. **Esegui il matching** con prenotazioni esistenti (ID prenotazione o conversationId).
5. **Aggiorna Firestore** nelle collezioni target (`reservations`, `properties`, `clients`, `properties/{propertyId}/conversations`).

## Tabella incrociata Airtbnb (conferma vs messaggio)
| Parametro Comune | Mail di Conferma Airbnb | Mail di Notifica Messaggi Airbnb | Ruolo di Collegamento |
| :---- | :---- | :---- | :---- |
| **ID Conversazione (Thread)** | 2311813630(nel link "Invia il messaggio") | 2311813630(nel link "Rispondi") | **L'ID tecnico primario** che collega la prenotazione confermata alla conversazione attiva. |
| **Nome Ospite** | Marie-Thérèse Weber-Gobet | MARIE-THÉRÈSE (Titolare prenotazione) | Il nome dell'ospite è l'elemento umano di collegamento. |
| **Periodo di Soggiorno** | dom 12 ott – dom 19 ott | 12 ottobre 2025 – 19 ottobre 2025 | Le date di check-in e check-out sono identiche. |
| **Alloggio** | IMPERIAL SUITE - PALAZZO DELLA STAFFA | IMPERIAL SUITE - PALAZZO DELLA STAFFA | Il nome della struttura è identico. |

## 1. Airbnb – Mail di Conferma Prenotazione
- **Scopo**: conferma ufficiale della prenotazione.
- **Campi da estrarre**: codice prenotazione (confirmation code), conversationId, nome ospite, periodo soggiorno, struttura.
- **Note**: il confirmation code è presente nel corpo. Conservare anche mittente `automated@airbnb.com` per validazione.

## 2. Airbnb – Mail di Notifica Messaggi
- **Scopo**: avvisa che l’ospite ha scritto nel thread.
- **Campi da estrarre**: conversationId presente nel link “Rispondi”, mittente `reply.airbnb.com`, testo del messaggio.
- **Associazione**: usare conversationId per collegare il messaggio alla prenotazione già registrata (tabella precedente).

## 3. Scidoo – Mail di Conferma Prenotazione
### Campi da estrarre
- ID voucher / prenotazione.
- Stato prenotazione, agenzia di provenienza, timestamp creazione.
- Dati ospite (nome, email guest, telefono), dettagli soggiorno (check-in/out, numero ospiti).
- Dettagli struttura e alloggio, note, importi (totale, extra, commissione).
- Servizi prenotati e stato pagamento (es. PRE-PAID).

### Payload raw di esempio (non modificare)
```
mail di conferma

mittente:

<[reservation@scidoo.com](mailto:reservation@scidoo.com)>

dati da estrarre:

### **📑 Parametri Chiave dalla Prima Email (Conferma Prenotazione Scidoo)**

#### **Dati di Prenotazione**

* **ID Voucher / ID Prenotazione:** `5958915259`  
* **Stato Prenotazione:** `Confermata`  
* **Agenzia Prenotante:** `Booking` (ID 44813)  
* **Data Creazione:** `23 ottobre 2025` alle `11:42`

#### **Dati Ospite**

* **Nome Ospite:** `Brufani Francesco`  
* **Email Ospite (Booking):** `fbrufa.422334@guest.booking.com`  
* **Cellulare Ospite:** `+393315681407`

#### **Dettagli Soggiorno**

* **Data di Check-in:** `15/01/2026`  
* **Data di Check-out:** `18/01/2026`  
* **Ospiti Totali:** `2 Adulti`  
* **Tariffa:** `Pernottamento`

#### **Dettagli Struttura e Alloggio**

* **Struttura Richiesta:** `Piazza Danti Perugia Centro`  
* **Camera/Alloggio:** `1 Suite Maggiore`

#### **Dettagli Finanziari e Servizi**

* **Totale Prenotazione:** `349,55 €`  
* **Totale Retta:** `259,55 €`  
* **Totale Extra:** `90,00 €`  
* **Commissione (Agenzia):** `48.52`  
* **Servizi Prenotati:** `N.3 Pernottamento`, `N.1 Addebito Libero`, `N.1 Pulizia Suite Small`  
* **Note Importanti:** Prenotazione **PRE-PAID** (Pagamento effettuato tramite Bonifico Bancario / BankTransfer).

mail esempio da parsare

Delivered-To: shortdeseos@gmail.com

Received: by 2002:a17:505:2581:10b0:1d27:83a3:6131 with SMTP id x1-n1csp726291njp;

        Thu, 23 Oct 2025 02:42:31 -0700 (PDT)

X-Google-Smtp-Source: AGHT+IGacSAy3OcqEnp6Dfi2hUmge0lH94kGBI5NiIUZglRUb1t9QpjTisdYCAWrMVwJhXJGsKe1

X-Received: by 2002:a05:6000:2284:b0:400:7e60:7ee0 with SMTP id ffacd0b85a97d-42704c8848cmr15564589f8f.0.1761212550857;

        Thu, 23 Oct 2025 02:42:30 -0700 (PDT)

ARC-Seal: i=1; a=rsa-sha256; t=1761212550; cv=none;

        d=google.com; s=arc-20240605;

        b=gW8YilI+lIVnR9DnY68/i47zRaXbfwmYWbVOo9qTM0t8P1R2a/swql7I36jeZhZZWG

         Ft5EthjHS5baowhX2bHFpEYEv+pFIWjDdD8DDduAhSxZ+AjpEdOy2g8Q53NEhyqFdMwc

         EXSO0KQX+PJ0AcrQKw6MZKKKqvDzz0WD0qVj3et4RZr33nfkgyFJkx0aRKkSQjRNlXGj

         BO/f8GRB4FcvZ/Tj6bwhoQZe5DuXGA8tNpOpOd2XwmjcNBxf1qzlnOH20mJRYMlVEBiA

         WdRgLu0I+B+t7kOl5wMGVEtqg2keaZ4NGJhEWL+IG1UyllVef3hZ5bUJIGI2mD97U/rT

         5wWw==

ARC-Message-Signature: i=1; a=rsa-sha256; c=relaxed/relaxed; d=google.com; s=arc-20240605;

        h=mime-version:message-id:list-unsubscribe:from:subject:date:to

         :feedback-id:list-unsubscribe-post:reply-to:origin-messageid

         :dkim-signature;

        bh=N3d1/xtbSWiHQbjQCnZ7WQWKkwG2nr33XW2U8HhSqCo=;

        fh=ZB2BVnsrDn+1LKbb9eEvR7ec8wSVeDXaQ8kKuqyu/MQ=;

        b=K5NJced/9UJ8Z3xhVs/CmyQcTHjwgIcYj/njwf6Ec3idNg4Ma2MOnorDSqdGO2Pe3s

         I0UOMdtaMk6pE8pERmNpygTf87GCWIGit7Wv0TrSBTFiCG73nrVCdz7b+X6bfxtwnp+A

         xCGDeKJxzq8GSWY4TTJgz8KU86CrhUkplN5vAMM7LCmbp10umiJT7ZV7S/Y9mPsN2Cvo

         QTWXKnZcHlOlHSWFVthAW5mFs7XewLXCASru2waAOIcI3Dr2Dbop5MwjMfjcIAwkC+ei

         Zk4WGCkwuH8+ox9U4uAtfB9J+G1W809Vzaq1Xv7mSwN8195344C7i8JG6ga+iR3ERlhW

         VZKQ==;

        dara=google.com

ARC-Authentication-Results: i=1; mx.google.com;

       dkim=pass header.i=@scidoo.com header.s=mail header.b=WyfOZgZr;

       spf=pass (google.com: domain of bounces-91910830-4256376833@email.scidoo.com designates 212.146.252.118 as permitted sender) smtp.mailfrom=bounces-91910830-4256376833@email.scidoo.com;

       dmarc=pass (p=NONE sp=NONE dis=NONE) header.from=scidoo.com

Return-Path: <bounces-91910830-4256376833@email.scidoo.com>

Received: from email.scidoo.com (email.scidoo.com. [212.146.252.118])

        by mx.google.com with ESMTPS id ffacd0b85a97d-4298990c3adsi850096f8f.817.2025.10.23.02.42.30

        for <shortdeseos@gmail.com>

        (version=TLS1_3 cipher=TLS_AES_256_GCM_SHA384 bits=256/256);

        Thu, 23 Oct 2025 02:42:30 -0700 (PDT)

Received-SPF: pass (google.com: domain of bounces-91910830-4256376833@email.scidoo.com designates 212.146.252.118 as permitted sender) client-ip=212.146.252.118;

Authentication-Results: mx.google.com;

       dkim=pass header.i=@scidoo.com header.s=mail header.b=WyfOZgZr;

       spf=pass (google.com: domain of bounces-91910830-4256376833@email.scidoo.com designates 212.146.252.118 as permitted sender) smtp.mailfrom=bounces-91910830-4256376833@email.scidoo.com;

       dmarc=pass (p=NONE sp=NONE dis=NONE) header.from=scidoo.com

DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; d=scidoo.com; q=dns/txt; s=mail; bh=N3d1/xtbSWiHQbjQCnZ7WQWKkwG2nr33XW2U8HhSqCo=; h=from:reply-to:subject:date:to:mime-version:content-type:list-unsubscribe:x-csa-complaints:list-unsubscribe-post:message-id:x-sib-id:feedback-id;

        b=WyfOZgZrMqrLp++36GBqnRcvaPhY0+dpfb4qlJakw6P2vRP/FBcy343vRkjyC5qfpobngAYe7GDC

        TGrisX6+aXta9cDjX9y7naHPxXK1lLyvusnnt4ZlQPg04opXHygXh2la1dzzFLLxx2svhlTHA+de

        +oe7smw3p4F2XYmX88g=

Origin-messageId: <202510230942.72553680763@smtp-relay.mailin.fr>

Reply-To: <reservation@scidoo.com>

List-Unsubscribe-Post: List-Unsubscribe=One-Click

Feedback-ID: 212.146.199.187:2694517_-1:2694517:Sendinblue

To: <shortdeseos@gmail.com>

Date: Thu, 23 Oct 2025 09:42:29 +0000

Subject: Confermata - Prenotazione ID 5958915259 - Booking

From: Scidoo Booking Manager <reservation@scidoo.com>

List-Unsubscribe: <https://r.email.scidoo.com/tr/un/li/MCxTswt93_FMj-JSa62UdgK1IsAnAnoJs9Zds41eoM4i4pgs_oVQDK-p3NDSSVY-XS0b6f1IvccQYb9nKmIx6s7_Qmd9OTKU7bLrfxlIuaW0XLtBumz0l3k4K119gmTftE66Mv_X_I2uMR2nBQg7EDelBamypMKd3-RUV_R4Kj4womawDSIVv8khUv_Yg1LNeMNDj1BLuvDre9r_ECk8TclSuLsjREwHIFIpXug>

X-CSA-Complaints: csa-complaints@eco.de

X-Mailin-EID: OTE5MTA4MzB%2Bc2hvcnRkZXNlb3NAZ21haWwuY29tfjwyMDI1MTAyMzA5NDIuNzI1NTM2ODA3NjNAc210cC1yZWxheS5tYWlsaW4uZnI%2BfmVtYWlsLnNjaWRvby5jb20%3D

X-sib-id: YGIYw-qtbjq_UMym2uvqBDp1xhQaeBXvoBVL8RLKGlAeeqpgp49khRiH_yw-V56VcyFNRXVo0q2qXbvbI4dJxRRkQ2_9gV6W4d9txOt4k5vcnG3V46N3dlobNAVqhH-iJhEo8Nfw-rxRUGrSpD6mhFvSSsOY004iCYXNkBLRdQG6gaU

Message-Id: <202510230942.72553680763@smtp-relay.mailin.fr>

Content-Type: multipart/alternative; boundary=d0f619190f98c5d9ad868dadafd7017c04575fbbda18d99e7bdb312dfceb

Mime-Version: 1.0

X-Api-Version: v3

--d0f619190f98c5d9ad868dadafd7017c04575fbbda18d99e7bdb312dfceb

Content-Transfer-Encoding: quoted-printable

Content-Type: text/plain; charset=utf-8

Agenzia Prenotante=0944813 -> Booking

ID Voucher=095958915259

Camera/Alloggio=091 Suite Maggiore

Struttura Richiesta=09Piazza Danti Perugia Centro

Stato Prenotazione=09Confermata

Tariffa=09Pernottamento

Ospiti=092 Adulti

Prezzo=09349,55

Nome Ospite=09Brufani Francesco

Data di Check-in=0915/01/2026

Data di Check-out=0918/01/2026

Commissione=0948.52

---------------------------------------------------------------

Servizi Prenotati

N.3 Pernottamento

N.3 Pernottamento

N.1 Addebito Libero

N.1 Pulizia Suite Small

---------------------------------------------------------------

Conto:

---------------------------------------------------------------

Totale Retta: 259,55=E2=82=AC

Totale Extra: 90,00=E2=82=AC

Totale Prenotazione: 349,55 =E2=82=AC

Dati Ospite

Email:fbrufa.422334@guest.booking.com

Telefono:

Cellulare:+393315681407

---------------------------------------------------------------

Note:

Booker Genius - BankTransfer - ** THIS RESERVATION HAS BEEN PRE-PAID ** BOO=

KING NOTE : Payment charge is EUR 4.04325 LANGUAGE: IT

--d0f619190f98c5d9ad868dadafd7017c04575fbbda18d99e7bdb312dfceb

Content-Transfer-Encoding: quoted-printable

Content-Type: text/html; charset=utf-8

<html><head></head><body><img width=3D"1" height=3D"1" src=3D"https://r.ema=

il.scidoo.com/tr/op/V-YMZ

mail messaggi utente da booking a cui rispondere

mail mittente (costante il suffisso [@mchat.booking.com](mailto:5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com))

| [5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com](mailto:5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com) mail da pasare tipo: Delivered-To: shortdeseos@gmail.com Received: by 2002:a17:505:2581:10b0:1d27:83a3:6131 with SMTP id x1-n1csp726620njp;         Thu, 23 Oct 2025 02:43:29 -0700 (PDT) X-Google-Smtp-Source: AGHT+IFb1Y24YzLq51VZWYyzLIEh/hz1v9MGLL4/Ir1AZ+1UENJdQg7bktWlVekJBCtpxfqXTQq/ X-Received: by 2002:a17:906:a20f:b0:b6d:2d06:bd82 with SMTP id a640c23a62f3a-b6d2d06f024mr632247366b.25.1761212609449;         Thu, 23 Oct 2025 02:43:29 -0700 (PDT) ARC-Seal: i=1; a=rsa-sha256; t=1761212609; cv=none;         d=google.com; s=arc-20240605;         b=V26hpJ/MxrHrAoKpPMBj4kxRUaQmiH6ks3ggWTlTezWqANZeSuBOPJtxqvT6bA3ay7          CrsRpf7fJNE5y/03gQaJy26v0osBPMHE2StzkyCXiDAsqpTDXorCi9J4sl0P1u31fJ3j          Mh7gbnIzl2X2OtKPn8cKXiSZj559xVDO/1admGs8prrR3QB+qTwbjMEOAqKo7DJv0EVN          rojRwW2Ewy7Rzqg8xlLaoS/BEhzF3YrbWSJQfB2dIn2qYkEAZKJMEpSSxCHGQ3llQLVS          w2m8tOmVm6w9adVMDxvpppRT0K+WeNLSu9Ue7b4NjLGAJZL68/fvzislQ8kJV3g2kh4J          aoNg==;         dara=google.com ARC-Authentication-Results: i=1; mx.google.com;        dkim=pass header.i=@mchat.booking.com header.s=bk header.b="JAbeD/nk";        spf=pass (google.com: domain of 5958915259-5sohk3qnf9yihbv5y31kzi0p5.2stir9myhhtxl7m69m0y4jiuq@mchat.booking.com designates 37.10.30.3 as permitted sender) smtp.mailfrom=5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com;        dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=mchat.booking.com Return-Path: <5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com> Received: from mailout-202-r2.booking.com (mailout-202-r2.booking.com. [37.10.30.3])         by mx.google.com with ESMTPS id a640c23a62f3a-b6d51468ce5si100883166b.846.2025.10.23.02.43.29         for <shortdeseos@gmail.com>         (version=TLS1_3 cipher=TLS_AES_256_GCM_SHA384 bits=256/256);         Thu, 23 Oct 2025 02:43:29 -0700 (PDT) Received-SPF: pass (google.com: domain of 5958915259-5sohk3qnf9yihbv5y31kzi0p5.2stir9myhhtxl7m69m0y4jiuq@mchat.booking.com designates 37.10.30.3 as permitted sender) client-ip=37.10.30.3; Authentication-Results: mx.google.com;        dkim=pass header.i=@mchat.booking.com header.s=bk header.b="JAbeD/nk";        spf=pass (google.com: domain of 5958915259-5sohk3qnf9yihbv5y31kzi0p5.2stir9myhhtxl7m69m0y4jiuq@mchat.booking.com designates 37.10.30.3 as permitted sender) smtp.mailfrom=5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com;        dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=mchat.booking.com DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; s=bk; d=mchat.booking.com; h=Content-Transfer-Encoding:Content-Type:MIME-Version:Date:Sender:Subject: From:Reply-To:To:Message-Id; i=5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com; bh=EJIM4E3C35sY5p9mTnvTSKOSROWTFabBxmu6r/2LLRg=; b=JAbeD/nkO1ohU1Pg6wwUI0jJxwV3bb4ukPZm/kAEf3mXVpYIf0Il5jw9KuRjFayn6bLyc1kYGTD1    cqE6mrYEgcEvkmnMPsbdmeUN/+fyGF+UcJxAlhWAC/DnGmFd/O0SjmvHPSmjzQUZd783v7x12b1c    ZbIMtB8Fr1y599cNixU= Content-Transfer-Encoding: binary Content-Type: multipart/alternative; boundary="_----------=_1761212608489324" MIME-Version: 1.0 Date: Thu, 23 Oct 2025 11:43:28 +0200 Sender: "Francesco Brufani via Booking.com" <5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com> Subject: Abbiamo ricevuto questo messaggio da Francesco Brufani From: "Francesco Brufani via Booking.com" <5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com> Reply-To: 5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com To: shortdeseos@gmail.com X-Bme-Id: 34955536433 Message-Id: <4csh1D6VbLzy5Z@mailrouter-601.fra3.prod.booking.com> --_----------=_1761212608489324 Content-Transfer-Encoding: base64 Content-Type: text/plain; charset=utf-8 Date: Thu, 23 Oct 2025 11:43:28 +0200 ICAgIyMtIFNjcml2aSBsYSB0dWEgcmlzcG9zdGEgc29wcmEgcXVlc3RhIHJpZ2EgLSMjCgogICAg ICAgICAgICAgICAgICAgICAgIE51bWVybyBkaSBjb25mZXJtYTogNTk1ODkxNTI1OQoKICAgICAg ICAgICAgICAgICAgICAgICAgTnVvdm8gbWVzc2FnZ2lvIGRhIHVuIG9zcGl0ZQoKICAgICAgICA   |  |

| :---- | ----- |

### **🎯 Parametro Identico e Affidabile**

| Parametro | Email Scidoo | Email Booking.com | Coerenza |
| :---- | :---- | :---- | :---- |
| **ID Prenotazione** | **5958915259** (ID Voucher) | **5958915259** (Numero di conferma) | **Identico al 100%** |

## 4. Booking.com – Messaggi Chat (dominio `mchat.booking.com`)
- **Scopo**: conversazione tra ospite e host tramite Booking.com.
- **Campi da estrarre**: mittente (indirizzo `@mchat.booking.com`), ID prenotazione incorporato nell’indirizzo, testo messaggio, timestamp.
- **Associazione**: utilizzare ID prenotazione per recuperare prenotazione/cliente e salvare il messaggio nella conversazione (`properties/{propertyId}/conversations`).
- **Nota**: l’esempio è incluso nel payload raw sopra; il parser deve distinguere la sezione Booking.com dalla porzione Scidoo.

## 5. Mapping verso Firestore v2
| Campo normalizzato | Collezione target | Note |
| --- | --- | --- |
| `reservationId`, `stayPeriod`, `status`, `channel` | `reservations/{reservationId}` | Upsert; link a `hostId`, `propertyId`, `clientId`. |
| `clientEmail`, `clientPhone`, `guestName` | `clients/{clientId}` | Aggiornare/creare cliente; salvare mapping email booking. |
| `propertyName`, `propertyExternalRef` | `properties/{propertyId}` | Usare per lookup o creazione se mancante. |
| `messageText`, `channel`, `sourceEmailId` | `properties/{propertyId}/conversations/{clientId}/messages/{messageId}` | `messageId` può essere l’header `Message-Id`. |
| `importMetadata` (provider, raw headers) | `integrations/email/{emailId}` | Conservare info debug, historyId Gmail. |

---
Questa struttura fornisce tutte le informazioni necessarie agli agenti per implementare o aggiornare i parser, mantenendo inalterati gli esempi raw di riferimento.



