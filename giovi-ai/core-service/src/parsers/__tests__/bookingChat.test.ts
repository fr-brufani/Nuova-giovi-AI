import "@parsers/bootstrap";
import { parseEmail } from "@parsers/index";

const BASE64_BODY =
  "IyMjLS0gU2NyaXZpIGxhIHR1YSByaXNwb3N0YSBzb3ByYSBxdWVzdGEgcmlnYSAtLQpOdW92byBtZXNzYWdnaW8gZGEgRnJhbmNlc2NvIEJydWZhbmkKTnVtZXJvIGRpIGNvbmZlcm1hOiA1OTU4OTE1MjU5CgpCdW9uZ2lvcm5vLCBhcnJpdmVyw7IgYWxsZSAxOC4K";

describe("Booking.com chat parser", () => {
  it("extracts reservation id and message content", () => {
    const html = `
      <html>
        <body>
          <p>Abbiamo ricevuto questo messaggio da <strong>Francesco Brufani</strong></p>
          <p>Numero di conferma: 5958915259</p>
          <p>Buongiorno, arriverò alle 18.</p>
          <a href="mailto:5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com">
            Rispondi dal portale
          </a>
        </body>
      </html>
    `;

    const payload = parseEmail({
      headers: {
        from: "Francesco Brufani via Booking.com <5958915259-5SOHK3QNF9YIHBV5Y31KZI0P5.2STIR9MYHHTXL7M69M0Y4JIUQ@mchat.booking.com>",
        subject: "Abbiamo ricevuto questo messaggio da Francesco Brufani",
        date: "Thu, 23 Oct 2025 11:43:28 +0200",
      },
      body: BASE64_BODY,
      html,
    });

    expect(payload).not.toBeNull();
    expect(payload?.source).toBe("booking_chat");
    expect(payload?.reservationId).toBe("5958915259");
    expect(payload?.conversationId).toBe("5958915259");
    expect(payload?.guestName).toBe("Francesco Brufani");
    expect(payload?.messageText).toContain("Buongiorno, arriverò alle 18.");
    expect(payload?.metadata?.subject).toBe("Abbiamo ricevuto questo messaggio da Francesco Brufani");
    expect(payload?.metadata?.sentAt).toContain("2025-10-23");
    expect(payload?.channel).toBe("booking");
  });
});


