// *** IMPORT V2 ***
import { https, logger } from "firebase-functions/v2"; // Importa da V2
import * as admin from "firebase-admin";
import { GoogleGenerativeAI, HarmCategory, HarmBlockThreshold } from "@google/generative-ai";

// Inizializza Firebase Admin SDK
admin.initializeApp();

// --- CONFIGURAZIONE GEMINI ---
const API_KEY = "AIzaSyBI6RyDafRa-raBIdQ0qXq5K82AQYIHCXo"; // <-- TUA CHIAVE REALE

// Controllo che la chiave non sia vuota
if (!API_KEY) {
  logger.error("ERRORE CRITICO: Chiave API Gemini è vuota o non definita in index.ts!");
}

// Inizializza il client Gemini solo se la chiave è presente
let geminiModel: any;
if (API_KEY) {
  try {
    const genAI = new GoogleGenerativeAI(API_KEY);
    geminiModel = genAI.getGenerativeModel({
      model: "gemini-pro",
      safetySettings: [
        {
          category: HarmCategory.HARM_CATEGORY_HARASSMENT,
          threshold: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        },
        {
          category: HarmCategory.HARM_CATEGORY_HATE_SPEECH,
          threshold: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        },
        {
          category: HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
          threshold: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        },
        {
          category: HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
          threshold: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        },
      ],
    });
    logger.info("Client Gemini inizializzato con successo.");
  } catch (initError) {
    logger.error(
      "Errore durante l'inizializzazione di Gemini (possibile chiave non valida?):",
      initError,
    );
  }
} else {
  logger.error("ERRORE CRITICO: Impossibile inizializzare Gemini - Chiave API mancante.");
}

// *** DEFINIZIONE FUNZIONE V2 ***
export const getAiChatResponse = https.onCall(
  {
    region: "europe-west1", // Specifica la tua regione
  },
  async (request: https.CallableRequest<any>): Promise<{ reply: string }> => {
    const contextAuth = request.auth;
    const data = request.data;

    // 1. Autenticazione
    if (!contextAuth) {
      logger.error("Chiamata non autenticata.");
      throw new https.HttpsError("unauthenticated", "Autenticazione richiesta.");
    }

    // 2. Validazione Input
    const userMessage = data?.message as string | undefined;
    const hostId = data?.hostId as string | undefined;
    const propertyId = data?.propertyId as string | undefined;
    if (!userMessage || !hostId || !propertyId) {
      logger.error("Input mancanti:", { data });
      throw new https.HttpsError(
        "invalid-argument",
        "Input mancanti (message, hostId, propertyId).",
      );
    }

    const clientUid = contextAuth.uid;
    logger.info(
      `Richiesta da client: ${clientUid}, Alloggio: ${propertyId}, Messaggio: ${userMessage}`,
    );

    // 3. Verifica Permessi Cliente
    try {
      const clientDoc = await admin.firestore().collection("users").doc(clientUid).get();
      if (
        !clientDoc.exists ||
        clientDoc.data()?.role !== "client" ||
        clientDoc.data()?.assignedHostId !== hostId ||
        clientDoc.data()?.assignedPropertyId !== propertyId
      ) {
        logger.warn(
          `Utente ${clientUid} non autorizzato per alloggio ${propertyId} dell'host ${hostId}`,
        );
        throw new https.HttpsError("permission-denied", "Non sei autorizzato per questo alloggio.");
      }
    } catch (e) {
      logger.error("Errore verifica permessi cliente:", e);
      throw new https.HttpsError("internal", "Errore verifica permessi.");
    }

    // 4. Recupera Dati Alloggio
    try {
      const propertyDocRef = admin
        .firestore()
        .collection("users")
        .doc(hostId)
        .collection("properties")
        .doc(propertyId);
      const propertySnapshot = await propertyDocRef.get();

      if (!propertySnapshot.exists) {
        logger.error(`Alloggio non trovato: users/${hostId}/properties/${propertyId}`);
        throw new https.HttpsError("not-found", "Alloggio non trovato.");
      }
      const propertyData = propertySnapshot.data();
      if (!propertyData) {
        logger.error(`Dati alloggio corrotti: users/${hostId}/properties/${propertyId}`);
        throw new https.HttpsError("internal", "Dati alloggio corrotti.");
      }

      // 5. Prepara il Prompt per Gemini
      let contextString = "INFORMAZIONI SULL'ALLOGGIO FORNITE DALL'HOST:\n";
      for (const [key, value] of Object.entries(propertyData)) {
        if (
          key !== "createdAt" &&
          key !== "photos" &&
          value !== null &&
          value !== "" &&
          (!Array.isArray(value) || value.length > 0)
        ) {
          if (Array.isArray(value)) {
            contextString += `- ${key}:\n`;
            value.forEach((item: any) => {
              const itemString = Object.entries(item)
                .map(([k, v]) => `${k}: ${v}`)
                .join(", ");
              contextString += `  - ${itemString}\n`;
            });
          } else {
            contextString += `- ${key}: ${value}\n`;
          }
        }
      }

      const prompt = `Sei "Giovi AI", un assistente concierge virtuale amichevole, preciso e disponibile per l'alloggio chiamato "${propertyData.name}". Il tuo compito è rispondere alle domande dell'ospite basandoti ESCLUSIVAMENTE sulle INFORMAZIONI SULL'ALLOGGIO FORNITE DALL'HOST qui sotto.
Se la risposta si trova nelle informazioni, forniscila in modo chiaro e conciso, usando solo i dettagli presenti.
Se l'informazione richiesta NON è presente nelle informazioni fornite, rispondi *esattamente* e *solo* con: "Mi dispiace, non ho questa informazione specifica. Ti suggerisco di contattare direttamente l'host per dettagli." Non inventare nulla, non fare supposizioni e non aggiungere altre frasi.

${contextString}
DOMANDA OSPITE:
"${userMessage}"

RISPOSTA GIOVI AI:
`;

      logger.info("Prompt per Gemini (Inizio):", { promptStart: prompt.substring(0, 500) + "..." });

      // 6. Chiama l'API di Gemini
      if (!geminiModel) {
        logger.error("Tentativo di chiamata a Gemini fallito - modello non inizializzato.");
        throw new https.HttpsError(
          "failed-precondition",
          "Assistente AI non disponibile (Errore Inizializzazione).",
        );
      }
      try {
        const result = await geminiModel.generateContent(prompt);
        const response = result.response;
        if (!response || response.promptFeedback?.blockReason) {
          logger.warn("Risposta Gemini bloccata o non valida:", response?.promptFeedback);
          throw new https.HttpsError(
            "internal",
            `L'assistente AI non ha potuto rispondere (contenuto bloccato o risposta non valida: ${response?.promptFeedback?.blockReason || "N/D"}).`,
          );
        }
        const aiResponseText = response.text();

        logger.info("Risposta da Gemini:", { response: aiResponseText });

        // 7. Ritorna la risposta all'app Flutter
        return { reply: aiResponseText };
      } catch (geminiError: any) {
        logger.error("Errore chiamata API Gemini:", geminiError);
        let errorMessage = "L'assistente AI ha riscontrato un problema nel generare la risposta.";
        if (geminiError.message) {
          errorMessage += ` Dettagli: ${geminiError.message}`;
        }
        if (geminiError.status) {
          errorMessage += ` (Status: ${geminiError.status})`;
        }
        if (
          geminiError.message?.includes("API key not valid") ||
          geminiError.message?.includes("API key invalid")
        ) {
          errorMessage =
            "Errore di configurazione dell'assistente AI (Chiave API non valida). Contatta il supporto.";
        }
        throw new https.HttpsError("internal", errorMessage);
      }
    } catch (error) {
      // Catch errori Firestore o altri errori generali
      logger.error("Errore generale in getAiChatResponse:", error);
      if (error instanceof https.HttpsError) {
        throw error; // Rilancia errori HttpsError specifici
      } else {
        // Maschera altri errori interni
        throw new https.HttpsError("internal", "Errore interno del server.");
      }
    }
  }, // Chiusura della funzione async (request) => ...
); // Chiusura di https.onCall
