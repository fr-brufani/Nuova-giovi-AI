Mail di conferma prenotazione Booking


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

il.scidoo.com/tr/op/V-YMZI6Ljuv6J5uGTbAEFe6mJqLHkzI3_e3q6jGq84Fpfw-ALv-F-4v=

KmfcW-vz1WlCr3RhJkJfetKp0SorIcPzWaIvDX3Ivoivbkaa-hBELQtHl9GI3igKT8wMpT8fOz5=

NAHdvKfTM7RK16hNTX7SpwXLb6c2jI-VlTUZpp1mFC_gqnOHDW-_pKqU9pftu0gOWlg_dmG9vA5=

2JaBDV80rI" style=3D"mso-hide:all"/>



=09<style>

=09.table{border-collapse:coollapse;}

=09.table th{background:#f1f1f1; border:solid 1px #cccccc; width:150px; hei=

ght:30px; text-align:left;}

=09.table td{ border:solid 1px #cccccc; padding:4px; text-align:left;}

=09</style>



=09<div style=3D"line-height:16px; font-size:15px;">



=09<table class=3D"table" cellspacing=3D"0">

=09=09<tbody><tr><th>Agenzia Prenotante</th><td>44813 -&gt; Booking</td></t=

r>

=09=09<tr><th>ID Voucher</th><td>5958915259</td></tr>

=09=09<tr><th>Camera/Alloggio</th><td>1 Suite Maggiore</td></tr>

=09=09<tr><th>Struttura Richiesta</th><td>Piazza Danti Perugia Centro</td><=

/tr>

=09=09<tr><th>Stato Prenotazione</th><td>Confermata</td></tr>

=09=09<tr><th>Tariffa</th><td>Pernottamento</td></tr>

=09=09<tr><th>Ospiti</th><td>2 Adulti</td></tr>

=09=09<tr><th><strong>Prezzo</strong></th><td>349,55</td></tr>

=09</tbody></table><br/><br/>





=09<table class=3D"table" cellspacing=3D"0">

=09=09<tbody><tr><th>Nome Ospite</th><td>Brufani Francesco</td></tr>

=09=09<tr><th>Data di Check-in</th><td>15/01/2026</td></tr>

=09=09<tr><th>Data di Check-out</th><td>18/01/2026</td></tr>

=09=09<tr><th>Commissione</th><td>48.52</td></tr>

=09</tbody></table><br/><hr/>

<br/>



=09<strong>Servizi Prenotati</strong><br/><br/>N.3 Pernottamento<br/>N.3 Pe=

rnottamento<br/>N.1 Addebito Libero<br/>N.1 Pulizia Suite Small<br/><hr/>

<strong>Conto:</strong><br/><hr/><br/>Totale Retta: 259,55=E2=82=AC=

<br/>Totale Extra: 90,00=E2=82=AC<br/><strong>Totale Prenotazione: 349,55 =

=E2=82=AC</strong><br/><br/>



=09<strong>Dati Ospite</strong><br/><br/>

=09Email:fbrufa.422334@guest.booking.com<br/>

=09Telefono:<br/>

=09Cellulare:+393315681407<br/><hr/><br/><strong>Note:</strong><br/><br/> B=

ooker Genius - BankTransfer - ** THIS RESERVATION HAS BEEN PRE-PAID ** BO=

OKING NOTE : Payment charge is EUR 4.04325 LANGUAGE: IT

</div></body></html>



--d0f619190f98c5d9ad868dadafd7017c04575fbbda18d99e7bdb312dfceb--





Mail ricezione messaggio Booking



Delivered-To: shortdeseos@gmail.com

Received: by 2002:a17:505:2581:10b0:1d27:83a3:6131 with SMTP id x1-n1csp726620njp;

Thu, 23 Oct 2025 02:43:29 -0700 (PDT)

X-Google-Smtp-Source: AGHT+IFb1Y24YzLq51VZWYyzLIEh/hz1v9MGLL4/Ir1AZ+1UENJdQg7bktWlVekJBCtpxfqXTQq/

X-Received: by 2002:a17:906:a20f:b0:b6d:2d06:bd82 with SMTP id a640c23a62f3a-b6d2d06f024mr632247366b.25.1761212609449;

Thu, 23 Oct 2025 02:43:29 -0700 (PDT)

ARC-Seal: i=1; a=rsa-sha256; t=1761212609; cv=none;

d=google.com; s=arc-20240605;

b=V26hpJ/MxrHrAoKpPMBj4kxRUaQmiH6ks3ggWTlTezWqANZeSuBOPJtxqvT6bA3ay7

CrsRpf7fJNE5y/03gQaJy26v0osBPMHE2StzkyCXiDAsqpTDXorCi9J4sl0P1u31fJ3j

Mh7gbnIzl2X2OtKPn8cKXiSZj559xVDO/1admGs8prrR3QB+qTwbjMEOAqKo7DJv0EVN

rojRwW2Ewy7Rzqg8xlLaoS/BEhzF3YrbWSJQfB2dIn2qYkEAZKJMEpSSxCHGQ3llQLVS

w2m8tOmVm6w9adVMDxvpppRT0K+WeNLSu9Ue7b4NjLGAJZL68/fvzislQ8kJV3g2kh4J

aoNg==

ARC-Message-Signature: i=1; a=rsa-sha256; c=relaxed/relaxed; d=google.com; s=arc-20240605;

h=message-id:to:reply-to:from:subject:sender:date:mime-version

:content-transfer-encoding:dkim-signature;

bh=EJIM4E3C35sY5p9mTnvTSKOSROWTFabBxmu6r/2LLRg=;

fh=XBTByGVyCMihm8LvqfNCIEQ1zKLApuAOsFeBQLo6miw=;

b=aOBwE3nhHoE9o78fHe9dXhr58CB8o8ZkYRY3nV0z+8utMj93SvCVd9kUI3u1HOXBhu

jF28H7jPg/6+3rV6Rc9C7TffJ5CuZu0Z7DVMJ0j7nwdVnSlKvT0WHnYIEj7nFmZ8O47S

aeRGDHfTv/mRMEpHGs1tBngX3Rm+4r4tCIc5Ul9WOh7RziRNU61wXUeIvATlxGTt6UWE

av6wcWeQciyAh6I7JdAX9P9WHLyaKjskXYBmbSJ8ZJRgegjrrE0jHHZO+zUgyRs4kDSE

GkjZT5FgWKqwaquh8fKdGhETJA1LI1SagOU3LQFwROrNz9ANkwfndK3FqqKJofdHukzy

tYrg==;

dara=google.com

ARC-Authentication-Results: i=1; mx.google.com;

dkim=pass header.i=@mchat.booking.com header.s=bk header.b="JAbeD/nk";

spf=pass (google.com: domain of 5958915259-5sohk3qnf9yihbv5y31kzi0p5.2stir9myhhtxl7m69m0y4jiuq@mchat.booking.com designates 37.10.30.3 as permitted sender) smtp.mailfrom=5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com;

dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=mchat.booking.com

Return-Path: <5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com>

Received: from mailout-202-r2.booking.com (mailout-202-r2.booking.com. [37.10.30.3])

by mx.google.com with ESMTPS id a640c23a62f3a-b6d51468ce5si100883166b.846.2025.10.23.02.43.29

for <shortdeseos@gmail.com>

(version=TLS1_3 cipher=TLS_AES_256_GCM_SHA384 bits=256/256);

Thu, 23 Oct 2025 02:43:29 -0700 (PDT)

Received-SPF: pass (google.com: domain of 5958915259-5sohk3qnf9yihbv5y31kzi0p5.2stir9myhhtxl7m69m0y4jiuq@mchat.booking.com designates 37.10.30.3 as permitted sender) client-ip=37.10.30.3;

Authentication-Results: mx.google.com;

dkim=pass header.i=@mchat.booking.com header.s=bk header.b="JAbeD/nk";

spf=pass (google.com: domain of 5958915259-5sohk3qnf9yihbv5y31kzi0p5.2stir9myhhtxl7m69m0y4jiuq@mchat.booking.com designates 37.10.30.3 as permitted sender) smtp.mailfrom=5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com;

dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=mchat.booking.com

DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; s=bk; d=mchat.booking.com; h=Content-Transfer-Encoding:Content-Type:MIME-Version:Date:Sender:Subject: From:Reply-To:To:Message-Id; i=5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com; bh=EJIM4E3C35sY5p9mTnvTSKOSROWTFabBxmu6r/2LLRg=; b=JAbeD/nkO1ohU1Pg6wwUI0jJxwV3bb4ukPZm/kAEf3mXVpYIf0Il5jw9KuRjFayn6bLyc1kYGTD1

cqE6mrYEgcEvkmnMPsbdmeUN/+fyGF+UcJxAlhWAC/DnGmFd/O0SjmvHPSmjzQUZd783v7x12b1c

ZbIMtB8Fr1y599cNixU=

Content-Transfer-Encoding: binary

Content-Type: multipart/alternative; boundary="_----------=_1761212608489324"

MIME-Version: 1.0

Date: Thu, 23 Oct 2025 11:43:28 +0200

Sender: "Francesco Brufani via Booking.com" <5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com>

Subject: Abbiamo ricevuto questo messaggio da Francesco Brufani

From: "Francesco Brufani via Booking.com" <5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com>

Reply-To: 5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com

To: shortdeseos@gmail.com

X-Bme-Id: 34955536433

Message-Id: <4csh1D6VbLzy5Z@mailrouter-601.fra3.prod.booking.com>



--_----------=_1761212608489324

Content-Transfer-Encoding: base64

Content-Type: text/plain; charset=utf-8

Date: Thu, 23 Oct 2025 11:43:28 +0200



ICAgIyMtIFNjcml2aSBsYSB0dWEgcmlzcG9zdGEgc29wcmEgcXVlc3RhIHJpZ2EgLSMjCgogICAg

ICAgICAgICAgICAgICAgICAgIE51bWVybyBkaSBjb25mZXJtYTogNTk1ODkxNTI1OQoKICAgICAg

ICAgICAgICAgICAgICAgICAgTnVvdm8gbWVzc2FnZ2lvIGRhIHVuIG9zcGl0ZQoKICAgICAgICAg

ICAgICAgICAgICAgICAgRnJhbmNlc2NvIEJydWZhbmkgaGEgc2NyaXR0bzoKCiAgICAgICAgICAg

ICAgICAgICAgICBDaWFvIMOoIHBvc3NpYmlsZSBwb3J0YXJlIHVuIGNhbmU/CgogICBSaXNwb25k

aQoKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIC0tPgogICBodHRwczovL2Fk

bWluLmJvb2tpbmcuY29tL2hvdGVsL2hvdGVsYWRtaW4vZXh0cmFuZXRfbmcvbWFuYWdlL21lc3Nh

Z2luZwogICAvaW5ib3guaHRtbD9tZXNzYWdlX2lkPTVmNjhhNTYwLWFmZjQtMTFmMC05N2UyLTdk

YmNjYzAyZTExNCZsYW5nPWl0JmhvdAogICBlbF9pZD0xMTcyMjU2OSZyZXNfaWQ9NTk1ODkxNTI1

OSZwcm9kdWN0X3R5cGU9UE9TVF9CT09LSU5HJmZyb21faW5zdGFudAogICBfZW1haWw9MSZwcm9k

dWN0X2lkPTU5NTg5MTUyNTkmdXRtX2NhbXBhaWduPXBmX2d1ZXN0X3JlcXVlc3QmdXRtX21lZGl1

bQogICA9ZW1haWwmdXRtX3Rlcm09ZnJlZV90ZXh0JnV0bV9zb3VyY2U9bWVzc2FnaW5nJnV0bV9j

b250ZW50PXJlcGx5Jl9lPTE3NgogICAgICAgICAgIDEyMTI2MDgmX3M9ZHF4dkh2Vk5GR1l6bnhz

eVFEc0hPelRoYUNpSWRnS1huc0dBNFNUVnBsNAoKICAgRGF0aSBkZWxsYSBwcmVub3RhemlvbmUK

CiAgIE5vbWUgZGVsbCdvc3BpdGU6CiAgIEZyYW5jZXNjbyBCcnVmYW5pCgogICBDaGVjay1pbjoK

ICAgZ2lvIDE1IGdlbiAyMDI2CgogICBDaGVjay1vdXQ6CiAgIGRvbSAxOCBnZW4gMjAyNgoKICAg

Tm9tZSBzdHJ1dHR1cmE6CiAgIE1hZ2dpb3JlIFN1aXRlIC0gRHVvbW8gZGkgUGVydWdpYQoKICAg

TnVtZXJvIGRpIHByZW5vdGF6aW9uZToKICAgNTk1ODkxNTI1OQoKICAgT3NwaXRpIHRvdGFsaToK

ICAgMgoKICAgVG90YWxlIGRlbGxlIGNhbWVyZToKICAgMQoKICAgwqkgQ29weXJpZ2h0IEJvb2tp

bmcuY29tIDIwMjUKICAgUXVlc3RhIGUtbWFpbCB0aSDDqCBzdGF0YSBpbnZpYXRhIGRhIEJvb2tp

bmcuY29tCgogICBBbCBtb21lbnRvLCBsYSB0dWEgaXNjcml6aW9uZSBhbGxhIG5ld3NsZXR0ZXIg

ZGkgQm9va2luZy5jb20gw6ggYXR0aXZhLgogICBTYXBldmkgY2hlIHB1b2kgbW9kaWZpY2FyZSBs

ZSB0dWUgcHJlZmVyZW56ZSBlIGltcG9zdGFyZSBsZSByaXNwb3N0ZQogICBhdXRvbWF0aWNoZSBw

ZXIgYWxjdW5pIG1lc3NhZ2dpIGRlZ2xpIG9zcGl0aT8KCiAgIFF1ZXN0YSBlLW1haWwgw6ggc3Rh

dGEgaW52aWF0YSBhOiBzaG9ydGRlc2Vvc0BnbWFpbC5jb20KICAgICAgICAgICAgICAgICAgICAg

ICAgICBNb2RpZmljYSBsZSB0dWUgcHJlZmVyZW56ZQoKICAgKkJvb2tpbmcuY29tIHJpY2V2ZXLD

oCBlZCBlbGFib3JlcsOgIGxlIHJpc3Bvc3RlIGEgcXVlc3RhIGUtbWFpbCwgY29tZQogICBzcGVj

aWZpY2F0byBuZWxsJ0luZm9ybWF0aXZhIHN1bGxhIFByaXZhY3kgZSBzdWkgQ29va2llIGRpIEJv

b2tpbmcuY29tLgogICBJbCBjb250ZW51dG8gZGkgcXVlc3RvIG1lc3NhZ2dpbyBub24gw6ggc3Rh

dG8gZ2VuZXJhdG8gZGEgQm9va2luZy5jb20sCiAgIHF1aW5kaSBCb29raW5nLmNvbSBub24gbmUg

w6ggcmVzcG9uc2FiaWxlLgoKCgogICBbZW1haWxfb3BlbmVkX3RyYWNraW5nX3BpeGVsP2xhbmc9

aXQmYW1wO2FpZD0zMDQxNDImYW1wO3Rva2VuPTUyNjE2ZTY0NgogICBmNmQ0OTU2MjQ3MzY0NjUy

MzI4N2Q2MWZkNGVhMTg2NjM5NmUzNDM1MmQ0MGJkYTcyZTljYzQ3YTNmNzc3NzE0Y2NkMjAxMAog

ICA2MDFjYzc3ZDY4MDRhYzYxODlkYmI5M2U2NmJhYTkxNjQ0NGQzZTNlMTdhZTQzMDEyMmY0Njk1

N2FlNThiZjEzM2RiZDg0YgogICA1YmQ5Mjg3NjdjMzViMjQ5OTRmNTM5YTczMmY5NjIxOTZhNGM0

MjcwOTBiN2E0NmRlOGNhNWU0YmJhOWMxZjhmM2VmY2ZhNAogICBkOTBiYzdhNmQzMGJkMGYwZGVi

MThmNzZmMmQzMzJkYWZmNTViOWRjNjA5ZTc5Mzk0OSZhbXA7dHlwZT10b19ob3RlbF9mcgogICBl

ZV90ZXh0XQo=

--_----------=_1761212608489324

Content-Type: multipart/related; boundary="_----------=_1761212608489325"

Date: Thu, 23 Oct 2025 11:43:28 +0200



--_----------=_1761212608489325

Content-Transfer-Encoding: base64

Content-Type: text/html; charset=utf-8

Date: Thu, 23 Oct 2025 11:43:28 +0200



PCFET0NUWVBFIGh0bWwgUFVCTElDICItLy9XM0MvL0RURCBYSFRNTCAxLjAgVHJhbnNpdGlvbmFs

Ly9FTiIgImh0dHA6Ly93d3cudzMub3JnL1RSL3hodG1sMS9EVEQveGh0bWwxLXRyYW5zaXRpb25h

bC5kdGQiPgo8aHRtbCB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMTk5OS94aHRtbCIgeG1sbnM6

dj0idXJuOnNjaGVtYXMtbWljcm9zb2Z0LWNvbTp2bWwiPgogPGhlYWQ+CiAgPHRpdGxlPkFiYmlh

bW8gcmljZXZ1dG8gcXVlc3RvIG1lc3NhZ2dpbyBkYSBGcmFuY2VzY28gQnJ1ZmFuaTwvdGl0bGU+

CiAgPHN0eWxlIHR5cGU9InRleHQvY3NzIj4KLkV4dGVybmFsQ2xhc3Mge3dpZHRoOjEwMCU7fQou

RXh0ZXJuYWxDbGFzcywgLkV4dGVybmFsQ2xhc3MgcCwgLkV4dGVybmFsQ2xhc3Mgc3BhbiwgLkV4

dGVybmFsQ2xhc3MgZm9udCwgLkV4dGVybmFsQ2xhc3MgdGQsIC5FeHRlcm5hbENsYXNzIGRpdiB7

CmxpbmUtaGVpZ2h0OiAxMDAlICFpbXBvcnRhbnQ7Cn0KYm9keSB7LXdlYmtpdC10ZXh0LXNpemUt

YWRqdXN0Om5vbmU7IC1tcy10ZXh0LXNpemUtYWRqdXN0Om5vbmU7fQpib2R5IHttYXJnaW46MDsg

cGFkZGluZzowO30KdGFibGUgdGQge2JvcmRlci1jb2xsYXBzZTpjb2xsYXBzZTt9CnUgKyAuYm9k

eSB7IG1pbi13aWR0aDogNDIwcHg7IG1hcmdpbjowOyBwYWRkaW5nOjA7IH0KcCB7bWFyZ2luOjA7

IHBhZGRpbmc6MDsgbWFyZ2luLWJvdHRvbTowO30KaDEsIGgyLCBoMywgaDQsIGg1LCBoNiB7CmNv

bG9yOiBibGFjazsKbGluZS1oZWlnaHQ6IDEwMCU7Cn0KYSwgYTpsaW5rIHsKY29sb3I6ICMwMDcx

QzI7CnRleHQtZGVjb3JhdGlvbjogdW5kZXJsaW5lOwp9CmJvZHksIHRhYmxlLCB0ZCwgYSB7IC13

ZWJraXQtdGV4dC1zaXplLWFkanVzdDogMTAwJTsgLW1zLXRleHQtc2l6ZS1hZGp1c3Q6IDEwMCU7

IH0KdGFibGUsIHRkIHsgbXNvLXRhYmxlLWxzcGFjZTogMHB0OyBtc28tdGFibGUtcnNwYWNlOiAw

cHQ7IH0KaW1nIHsgLW1zLWludGVycG9sYXRpb24tbW9kZTogYmljdWJpYzsgfQppbWcgeyBib3Jk

ZXI6IDA7IG91dGxpbmU6IG5vbmU7IHRleHQtZGVjb3JhdGlvbjogbm9uZTsgfQouaGlkZGVuIHsK

ZGlzcGxheTogbm9uZSAhaW1wb3J0YW50Owp9CiogW2xhbmc9ImNvbnRhaW5lci10YWJsZSJdIHsK

bWF4LXdpZHRoOiA0MjBweDsKfQpAbWVkaWEgb



Parametri Comuni per l'Associazione nel DB
Il parametro fondamentale per associare l'email di Conferma Prenotazione con l'email di Messaggio Ricevuto è l'ID della Prenotazione (o ID Voucher).

L'ID Prenotazione è l'elemento più robusto per collegare le comunicazioni in un database. Il valore identificativo è 5958915259.

Nella prima email (Conferma), questo ID è chiaramente indicato nel campo Subject (Prenotazione ID 5958915259) e nel corpo come ID Voucher.

Nella seconda email (Messaggio), l'ID è incorporato nell'indirizzo del mittente (Sender) come prefisso (5958915259-) e specificato nel corpo del messaggio come "Numero di conferma: 5958915259".

Per l'associazione in un database, l'ID Prenotazione (5958915259) dovrebbe essere utilizzato come Chiave



Maiil di conferma prneotaizone Airbnb



Delivered-To: shortdeseos@gmail.com

Received: by 2002:a17:504:ca91:b0:1bfd:bb51:a3e8 with SMTP id qu17csp2383250njb;

        Fri, 7 Mar 2025 12:27:18 -0800 (PST)

X-Google-Smtp-Source: AGHT+IFdhsVrRxrC9i4umh3Lz/s/GcpQoCeTTu60qJNLGqL7PQGOSaTLDVGVkTYEI/GdHvbFD9wt

X-Received: by 2002:a05:6214:daa:b0:6e6:5f08:e77d with SMTP id 6a1803df08f44-6e90060fa25mr66239606d6.19.1741379238168;

        Fri, 07 Mar 2025 12:27:18 -0800 (PST)

ARC-Seal: i=1; a=rsa-sha256; t=1741379238; cv=none;

        d=google.com; s=arc-20240605;

        b=LwV6aHIuKp+bvtRCO9IVdg0ty8K+TlaML6T5eaTvwxdCYwYxCTwv0bWPFrVfr+eszF

         HS9oOS+/mJgcdjEgVHGH/jv9VFom+PyJWUonkLjap1UCknrKMLw6LFENDN1S8YCedhYv

         lMJwIkiR2UdjFKug7Y2M5AKriyHHflJrM8e2rqZQ+Ec/sGEMLkTqHEvzhN+nIy29erLo

         67XAwlj2R8tMAuUIxC/rMogKxY4qUFbtJK6MuKVrx+9tiQcbyR/O2wacbij3R9xDMPRO

         Wl0LEHzgYyOapdi3Qf3se2gyOOwK8hOjmSHgFJKENJ1O7YBipcsBi6tCjb2f9WItrsu9

         ygbQ==

ARC-Message-Signature: i=1; a=rsa-sha256; c=relaxed/relaxed; d=google.com; s=arc-20240605;

        h=to:priority:importance:bimi-selector:reply-to:subject:message-id

         :mime-version:from:date:dkim-signature:dkim-signature;

        bh=HRF5voWwjvlbtuXb+hvMTdjE/aNGIi+PjdvHskV/Ql0=;

        fh=XBTByGVyCMihm8LvqfNCIEQ1zKLApuAOsFeBQLo6miw=;

        b=aVfV7NZHbMgVTzYjDfqARvUmU3pS4nOu4GOaFWfqM+YCE7+qLVNLaDId3I/6HdgkM7

         KXjVrPJIe1gYpRrPmyjOT5dk3YKAArLHX7gEZQStF3eCvZ41Gv43k89YHysCK3w1penH

         wJ2CPwmzfDd7Ba+6dRyB/W3PoHYT9KE5zrWgcmELnsibkHwY5ALmwwACkv4T1EZXtZyF

         xwmrtgnlxW4PihhbhPZxsm0Kvd4M8P+VH+oIEok6nMtpLTbkws07LFBo/irNVIa8Bdc0

         fzqFzWP7ZlTRKlmYnFaqVKD9C0RAjKo7vwrr0Z4QCP+gu902Ff0QW6ccs5/LaHhLsYU9

         ZAUA==;

        dara=google.com

ARC-Authentication-Results: i=1; mx.google.com;

       dkim=pass header.i=@email.airbnb.com header.s=s20150428 header.b=rO8me5lc;

       dkim=pass header.i=@sendgrid.info header.s=smtpapi header.b="zlbvsje/";

       spf=pass (google.com: domain of bounces+169303-ba73-shortdeseos=gmail.com@email.airbnb.com designates 50.31.32.8 as permitted sender) smtp.mailfrom="bounces+169303-ba73-shortdeseos=gmail.com@email.airbnb.com";

       dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=airbnb.com

Return-Path: <bounces+169303-ba73-shortdeseos=gmail.com@email.airbnb.com>

Received: from o14.email.airbnb.com (o14.email.airbnb.com. [50.31.32.8])

        by mx.google.com with ESMTPS id 6a1803df08f44-6e8f7162927si39810176d6.192.2025.03.07.12.27.17

        for <shortdeseos@gmail.com>

        (version=TLS1_3 cipher=TLS_AES_128_GCM_SHA256 bits=128/128);

        Fri, 07 Mar 2025 12:27:18 -0800 (PST)

Received-SPF: pass (google.com: domain of bounces+169303-ba73-shortdeseos=gmail.com@email.airbnb.com designates 50.31.32.8 as permitted sender) client-ip=50.31.32.8;

Authentication-Results: mx.google.com;

       dkim=pass header.i=@email.airbnb.com header.s=s20150428 header.b=rO8me5lc;

       dkim=pass header.i=@sendgrid.info header.s=smtpapi header.b="zlbvsje/";

       spf=pass (google.com: domain of bounces+169303-ba73-shortdeseos=gmail.com@email.airbnb.com designates 50.31.32.8 as permitted sender) smtp.mailfrom="bounces+169303-ba73-shortdeseos=gmail.com@email.airbnb.com";

       dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=airbnb.com

DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; d=email.airbnb.com; h=content-type:from:mime-version:subject:reply-to:x-feedback-id:to:cc: content-type:from:subject:to; s=s20150428; bh=HRF5voWwjvlbtuXb+hvMTdjE/aNGIi+PjdvHskV/Ql0=; b=rO8me5lcKyWxxPtQgGt9bZhqGzPt/4OLaAYprJAG904qGIaOVJJPGoDwI39pbdiLZ/AA 2Wr6TMKRRc6c+KZbadXFhTkT5scCEMTICTJCyyFLKjPQiuSmFZfcykNiuRex+qexVDBbmR FE2S+RInETgjOfAUNhLRMfb52l684YqPk=

DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; d=sendgrid.info; h=content-type:from:mime-version:subject:reply-to:x-feedback-id:to:cc: content-type:from:subject:to; s=smtpapi; bh=HRF5voWwjvlbtuXb+hvMTdjE/aNGIi+PjdvHskV/Ql0=; b=zlbvsje/NtqQfvEC8uhGWzKxyPLxvWPW5ZTDluwVZCyScVOLjrsVVUyYRim9VSl7PcDC pHsv/LQvI5czHQqLG6aeOt5UPPerC6/2Frjy/BgncKaa8UYVP77zUhUEKU7dWc6SKaQ9+k A9c0NmUT8JFfBa9qzFTE47M6j9GM9+ap0=

Received: by recvd-5d45dc6d9b-lgjkr with SMTP id recvd-5d45dc6d9b-lgjkr-1-67CB56A5-19 2025-03-07 20:27:17.500020281 +0000 UTC m=+3285267.620608034

Received: from MTY5MzAz (unknown) by geopod-ismtpd-36 (SG) with HTTP id Q4XmbzweR9ennOEuhsp2TA Fri, 07 Mar 2025 20:27:17.494 +0000 (UTC)

Content-Type: multipart/alternative; boundary=38da64a423c2f23e09e8640ea1630200a657a9c9d2dcc6f75242c15dee9a

Date: Fri, 07 Mar 2025 20:27:17 +0000 (UTC)

From: Airbnb <automated@airbnb.com>

Mime-Version: 1.0

Message-ID: <Q4XmbzweR9ennOEuhsp2TA@geopod-ismtpd-36>

Subject: Prenotazione confermata - Edward Cadagin arriverà il 10 set

Reply-To: "Edward (Airbnb)" <3wa1d003wd5bees1l0v92fejx0y1qcgp@reply.airbnb.com>

BIMI-Selector: v=BIMI1; s=belov2;

Importance: high

Priority: Urgent

Return-Path: automated@airbnb.com

X-Category: support

X-Locale: it

X-MSMail-Priority: High

X-Message-Package-UUID: 79e36e35-3e78-f18c-c5ab-b321f0e7704a

X-Priority: 1

X-Strategy: email

X-Template: booking/v2_migration/reservation_host_confirmation

X-User-ID: 520289023

X-rpcampaign: airbnb20250307222037388902357090341287344254544743471

X-Feedback-ID: 169303:SG

X-SG-EID: u001.373TPjtMqGbzwgRnUiLO4XljsWSZKewimAbF7sau2vF2RcaqvXC4aBu98qmouqE315bWTq7G9Woc+/rCXCZAOmgHOpTOKN9M0aKCe79ViUv3gOhbaazKI1eoLd8T3mkYxqbn1DoBNgfr2X5DHdxpHy5hh2zynGBZSHn0jgHMQLBplBGgM/zzjDt4E5JpnZVxvABVnGkIWey1nKw9rabU8ZtyEUzfnc5oiZTcq8VbeEg=

X-SG-ID: u001.SdBcvi+Evd/bQef8eZF3BgIJHvZMm/83c8KgBB9OmLZKwyR8JhoGd5Oqi3E2B9l8wHoV2nqZjdg9lWbmsPSOl/KcmMJPnreOwvvMTZKGp7Scqtu2KDoT9uQC3HbeIGKLOZwrkDpw52/PGrvV90v+A8Q3bdsKTaCazG/sYENsjR4Otp0832Q71R8uvMAbT1ClmLcr4QEkQk/jNr9C96RArla6rDzVIwSQjCOILcodW8AeUyksX3sGgcNkF42NbGp7TxiQwWL88P+34A/DLA00tQixdYKHUp6AZueFlrzSM0Bu0vKE4AFDwfCOr/mZCn84m7FgQAzBdr91sn+s0b54cBEYadTL4EhLlpzghVEp3XXZPE94/iHWNRQkbN+kGgbUB7uxozebzaTsQURGK5V91eEyjje2vaFfaGOkq1V/H7gyL7cBk+yQN3Mi4fQi34n+GegiHRMFcQjCIdpMFDE1kpve7fj6ydDkjehzOV1EBPPOEoMWTcqiwGtFtQOiG26bBbgxSwUKgD5jtoXcbvyQy5fATCyHwD5XaY1NvEypzNR4q2BkOXwtEuu7nykPujpNXv/O4A2VnsTh/r1KiDJ1ng==

To: shortdeseos@gmail.com

X-Entity-ID: u001./H5mzSYUmGGnQUq8WJ0Pfw==



--38da64a423c2f23e09e8640ea1630200a657a9c9d2dcc6f75242c15dee9a

Content-Transfer-Encoding: quoted-printable

Content-Type: text/plain; charset=utf-8

Mime-Version: 1.0



%opentrack%



https://www.airbnb.it/?c=3D.pi80.pkYm9va2luZy92Ml9taWdyYXRpb24vcmVzZXJ2YXRp=

b25faG9zdF9jb25maXJtYXRpb24=3D&euid=3D79e36e35-3e78-f18c-c5ab-b321f0e7704a



NUOVA PRENOTAZIONE CONFERMATA! EDWARD ARRIVER=C3=80 IL 10 SET.



Invia un messaggio per confermare i dettagli di check-in o

per dare il benvenuto a Edward.



https://www.airbnb.it/hosting/reservations/details/HMYQBXYTNP?c=3D.pi80.pkY=

m9va2luZy92Ml9taWdyYXRpb24vcmVzZXJ2YXRpb25faG9zdF9jb25maXJtYXRpb24=3D&euid=

=3D79e36e35-3e78-f18c-c5ab-b321f0e7704a   Edward

                                                                           =

                                                                           =

                                  =20

                                                                           =

                                                                           =

                                   [https://www.airbnb.it/hosting/reservati=

ons/details/HMYQBXYTNP?c=3D.pi80.pkYm9va2luZy92Ml9taWdyYXRpb24vcmVzZXJ2YXRp=

b25faG9zdF9jb25maXJtYXRpb24=3D&euid=3D79e36e35-3e78-f18c-c5ab-b321f0e7704a]

                                                                           =

                                                                           =

                                  =20

                                                                           =

                                                                           =

                                   Identit=C3=A0 verificata =C2=B7 2 recens=

ioni

                                                                           =

                                                                           =

                                  =20

                                                                           =

                                                                           =

                                   Ann Arbor, MI



Ciao! Io e mia moglie vogliamo trascorrere un mese in

Umbria, in una posizione centrale nella splendida citt=C3=A0 di

Perugia. Il tuo appartamento sembra ideale e molto bello.

Potrei lavorare alcuni giorni mentre sono l=C3=AC, quindi voglio

assicurarmi che ci sia una buona connessione WIFI. Inoltre,

c'=C3=A8 un parcheggio a pagamento dove potremmo essere sicuri di

trovare un posto auto? Grazie mille per l'attenzione. Ed e

Victoria



Tradotto automaticamente. Segue il messaggio originale:



Hello! My wife and I want to spend a month in Umbria,

centrally located in the beautiful city of Perugia. Your

apartment looks ideal and very lovely. I may work some days

while I am there, so want to make sure there is a good WIFI

connection. Also, is there a paid parking option where we

could be guaranteed of a parking space? Thank you so much

for your attention. Ed and Victoria



I messaggi di ospiti e host sono stati tradotti

automaticamente nella lingua del tuo account. Puoi

modificare questa preferenza dalle impostazioni.



Invia un Messaggio a Edward.

[https://www.airbnb.it/hosting/thread/2095057270?c=3D.pi80.pkYm9va2luZy92Ml=

9taWdyYXRpb24vcmVzZXJ2YXRpb25faG9zdF9jb25maXJtYXRpb24=3D&euid=3D79e36e35-3e=

78-f18c-c5ab-b321f0e7704a&thread_type=3Dhome_booking&email_cta=3Dlink_hosti=

ng_message_thread]



https://www.airbnb.it/rooms/1136830922567086505?c=3D.pi80.pkYm9va2luZy92Ml9=

taWdyYXRpb24vcmVzZXJ2YXRpb25faG9zdF9jb25maXJtYXRpb24=3D&euid=3D79e36e35-3e7=

8-f18c-c5ab-b321f0e7704a



IMPERIAL SUITE LUXURY PERUGIA PIENO CENTRO STORICO



Intera casa/apt



[https://www.airbnb.it/rooms/1136830922567086505?c=3D.pi80.pkYm9va2luZy92Ml=

9taWdyYXRpb24vcmVzZXJ2YXRpb25faG9zdF9jb25maXJtYXRpb24=3D&euid=3D79e36e35-3e=

78-f18c-c5ab-b321f0e7704a]



Check-in     Check-out

            =20

mer 10 set   ven 10 ott

            =20

16:00        11:00



OSPITI



2 adulti



PI=C3=99 DETTAGLI SU CHI STA ARRIVANDO



Gli ospiti ti faranno ora sapere se viaggiano con bambini o

neonati. Scopri di pi=C3=B9

[https://blog.atairbnb.com/more-host-controls-it/]



CODICE DI CONFERMA

HMYQBXYTNP



L'OSPITE HA PAGATO



190,20=C2=A0=E2=82=AC x 30 notti   5.706,00=C2=A0=E2=82=AC



Costi di pulizia   105,00=C2=A0=E2=82=AC



Costi del servizio dell'ospite   0,00=C2=A0=E2=82=AC



Tasse di utilizzo degli alloggi   5,00=C2=A0=E2=82=AC



TOTALE (EUR)   5.816,00=C2=A0=E2=82=AC



COMPENSO DELL'HOST



Costi della stanza per 30 notti   9.510,00=C2=A0=E2=82=AC



Costi di pulizia   105,00=C2=A0=E2=82=AC



Sconto mensile   -3.804,00=C2=A0=E2=82=AC



Costi del servizio dell'host (12.3%)   -714,75=C2=A0=E2=82=AC



Tasse di utilizzo degli alloggi   5,00=C2=A0=E2=82=AC



TU GUADAGNI   5.101,25=C2=A0=E2=82=AC



Ti invieremo il denaro che guadagni come host 24 ore dopo

l'arrivo del tuo ospite. Puoi controllare i prossimi

pagamenti nella Cronologia delle transazioni

[https://www.airbnb.com/users/transaction_history].



CANCELLAZIONI

I tuoi termini di cancellazione per gli ospiti sono Lungo

termine [https://www.airbnb.com/help/article/149].



Le penalit=C3=A0 previste per cancellare questa prenotazione

includono la pubblicazione di una recensione visibile a

tutti in cui =C3=A8 indicata la cancellazione da parte tua, il

pagamento del costo di cancellazione e il blocco dei

pernottamenti cancellati sul tuo calendario.

Leggi informazioni sulle penalit=C3=A0 di cancellazione

[https://www.airbnb.it/help/article/990?c=3D.pi80.pkYm9va2luZy92Ml9taWdyYXR=

pb24vcmVzZXJ2YXRpb25faG9zdF9jb25maXJtYXRpb24=3D&euid=3D79e36e35-3e78-f18c-c=

5ab-b321f0e7704a]



PREPARATI ALL'ARRIVO DI EDWARD



CONSULTA LE PRATICHE DI SICUREZZA PER L'EMERGENZA COVID-19

Abbiamo creato una serie di pratiche di sicurezza

obbligatorie per l'emergenza COVID-19 che host e ospiti di

Airbnb sono tenuti a seguire. Queste includono il rispetto

del distanziamento sociale e l'utilizzo di una mascherina.

Consulta le pratiche

[https://www.airbnb.it/help/article/2839?c=3D.pi80.pkYm9va2luZy92Ml9taWdyYX=

Rpb24vcmVzZXJ2YXRpb25faG9zdF9jb25maXJtYXRpb24=3D&euid=3D79e36e35-3e78-f18c-=

c5ab-b321f0e7704a]



SEGUI IL PROCESSO AVANZATO DI PULIZIA IN 5 FASI

Tutti gli host devono seguire il protocollo avanzato di

pulizia tra un soggiorno e l'altro. Abbiamo sviluppato

queste fasi in collaborazione con esperti allo scopo di

prevenire la diffusione della malattia causata dal nuovo

coronavirus (COVID-19).

Consulta il processo

[https://www.airbnb.it/help/article/2809?c=3D.pi80.pkYm9va2luZy92Ml9taWdyYX=

Rpb24vcmVzZXJ2YXRpb25faG9zdF9jb25maXJtYXRpb24=3D&euid=3D79e36e35-3e78-f18c-=

c5ab-b321f0e7704a]



FORNISCI INDICAZIONI

Verifica che l'ospite sappia come arrivare al tuo alloggio.

Invia il messaggio

[https://www.airbnb.it/hosting/thread/2095057270?c=3D.pi80.pkYm9va2luZy92Ml=

9taWdyYXRpb24vcmVzZXJ2YXRpb25faG9zdF9jb25maXJtYXRpb24=3D&euid=3D79e36e35-3e=

78-f18c-c5ab-b321f0e7704a&thread_type=3Dhome_booking]



La protezione dalla A alla Z, inclusa ogni volta che ospiti.

Scopri di pi=C3=B9

[https://www.airbnb.it/help/article/3142/getting-protected-through-aircover=

-for-hosts?c=3D.pi80.pkYm9va2luZy92Ml9taWdyYXRpb24vcmVzZXJ2YXRpb25faG9zdF9j=

b25maXJtYXRpb24=3D&euid=3D79e36e35-3e78-f18c-c5ab-b321f0e7704a&email_cta=3D=

]



ASSISTENZA CLIENTI

Contatta il nostro team di assistenza h24, ovunque nel

mondo.

Visita il Centro assistenza

[https://www.airbnb.it/help?c=3D.pi80.pkYm9va2luZy92Ml9taWdyYXRpb24vcmVzZXJ=

2YXRpb25faG9zdF9jb25maXJtYXRpb24=3D&euid=3D79e36e35-3e78-f18c-c5ab-b321f0e7=

704a]Contatta

Airbnb

[https://www.airbnb.it/help/contact_us?c=3D.pi80.pkYm9va2luZy92Ml9taWdyYXRp=

b24vcmVzZXJ2YXRpb25faG9zdF9jb25maXJtYXRpb24=3D&euid=3D79e36e35-3e78-f18c-c5=

ab-b321f0e7704a]



Airbnb Ireland UC



8 Hanover Quay



Dublin 2, Ireland



Termini di pagamento tra te e:



Airbnb Payments, Inc.



888 Brannan St.



San Francisco, CA 94103



Scarica l'app di Airbnb



https://www.airbnb.it/external_link?c=3D.pi80.pkYm9va2luZy92Ml9taWdyYXRpb24=

vcmVzZXJ2YXRpb25faG9zdF9jb25maXJtYXRpb24=3D&euid=3D79e36e35-3e78-f18c-c5ab-=

b321f0e7704a&url=3Dhttps%3A%2F%2Fairbnb.sng.link%2FA6f9up%2Fdvs6%3F_smtype%=

3D3%26pcid%3D.pi80.pkYm9va2luZy92Ml9taWdyYXRpb24vcmVzZXJ2YXRpb25faG9zdF9jb2=

5maXJtYXRpb24%3D   https://www.airbnb.it/external_link?c=3D.pi80.pkYm9va2lu=

Zy92Ml9taWdyYXRpb24vcmVzZXJ2YXRpb25faG9zdF9jb25maXJtYXRpb24=3D&euid=3D79e36=

e35-3e78-f18c-c5ab-b321f0e7704a&url=3Dhttps%3A%2F%2Fairbnb.sng.link%2FA6f9u=

p%2Fqh0lc%3Fid%3Dcom.airbnb.android%26pcid%3D.pi80.pkYm9va2luZy92Ml9taWdyYX=

Rpb24vcmVzZXJ2YXRpb25faG9zdF9jb25maXJtYXRpb24%3D  =20



=C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=

=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =

=C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0 =C2=A0

--38da64a423c2f23e09e8640ea1630200a657a9c9d2dcc6f75242c15dee9a

Content-Transfer-Encoding: quoted-printable

Content-Type: text/html; charset=utf-8

Mime-Version: 1.0



<html lang=3D"en"><head><meta http-equiv=3D"Content-Type" content=3D"text/h=

tml; charset=3Dutf-8"><meta name=3D"viewport" content=3D"width=3Ddevice-wid=

th, initial-scale=3D1"><style type=3D"text/css">

@font-face {

  font-family: Cereal;

  src: url("https://a0.muscache.com/airbnb/static/airbnb-dls-web/build/font=

s/Airbnb_Cereal-Book-9a1c9cca9bb3d65fefa2aa487617805e.woff2") format("woff2=

"), url("https://a0.muscache.com/airbnb/static/airbnb-dls-web/build/fonts/A=

irbnb_Cereal-Book-aa38e86e3f98554f9f7053d7b713b4db.woff") format('woff');

  font-weight: normal;

  font-style: normal;

  font-display: swap;}


Mail messaggio Airbnb


Delivered-To: shortdeseos@gmail.com
Received: by 2002:a17:505:4a13:b0:1bfd:bb51:a3e8 with SMTP id op19csp1386235njb;
        Mon, 10 Mar 2025 13:18:45 -0700 (PDT)
X-Google-Smtp-Source: AGHT+IFw2PftFJ9Xua3AYVXS0b65eQwmJne96r56oDhf1HR8mx76b74FzNcswuzx8zxYgmDyFbvm
X-Received: by 2002:a5d:6d04:0:b0:390:f0ff:2bf8 with SMTP id ffacd0b85a97d-39132d05f78mr10590774f8f.10.1741637925466;
        Mon, 10 Mar 2025 13:18:45 -0700 (PDT)
ARC-Seal: i=1; a=rsa-sha256; t=1741637925; cv=none;
        d=google.com; s=arc-20240605;
        b=X07B2twpY3b+9y+I2aTYlcX7tcOz5oeLlWQW9LDLq9R0JbtaxFdj81T1V8tqSCQZfv
         yicF3Tc++4BsUIqMirb0wJEioabJFm67ie0kBHBoC5KbkVK6ZOSej0R+88Z1o6sF3Sj1
         kU6oghuVfsJgKEvZdWLdc6E981qsMfo39ths+uvdbJSHJtB/ydQnOlAe0AwFk9Ajl8+w
         WQ/0PXif2mwvhGLU7dxXywY/0e4A+NRJFI3MW+XB0ugu7hZmX71334j1tZqbeow1P0Li
         KLJjdulu71B+ughNbBq8QhWm4m1qf+se0D9YDb9gU6hL1vMTCZV3/OsGoQlqCiHWeHOH
         czJA==
ARC-Message-Signature: i=1; a=rsa-sha256; c=relaxed/relaxed; d=google.com; s=arc-20240605;
        h=to:priority:importance:bimi-selector:reply-to:subject:message-id
         :mime-version:from:date:dkim-signature:dkim-signature;
        bh=4itIKhD3Do9ZIx5PpWXTMy4MmOFrNy5NFzrFSyfsxYM=;
        fh=XBTByGVyCMihm8LvqfNCIEQ1zKLApuAOsFeBQLo6miw=;
        b=hxwHZf0JzeK6wEoq+dgGSeFNKK2yPT6gDvObBcbuxAZUVwq63DVEu7gF7KViI6rEgv
         fmWOMnHJAAszpsZcKDfRo3wTx1xOcbBbAQ5eQGz23QLcla2kxO/Vg/iRL/ndk4uGYAQQ
         7P3vH0xUP9gEu9SLjGBg5jLmw/1R6pENu2W6SA9KlkKYwEW++LcwGdFLzeLbv/whoYvs
         ZjEpjy4GFxw1PGXCKvS8qPKbAEwuW9x+0tpIqFadNlww8Hcemvmg8Bmwl/bRwNlbG59f
         LAaqdbkDGeZb/jHP1vYJkoF3hEOI0dCWgFxJH3ubwuXnT4DGl4vlR4lyVU/Ln7eR4+ko
         yRZw==;
        dara=google.com
ARC-Authentication-Results: i=1; mx.google.com;
       dkim=pass header.i=@email.airbnb.com header.s=s20150428 header.b=KQgYFujg;
       dkim=pass header.i=@sendgrid.info header.s=smtpapi header.b=z1HdAQnB;
       spf=pass (google.com: domain of bounces+168748-7bbd-shortdeseos=gmail.com@email.airbnb.com designates 167.89.32.207 as permitted sender) smtp.mailfrom="bounces+168748-7bbd-shortdeseos=gmail.com@email.airbnb.com";
       dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=airbnb.com
Return-Path: <bounces+168748-7bbd-shortdeseos=gmail.com@email.airbnb.com>
Received: from o3.email.airbnb.com (o3.email.airbnb.com. [167.89.32.207])
        by mx.google.com with ESMTPS id ffacd0b85a97d-3912c11ef6csi6808621f8f.706.2025.03.10.13.18.44
        for <shortdeseos@gmail.com>
        (version=TLS1_3 cipher=TLS_AES_128_GCM_SHA256 bits=128/128);
        Mon, 10 Mar 2025 13:18:45 -0700 (PDT)
Received-SPF: pass (google.com: domain of bounces+168748-7bbd-shortdeseos=gmail.com@email.airbnb.com designates 167.89.32.207 as permitted sender) client-ip=167.89.32.207;
Authentication-Results: mx.google.com;
       dkim=pass header.i=@email.airbnb.com header.s=s20150428 header.b=KQgYFujg;
       dkim=pass header.i=@sendgrid.info header.s=smtpapi header.b=z1HdAQnB;
       spf=pass (google.com: domain of bounces+168748-7bbd-shortdeseos=gmail.com@email.airbnb.com designates 167.89.32.207 as permitted sender) smtp.mailfrom="bounces+168748-7bbd-shortdeseos=gmail.com@email.airbnb.com";
       dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=airbnb.com
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; d=email.airbnb.com; h=content-type:from:mime-version:subject:reply-to:x-feedback-id:to:cc: content-type:from:subject:to; s=s20150428; bh=4itIKhD3Do9ZIx5PpWXTMy4MmOFrNy5NFzrFSyfsxYM=; b=KQgYFujgmwIRxbUMlXh30uI24IXAI49yzL9xhRtF0ewlr5Pc1dL4Kti6rLYi9YKEI73m N1ON3m7H8RvOlTOVCHPqgsQe735zs5pDBJyzjQn8yp6HjQ+wSi9Ep4o98STQ4zJmrNilOR T5bfScfa9ideSJcFfIFt3/KS4tYhCmX6k=
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; d=sendgrid.info; h=content-type:from:mime-version:subject:reply-to:x-feedback-id:to:cc: content-type:from:subject:to; s=smtpapi; bh=4itIKhD3Do9ZIx5PpWXTMy4MmOFrNy5NFzrFSyfsxYM=; b=z1HdAQnBSIw1XPur9WzJ9+o9iKZk/tDOovv+RPbIOYY4kofCMwQ/WgTflLCZ7CW1qfXr MJD8SWGcly4BNGd3Wog5X7NlkKlvI7waolkvBI/dy7MbV9LVglrbtWB6eFcNxCaXobHoqI B5wwxWlunPIRVPxdXl+1A0KqKCl2emnoE=
Received: by recvd-74889bb77c-75x4q with SMTP id recvd-74889bb77c-75x4q-1-67CF4923-16 2025-03-10 20:18:43.153265808 +0000 UTC m=+3181913.712012638
Received: from MTY4NzQ4 (unknown) by geopod-ismtpd-38 (SG) with HTTP id GpTNm-VfQ6S9B0Mvf831lg Mon, 10 Mar 2025 20:18:43.112 +0000 (UTC)
Content-Type: multipart/alternative; boundary=fc27988ec100f8b6ccb34361a59d245d7db829e8bc85bef0754e416c816b
Date: Mon, 10 Mar 2025 20:18:43 +0000 (UTC)
From: Airbnb <express@airbnb.com>
Mime-Version: 1.0
Message-ID: <GpTNm-VfQ6S9B0Mvf831lg@geopod-ismtpd-38>
Subject: RE: Prenotazione per Imperial Suite Luxury Perugia pieno Centro Storico per 10 settembre 2025 - 10 ottobre 2025
Reply-To: "Edward (Airbnb)" <4o16uutn38vqzkuo4t6z33fl7ydpd0pg57is@reply.airbnb.com>
BIMI-Selector: v=BIMI1; s=belov2;
Importance: high
Priority: Urgent
Return-Path: express@airbnb.com
X-Category: message
X-Locale: it
X-MSMail-Priority: High
X-Message-Package-UUID: 780466c5-ef91-f2ff-09aa-aeb4be9f9589
X-Priority: 1
X-Strategy: email
X-Template: homes_messaging/new_message
X-User-ID: 520289023
X-rpcampaign: airbnb20250310152328760092722452715530303223890373903
X-Feedback-ID: 168748:SG
X-SG-EID: u001.373TPjtMqGbzwgRnUiLO4aQplIiW+Q7azdMrDCU1iICBGcf7GI8fS8Yas/rvZ5srHMnntaBeej/QxrQFQhH0fJOlMipDiRbVX6+zTeAvjcOSwbaaN8P1eY3heK3QerTYyYSYLr0yQ4NGloYNqXJMojuqIuqeJmlk6tYLnldnckDB1b5g66OAsWfXdOgEjEEUl+7yug+qskEEM0OpcV2LHqV/5Ae9TAK4jSYuGYc68I4=
X-SG-ID: u001.SdBcvi+Evd/bQef8eZF3BqZ9cHLZlaQH8LGBOs0K2+F024wgXfxgfZf8owozgZzIDr0SWjqkz0Hzl15He+3JiV4qiZ3NftmNAQKXfQpNpidNvJalNic6JYjllxfNAmK52O3GlhDFOjjI2YBmc2SQ5ATHgFyULupM9awHXeLmO3kPaIPUO8W6taw7YakxdxL7HtPYOEf0PhchSaqp2ofmDW8lAtz7PCbo7AW8KFNu2QQPf1jce2NXIhhOq5eOXspp4BXMgPbWMMx2CH1fJgTnERWU8/5DJvEGxbNn7nYMseij/+3jpPSQYetZjMM9WDqESNxsAizSZ9xoCPkreo0E5mx/3eNSSbnSMDbRM4j5ScH+Yb3Qh7qm+N7e1ap9ktAUmBsZvacQ+CFvSbm+Vj9IKRXZPe/Z5EkGrRzybf5NAqruE9G4R9l5ewe1Le1rcJOqIek8Xbbgk5YDlDOFltT75HcEeXNnQ1xpMruqpsQqNJQ1JKEJMlYaOjvVZznJxugIA1C8OKUEGG8N5fQ3kavZZw==
To: shortdeseos@gmail.com
X-Entity-ID: u001.xNm+654l4yZx3FKLl1hq6g==

--fc27988ec100f8b6ccb34361a59d245d7db829e8bc85bef0754e416c816b
Content-Transfer-Encoding: quoted-printable
Content-Type: text/plain; charset=iso-8859-1
Mime-Version: 1.0

%opentrack%

https://www.airbnb.it/?c=3D.pi80.pkaG9tZXNfbWVzc2FnaW5nL25ld19tZXNzYWdl&eui=
d=3D780466c5-ef91-f2ff-09aa-aeb4be9f9589

RE: PRENOTAZIONE PER IMPERIAL SUITE LUXURY PERUGIA PIENO
CENTRO STORICO PER 10 SETTEMBRE 2025 - 10 OTTOBRE 2025

Ricorda: Airbnb non ti chiederebbe mai di trasferire fondi.
Scopri di pi=F9
[https://www.airbnb.it/help/article/209?c=3D.pi80.pkaG9tZXNfbWVzc2FnaW5nL25=
ld19tZXNzYWdl&euid=3D780466c5-ef91-f2ff-09aa-aeb4be9f9589].

   Edward
  =20
   Gentile Lorenzo,
   grazie mille per le informazioni. Abbiamo un'altra domanda.
   Dalle foto sembra che non ci sia la doccia in bagno. Non
   sar=E0 un problema, ma avremmo bisogno di una specie di tubo
   nella vasca con un ugello doccia per lavarci i capelli. =C8
   disponibile? Grazie.
   Cordiali saluti,
   Edward
  =20
   Tradotto automaticamente. Segue il messaggio originale:
  =20
   Dear Lorenzo,
   Thank you so much for the information. We do have another
   question. From the photos it looks as if there is no shower
   in the bathroom. This will not be a problem. but we would
   need some some sort of hose in the tub with a shower nozzle
   on it in order to wash our hair. Is this available? Thank
   you.
   Best regards,
   Edward

Rispondi
[https://www.airbnb.it/hosting/thread/2095057270?thread_type=3Dhome_booking=
&c=3D.pi80.pkaG9tZXNfbWVzc2FnaW5nL25ld19tZXNzYWdl&euid=3D780466c5-ef91-f2ff=
-09aa-aeb4be9f9589]

I messaggi di ospiti e host sono stati tradotti
automaticamente nella lingua del tuo account. Puoi
modificare questa preferenza dalle impostazioni.

Rispondi a questa email per inviare un messaggio a Edward

https://www.airbnb.it/rooms/1136830922567086505?c=3D.pi80.pkaG9tZXNfbWVzc2F=
naW5nL25ld19tZXNzYWdl&euid=3D780466c5-ef91-f2ff-09aa-aeb4be9f9589

DETTAGLI DELLA PRENOTAZIONE

Imperial Suite Luxury Perugia pieno Centro Storico

Appartamento - Intera casa/apt da Deseos

OSPITI

2 ospiti

   CHECK-IN            CHECK-OUT
                   =20
mercoled=EC           venerd=EC
                   =20
10 settembre 2025   10 ottobre 2025

Il tuo tasso di risposta medio: entro un'ora

Il tuo tasso di risposta: 100%

FREQUENTLY ASKED QUESTIONS

Posso rifiutare le richieste di prenotazione?
[https://www.airbnb.it/help/article/899?c=3D.pi80.pkaG9tZXNfbWVzc2FnaW5nL25=
ld19tZXNzYWdl&euid=3D780466c5-ef91-f2ff-09aa-aeb4be9f9589]

Come pre-approvo un ospite?
[https://www.airbnb.it/help/article/237?c=3D.pi80.pkaG9tZXNfbWVzc2FnaW5nL25=
ld19tZXNzYWdl&euid=3D780466c5-ef91-f2ff-09aa-aeb4be9f9589]

Come vengono calcolati il tasso e il tempo di risposta?
[https://www.airbnb.it/help/article/430?c=3D.pi80.pkaG9tZXNfbWVzc2FnaW5nL25=
ld19tZXNzYWdl&euid=3D780466c5-ef91-f2ff-09aa-aeb4be9f9589]

L'ASSISTENZA CLIENTI

Visita il Centro Assistenza
[https://www.airbnb.it/help?c=3D.pi80.pkaG9tZXNfbWVzc2FnaW5nL25ld19tZXNzYWd=
l&euid=3D780466c5-ef91-f2ff-09aa-aeb4be9f9589]

Contatta Airbnb
[https://www.airbnb.it/help/contact_us?c=3D.pi80.pkaG9tZXNfbWVzc2FnaW5nL25l=
d19tZXNzYWdl&euid=3D780466c5-ef91-f2ff-09aa-aeb4be9f9589]

   https://www.airbnb.it/external_link?c=3D.pi80.pkaG9tZXNfbWVzc2FnaW5nL25l=
d19tZXNzYWdl&euid=3D780466c5-ef91-f2ff-09aa-aeb4be9f9589&url=3Dhttps%3A%2F%=
2Fwww.facebook.com%2Fairbnb   https://www.airbnb.it/external_link?c=3D.pi80=
.pkaG9tZXNfbWVzc2FnaW5nL25ld19tZXNzYWdl&euid=3D780466c5-ef91-f2ff-09aa-aeb4=
be9f9589&url=3Dhttps%3A%2F%2Fwww.instagram.com%2Fairbnb   https://www.airbn=
b.it/external_link?c=3D.pi80.pkaG9tZXNfbWVzc2FnaW5nL25ld19tZXNzYWdl&euid=3D=
780466c5-ef91-f2ff-09aa-aeb4be9f9589&url=3Dhttps%3A%2F%2Ftwitter.com%2FAirb=
nb

Airbnb Ireland UC

8 Hanover Quay

Dublin 2, Ireland

Scarica l'app di Airbnb

https://www.airbnb.it/external_link?c=3D.pi80.pkaG9tZXNfbWVzc2FnaW5nL25ld19=
tZXNzYWdl&euid=3D780466c5-ef91-f2ff-09aa-aeb4be9f9589&url=3Dhttps%3A%2F%2Fa=
irbnb.sng.link%2FA6f9up%2Fdvs6%3F_smtype%3D3%26pcid%3D.pi80.pkaG9tZXNfbWVzc=
2FnaW5nL25ld19tZXNzYWdl   https://www.airbnb.it/external_link?c=3D.pi80.pka=
G9tZXNfbWVzc2FnaW5nL25ld19tZXNzYWdl&euid=3D780466c5-ef91-f2ff-09aa-aeb4be9f=
9589&url=3Dhttps%3A%2F%2Fairbnb.sng.link%2FA6f9up%2Fqh0lc%3Fid%3Dcom.airbnb=
.android%26pcid%3D.pi80.pkaG9tZXNfbWVzc2FnaW5nL25ld19tZXNzYWdl  =20

Aggiorna le tue preferenze email
[https://www.airbnb.it/account-settings/notifications?c=3D.pi80.pkaG9tZXNfb=
WVzc2FnaW5nL25ld19tZXNzYWdl&euid=3D780466c5-ef91-f2ff-09aa-aeb4be9f9589]
per scegliere quali ricevere o annulla l'iscrizione
[https://www.airbnb.it/account-settings/email-unsubscribe?email_type=3Dfals=
e&mac=3DZYA2jlNzZK77uRKEmawJvW31bsM%3D&token=3DeyJncmFudWxhcl9jYXRlZ29yeSI6=
Ik1FU1NBR0VTIiwiY2F0ZWdvcnkiOm51bGwsInRlbXBsYXRlIjpudWxsLCJ1dWlkIjoiNzgwNDY=
2YzUtZWY5MS1mMmZmLTA5YWEtYWViNGJlO


Parametri Comuni per l'Associazione nel DB (Formato Testuale)
L'elemento più efficace e cruciale per associare l'email di Conferma Prenotazione con l'email successiva di Messaggio Ospite è l'ID Discussione (Thread ID).

Identificatore Primario: ID Discussione
Airbnb utilizza un ID Discussione (Thread ID) per tracciare la conversazione specifica tra host e ospite relativa a una prenotazione. Questo è il parametro più affidabile per collegare i messaggi successivi alla prenotazione originale:

Valore: L'ID Discussione è 2095057270.

Fonte nell'Email 1 (Conferma): Si trova all'interno dei link per "Invia un Messaggio a Edward" o "FORNISCI INDICAZIONI", ad esempio: .../hosting/thread/2095057270?...

Fonte nell'Email 2 (Messaggio): Si trova all'interno del link "Rispondi" in fondo al messaggio: .../hosting/thread/2095057270?...


Nuova mail messaggio booking


Delivered-To: shortdeseos@gmail.com
Received: by 2002:a17:504:d884:b0:1d27:83a3:6131 with SMTP id nr4csp1334802njb;
        Thu, 13 Nov 2025 21:22:19 -0800 (PST)
X-Google-Smtp-Source: AGHT+IGV331bnwtv2STY8RobcL8Kuz5a7o0wk89R/Ws44oLUUaEjoWidc5ZVmNog1SJzqaqyK63c
X-Received: by 2002:a17:907:9446:b0:b72:dbf2:afb8 with SMTP id a640c23a62f3a-b7367bda000mr144408466b.65.1763097739200;
        Thu, 13 Nov 2025 21:22:19 -0800 (PST)
ARC-Seal: i=1; a=rsa-sha256; t=1763097739; cv=none;
        d=google.com; s=arc-20240605;
        b=UjrmZQGzBu+rDthbVR1bvo0d3CF6ghpUSjx92ugWndWveNQxmD0DIwMjISB3f1nGYj
         ZWstoBhp517TUsItVm2N9woQCrtaUwdbxtUUFWyCGWDuOOjFGUbtp1JqgbT8mBj5R18u
         WcfNZM6KOWtDuJFDb3pjM3Tz5Cu/l9yWTRL5W1CPka7SWOHlRLIauaa4BLPDf7fH//Me
         DZ+InBeuw57RsZK4NI/XrvoEKVarjgPSPobTlhcl/tWl/VvjOdYoAZKLwKa+ia/53zDY
         kz0ftGTxIV8hsCrxW1lRhcrwnNbhOLK5xWzXGHEaQHftxP8kniugWtmkF2QGt9bpxbOE
         FSCQ==
ARC-Message-Signature: i=1; a=rsa-sha256; c=relaxed/relaxed; d=google.com; s=arc-20240605;
        h=message-id:sender:subject:reply-to:from:to:date:mime-version
         :content-transfer-encoding:dkim-signature;
        bh=af0RCaWextyJpB0ZYM1y0Yn13FKNF2lv2WLKmWp2obo=;
        fh=XBTByGVyCMihm8LvqfNCIEQ1zKLApuAOsFeBQLo6miw=;
        b=cTIrMB5rfCJubSVNZeD4zAgh3XnzIayuXqkUP0q0/L2aMdqhOhUYkmCBLgpMddpzoV
         Lkl6WeXYUucdQN7ef1xoc+87IhbNEOwoNKoqWBeGWZvUxOmkvLtb66oJZdSYriva1IxG
         f8xEt+CnFCBxBLBgvuozSmB337KpexNrdu4STMJsK22vVjMgPVdo6VXqIHvCsUXFupBh
         5sAIXb0DtmmiGhvsDBvrkasiH6FwGnl+84KX9K2LtkfjjJsbPrf9b+EmzOl29krcIPAS
         7UA1cH5cQmGPLQ+yGMngg9JXRHNdlyOwtXvwL5N/QOjp/e4oqiV6bSYbKGnJzTqhbnSb
         CSeA==;
        dara=google.com
ARC-Authentication-Results: i=1; mx.google.com;
       dkim=pass header.i=@guest.booking.com header.s=bk header.b=cEdYqDLx;
       spf=pass (google.com: domain of 5990548837-bnsc.hqug.v35m.x4vx@guest.booking.com designates 37.10.30.7 as permitted sender) smtp.mailfrom=5990548837-bnsc.hqug.v35m.x4vx@guest.booking.com;
       dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=guest.booking.com
Return-Path: <5990548837-bnsc.hqug.v35m.x4vx@guest.booking.com>
Received: from mailout-202-r6.booking.com (mailout-202-r6.booking.com. [37.10.30.7])
        by mx.google.com with ESMTPS id a640c23a62f3a-b734fc0dfcbsi191682866b.381.2025.11.13.21.22.18
        for <shortdeseos@gmail.com>
        (version=TLS1_3 cipher=TLS_AES_256_GCM_SHA384 bits=256/256);
        Thu, 13 Nov 2025 21:22:19 -0800 (PST)
Received-SPF: pass (google.com: domain of 5990548837-bnsc.hqug.v35m.x4vx@guest.booking.com designates 37.10.30.7 as permitted sender) client-ip=37.10.30.7;
Authentication-Results: mx.google.com;
       dkim=pass header.i=@guest.booking.com header.s=bk header.b=cEdYqDLx;
       spf=pass (google.com: domain of 5990548837-bnsc.hqug.v35m.x4vx@guest.booking.com designates 37.10.30.7 as permitted sender) smtp.mailfrom=5990548837-bnsc.hqug.v35m.x4vx@guest.booking.com;
       dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=guest.booking.com
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; s=bk; d=guest.booking.com; h=Content-Transfer-Encoding:Content-Type:MIME-Version:Date:To:From:Reply-To: Subject:Sender:Message-Id; i=5990548837-bnsc.hqug.v35m.x4vx@guest.booking.com; bh=af0RCaWextyJpB0ZYM1y0Yn13FKNF2lv2WLKmWp2obo=; b=cEdYqDLxTb0/RXjkrLeXbBxPIOuJ6rEwwlZeg6f83vn1cFtqomlWTTdp1ccP+z4KLp6tWaiCBjxw
   NXJO7N/bqtNk1nxvvnHcwPoCfXg7UmFjjXQY7DKNmBNjlC9qJAAFmXRU6XOwQr2yzqvCGJNw1RiW
   DN8ChLVMNP7uUUmsp8I=
Content-Transfer-Encoding: binary
Content-Type: multipart/alternative; boundary="_----------=_176309773829844"
MIME-Version: 1.0
Date: Fri, 14 Nov 2025 06:22:18 +0100
To: shortdeseos@gmail.com
From: "Salvatore Bracciante tramite Booking.com" <5990548837-bnsc.hqug.v35m.x4vx@guest.booking.com>
Reply-To: 5990548837-bnsc.hqug.v35m.x4vx@guest.booking.com
Subject: Abbiamo ricevuto questo messaggio da Salvatore Bracciante
Sender: "Salvatore Bracciante tramite Booking.com" <5990548837-bnsc.hqug.v35m.x4vx@guest.booking.com>
X-Bme-Id: 35217668954
Message-Id: <4d759k4mzPz2wGp@mailrouter-101.ams4.prod.booking.com>

--_----------=_176309773829844
Content-Transfer-Encoding: base64
Content-Type: text/plain; charset=utf-8
Date: Fri, 14 Nov 2025 06:22:18 +0100

ICAgIyMtIFNjcml2aSBsYSB0dWEgcmlzcG9zdGEgc29wcmEgcXVlc3RhIHJpZ2EgLSMjCgogICAg
ICAgICAgICAgICAgICAgICAgIE51bWVybyBkaSBjb25mZXJtYTogNTk5MDU0ODgzNwoKICAgICAg
ICAgICAgICAgICAgICAgICAgTnVvdm8gbWVzc2FnZ2lvIGRhIHVuIG9zcGl0ZQoKICAgICAgICAg
ICAgICAgICAgICAgIFNhbHZhdG9yZSBCcmFjY2lhbnRlIGhhIHNjcml0dG86CgogIEJ1b25naW9y
bm8gw6kgcG9zc2liaWxlIHByZW5kZXJlIHBvc3Nlc3NvIGRlbGzigJlhcHB1bnRhbWVudG8gcHJp
bWEgZGVsbGUKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDE2IHBlciBmYXZvcmU/Cgog
ICBSaXNwb25kaQoKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIC0tPgogICBo
dHRwczovL2FkbWluLmJvb2tpbmcuY29tL2hvdGVsL2hvdGVsYWRtaW4vZXh0cmFuZXRfbmcvbWFu
YWdlL21lc3NhZ2luZwogICAvaW5ib3guaHRtbD9wcm9kdWN0X2lkPTU5OTA1NDg4MzcmcHJvZHVj
dF90eXBlPVBPU1RfQk9PS0lORyZob3RlbF9pZD0xMwogICAwNjk2MzgmbWVzc2FnZV9pZD0yZDU3
ODkyMC1jMTE5LTExZjAtOTQ2MS0xZjk1YzhlZmU1NWEmcmVzX2lkPTU5OTA1NDg4MwogICA3JmZy
b21faW5zdGFudF9lbWFpbD0xJmxhbmc9aXQmdXRtX21lZGl1bT1lbWFpbCZ1dG1fc291cmNlPW1l
c3NhZ2luZyZ1dAogICBtX3Rlcm09ZnJlZV90ZXh0JnV0bV9jYW1wYWlnbj1wZl9ndWVzdF9yZXF1
ZXN0JnV0bV9jb250ZW50PXJlcGx5Jl9lPTE3NgogICAgICAgICAgIDMwOTc3MzgmX3M9c1Z5ZUhB
R1RKdHVhYTBjOFIrejNJTHdCdUJ6Qi9ud2pTUExiMndpSlpTMAoKICAgRGF0aSBkZWxsYSBwcmVu
b3RhemlvbmUKCiAgIE5vbWUgZGVsbCdvc3BpdGU6CiAgIFNhbHZhdG9yZSBCcmFjY2lhbnRlCgog
ICBDaGVjay1pbjoKICAgdmVuIDE0IG5vdiAyMDI1CgogICBDaGVjay1vdXQ6CiAgIGRvbSAxNiBu
b3YgMjAyNQoKICAgTm9tZSBzdHJ1dHR1cmE6CiAgIE5ldyBFcmEgU3VpdGUgLSBEdW9tbyBkaSBQ
ZXJ1Z2lhIENlbnRybyBTdG9yaWNvCgogICBOdW1lcm8gZGkgcHJlbm90YXppb25lOgogICA1OTkw
NTQ4ODM3CgogICBPc3BpdGkgdG90YWxpOgogICA0CgogICBUb3RhbGUgZGVsbGUgY2FtZXJlOgog
ICAxCgogICDCqSBDb3B5cmlnaHQgQm9va2luZy5jb20gMjAyNQogICBRdWVzdGEgZS1tYWlsIHRp
IMOoIHN0YXRhIGludmlhdGEgZGEgQm9va2luZy5jb20KCiAgIEFsIG1vbWVudG8sIGxhIHR1YSBp
c2NyaXppb25lIGFsbGEgbmV3c2xldHRlciBkaSBCb29raW5nLmNvbSDDqCBhdHRpdmEuCiAgIFNh
cGV2aSBjaGUgcHVvaSBtb2RpZmljYXJlIGxlIHR1ZSBwcmVmZXJlbnplIGUgaW1wb3N0YXJlIGxl
IHJpc3Bvc3RlCiAgIGF1dG9tYXRpY2hlIHBlciBhbGN1bmkgbWVzc2FnZ2kgZGVnbGkgb3NwaXRp
PwoKICAgUXVlc3RhIGUtbWFpbCDDqCBzdGF0YSBpbnZpYXRhIGE6IHNob3J0ZGVzZW9zQGdtYWls
LmNvbQogICAgICAgICAgICAgICAgICAgICAgICAgIE1vZGlmaWNhIGxlIHR1ZSBwcmVmZXJlbnpl
CgogICAqQm9va2luZy5jb20gcmljZXZlcsOgIGVkIGVsYWJvcmVyw6AgbGUgcmlzcG9zdGUgYSBx
dWVzdGEgZS1tYWlsLCBjb21lCiAgIHNwZWNpZmljYXRvIG5lbGwnSW5mb3JtYXRpdmEgc3VsbGEg
UHJpdmFjeSBlIHN1aSBDb29raWUgZGkgQm9va2luZy5jb20uCiAgIElsIGNvbnRlbnV0byBkaSBx
dWVzdG8gbWVzc2FnZ2lvIG5vbiDDqCBzdGF0byBnZW5lcmF0byBkYSBCb29raW5nLmNvbSwKICAg
cXVpbmRpIEJvb2tpbmcuY29tIG5vbiBuZSDDqCByZXNwb25zYWJpbGUuCgoKCiAgIFtlbWFpbF9v
cGVuZWRfdHJhY2tpbmdfcGl4ZWw/bGFuZz1pdCZhbXA7YWlkPTMwNDE0MiZhbXA7dG9rZW49NTI2
MTZlNjQ2CiAgIGY2ZDQ5NTYyNDczNjQ2NTIzMjg3ZDYxY2MwNDg0NDdkMTgyYmRmMjgzYmEwMTA1
NTFmZjdmNDA5NjE5ODViY2MyZDFhOTljCiAgIDFhOTQ0MmNhYzNjMWE5YmQyMzAwZDQ4NjNhMGM0
NmJhM2FmYTIxNWEyNzEyYjRkNzE2MzBiNzA1NDAxNWU1MDdlNGI4YTVmCiAgIGM0MTRiOGI1NWRi
NGIyYWQ5NjBmNGUzM2E3OWNlN2RlNzI5N2FmZmVmOGY4OGQ4Y2VjNTcwMmUzMDA5MDIyZmJlNWU2
ODI2CiAgIGU4MTIxMjMyZTdmZDlmNjNjNTFkZjNiNjQwNTc2MjQ4NjFkZTA0MTU4MzZlYzM5NDRk
JmFtcDt0eXBlPXRvX2hvdGVsX2ZyCiAgIGVlX3RleHRdCg==
--_----------=_176309773829844
Content-Type: multipart/related; boundary="_----------=_176309773829845"
Date: Fri, 14 Nov 2025 06:22:18 +0100

--_----------=_176309773829845
Content-Transfer-Encoding: base64
Content-Type: text/html; charset=utf-8
Date: Fri, 14 Nov 2025 06:22:18 +0100

PCFET0NUWVBFIGh0bWwgUFVCTElDICItLy9XM0MvL0RURCBYSFRNTCAxLjAgVHJhbnNpdGlvbmFs
Ly9FTiIgImh0dHA6Ly93d3cudzMub3JnL1RSL3hodG1sMS9EVEQveGh0bWwxLXRyYW5zaXRpb25h
bC5kdGQiPgo8aHRtbCB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMTk5OS94aHRtbCIgeG1sbnM6
dj0idXJuOnNjaGVtYXMtbWljcm9zb2Z0LWNvbTp2bWwiPgogPGhlYWQ+CiAgPHRpdGxlPkFiYmlh
bW8gcmljZXZ1dG8gcXVlc3RvIG1lc3NhZ2dpbyBkYSBTYWx2YXRvcmUgQnJhY2NpYW50ZTwvdGl0
bGU+CiAgPHN0eWxlIHR5cGU9InRleHQvY3NzIj4KLkV4dGVybmFsQ2xhc3Mge3dpZHRoOjEwMCU7
fQouRXh0ZXJuYWxDbGFzcywgLkV4dGVybmFsQ2xhc3MgcCwgLkV4dGVybmFsQ2xhc3Mgc3



