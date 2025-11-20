import "@parsers/bootstrap";
import { parseEmail } from "@parsers/index";

describe("Airbnb confirm parser", () => {
  it("extracts reservation metadata from confirmation email", () => {
    const body = `
      Prenotazione confermata!
      Codice di conferma: HMPBBAR2AN
      Ospite: Marie-Thérèse Weber-Gobet
      Alloggio: Imperial Suite - Palazzo della Staffa
      Check-in: 12 ottobre 2025
      Check-out: 19 ottobre 2025
      https://www.airbnb.com/messaging/thread/2311813630
    `;

    const html = `
      <html>
        <body>
          <p>Prenotazione confermata!</p>
          <p><strong>Codice di conferma:</strong> HMPBBAR2AN</p>
          <p><strong>Ospite:</strong> Marie-Thérèse Weber-Gobet</p>
          <p><strong>Alloggio:</strong> Imperial Suite - Palazzo della Staffa</p>
          <p>12 ottobre 2025 – 19 ottobre 2025</p>
          <a href="https://www.airbnb.com/messaging/thread/2311813630">Apri thread</a>
        </body>
      </html>
    `;

    const payload = parseEmail({
      headers: {
        from: "Airbnb <automated@airbnb.com>",
        to: "Host Example <host@example.com>",
      },
      body,
      html,
    });

    expect(payload).not.toBeNull();
    expect(payload?.source).toBe("airbnb_confirm");
    expect(payload?.reservationId).toBe("HMPBBAR2AN");
    expect(payload?.conversationId).toBe("2311813630");
    expect(payload?.guestName).toBe("Marie-Thérèse Weber-Gobet");
    expect(payload?.propertyName).toBe("Imperial Suite - Palazzo della Staffa");
    expect(payload?.hostEmail).toBe("host@example.com");
    expect(payload?.stayPeriod?.start.toISOString()).toContain("2025-10-12");
    expect(payload?.stayPeriod?.end.toISOString()).toContain("2025-10-19");
    expect(payload?.reservationStatus).toBe("confirmed");
    expect(payload?.metadata?.propertyName).toBe("Imperial Suite - Palazzo della Staffa");
  });
});

