import "@parsers/bootstrap";
import { parseEmail } from "@parsers/index";

const BASE64_BODY =
  "IyMjLS0gU2NyaXZpIGxhIHR1YSByaXNwb3N0YSBzb3ByYSBxdWVzdGEgcmlnYSAtLQpNZXNzYWdnaW8gZGEgRnJhbmNlc2NvIEJydWZhbmkKTnVtZXJvIGRpIGNvbmZlcm1hOiAyMzExODEzNjMwCgpDaWFvISBBcnJpdmVyZW1vIGFsbGUgMTguCg==";

describe("Airbnb message parser", () => {
  it("extracts conversation details from inbound guest messages", () => {
    const html = `
      <html>
        <body>
          <p>Nuovo messaggio da <strong>Francesco Brufani</strong></p>
          <p>Numero di conferma: 2311813630</p>
          <p>Ciao! Arriveremo alle 18.</p>
          <a href="https://www.airbnb.com/messaging/thread/2311813630">Rispondi</a>
        </body>
      </html>
    `;

    const payload = parseEmail({
      headers: {
        from: "Francesco Brufani via Airbnb <thread_2311813630@reply.airbnb.com>",
        subject: "Nuovo messaggio da Francesco Brufani",
        date: "Thu, 23 Oct 2025 11:43:28 +0200",
      },
      body: BASE64_BODY,
      html,
    });

    expect(payload).not.toBeNull();
    expect(payload?.source).toBe("airbnb_message");
    expect(payload?.conversationId).toBe("2311813630");
    expect(payload?.guestName).toBe("Francesco Brufani");
    expect(payload?.messageText).toContain("Ciao! Arriveremo alle 18.");
    expect(payload?.metadata?.subject).toBe("Nuovo messaggio da Francesco Brufani");
    expect(payload?.metadata?.sentAt).toContain("2025-10-23");
  });
});


