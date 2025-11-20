import "@parsers/bootstrap";
import { parseEmail } from "@parsers/index";

describe("Scidoo confirm parser", () => {
  it("normalises reservation details including totals and services", () => {
    const body = `
Agenzia Prenotante=0944813 -> Booking
ID Voucher=5958915259
Camera/Alloggio=091 Suite Maggiore
Struttura Richiesta=09Piazza Danti Perugia Centro
Stato Prenotazione=09Confermata
Tariffa=09Pernottamento
Ospiti=092 Adulti
Nome Ospite=09Brufani Francesco
Email:fbrufa.422334@guest.booking.com
Cellulare:+39 331 5681407
Data di Check-in=0915/01/2026
Data di Check-out=0918/01/2026
Commissione=0948.52
---------------------------------------------------------------
Servizi Prenotati
N.3 Pernottamento
N.3 Pernottamento
N.1 Pulizia Suite Small
---------------------------------------------------------------
Totale Retta: 259,55 €
Totale Extra: 90,00 €
Totale Prenotazione: 349,55 €
Note:
Prenotazione PRE-PAID (Pagamento effettuato tramite Bonifico)
`;

    const html = `
      <html>
        <body>
          <p><strong>ID Prenotazione:</strong> 5958915259</p>
          <p><strong>Struttura Richiesta:</strong> Piazza Danti Perugia Centro</p>
          <p><strong>Camera:</strong> 1 Suite Maggiore</p>
          <p><strong>Totale Prenotazione:</strong> 349,55 €</p>
          <p><strong>Stato Prenotazione:</strong> Confermata</p>
        </body>
      </html>
    `;

    const payload = parseEmail({
      headers: {
        from: "Scidoo Booking Manager <reservation@scidoo.com>",
        subject: "Confermata - Prenotazione ID 5958915259 - Booking",
        date: "Thu, 23 Oct 2025 09:42:29 +0000",
      },
      body,
      html,
    });

    expect(payload).not.toBeNull();
    expect(payload?.source).toBe("scidoo_confirm");
    expect(payload?.reservationId).toBe("5958915259");
    expect(payload?.reservationStatus).toBe("Confermata");
    expect(payload?.guestName).toBe("Brufani Francesco");
    expect(payload?.clientEmail).toBe("fbrufa.422334@guest.booking.com");
    expect(payload?.clientPhone).toBe("+39 331 5681407");
    expect(payload?.stayPeriod?.start.toISOString()).toContain("2026-01-15");
    expect(payload?.stayPeriod?.end.toISOString()).toContain("2026-01-18");
    expect(payload?.totals?.amount).toBeCloseTo(349.55, 2);
    expect(payload?.totals?.extras).toBeCloseTo(90, 2);
    expect(payload?.totals?.baseRate).toBeCloseTo(259.55, 2);
    expect(payload?.totals?.commission).toBeCloseTo(48.52, 2);
    expect(payload?.totals?.currency).toBe("EUR");
    expect(payload?.services).toEqual(["Pernottamento", "Pulizia Suite Small"]);
    expect(payload?.paymentStatus).toBe("PRE-PAID");
    expect(payload?.notes?.[0]).toContain("Bonifico");
    expect(payload?.propertyName).toBe("Piazza Danti Perugia Centro");
    expect(payload?.roomName).toBe("1 Suite Maggiore");
    expect(payload?.metadata?.agency).toBe("Booking");
    expect(payload?.metadata?.createdAt).toContain("2025-10-23");
  });
});


