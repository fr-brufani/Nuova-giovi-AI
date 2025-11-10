// workflow-service/src/server.ts
import express, { Request, Response } from 'express';
import cors from 'cors';
import * as admin from 'firebase-admin';
import axios from 'axios';
// --- Inizializzazioni ---
admin.initializeApp();
const firestore = admin.firestore();
const FieldValue = admin.firestore.FieldValue;
const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// --- Costanti e Configurazioni ---
const PORT = process.env.PORT || 8080;

const GEMINI_PROXY_SERVICE_URL = process.env.GEMINI_PROXY_SERVICE_URL;
if (!GEMINI_PROXY_SERVICE_URL && process.env.NODE_ENV !== 'test') {
    console.error("Workflow CRITICAL ERROR: GEMINI_PROXY_SERVICE_URL environment variable is not set.");
}
const GEMINI_PROXY_SEND_WA_ENDPOINT = `${GEMINI_PROXY_SERVICE_URL}/system/send-whatsapp`;

const WORKFLOW_TO_GEMINI_PROXY_API_KEY = process.env.WORKFLOW_TO_GEMINI_PROXY_API_KEY;
if (!WORKFLOW_TO_GEMINI_PROXY_API_KEY && process.env.NODE_ENV !== 'test') {
    console.warn("Workflow WARNING: WORKFLOW_TO_GEMINI_PROXY_API_KEY is not set. Calls to Gemini Proxy will fail.");
}

const PROPERTY_TASKS_COLLECTION = 'propertyTasks';
const USERS_COLLECTION = 'users';
const PROPERTIES_SUBCOLLECTION = 'properties';
const RESERVATIONS_COLLECTION = 'reservations'; // Aggiunta per getReservationDetails
const CHAT_LOG_COLLECTION = 'gioviAiChatDataset';

// --- Interfacce ---
interface ToolCallContext {
    propertyId: string;
    hostId: string;
    clientId: string; // UID Firebase del cliente
    originalUserMessage: string;
    originalChannel: "app" | "whatsapp";
}

interface InitiateCleaningArgs {
    clientNotes?: string;
}

interface RequestTechnicianArgs {
    technicianType: string;
    issueDescription: string;
}

interface ToolCallPayload {
    toolName: "initiateCleaning" | "requestTechnician" | string;
    toolArgs: InitiateCleaningArgs | RequestTechnicianArgs | any;
    context: ToolCallContext;
}

interface ProviderResponsePayload {
    source: "provider_response";
    providerPhoneNumber: string;
    providerMessageText: string;
    relatedTaskId: string;
    originalClientContext: {
        clientId: string;
        hostId: string;
        propertyId: string;
        originalChannel: "app" | "whatsapp";
    };
}

interface ProviderContact {
    name?: string;
    phone?: string;
    type?: string;
    description?: string;
}

interface PropertyData {
    name?: string;
    address?: string;
    cleaningContactName?: string;
    cleaningAgencyName?: string;
    cleaningContactPhone?: string;
    contacts?: ProviderContact[];
    // Aggiungere altri campi rilevanti se necessario
}

interface GeminiProxySendWaResponse { // Risposta attesa dal proxy
    success: boolean;
    messageId?: string;
    message?: string; // Messaggio di successo o errore dal proxy
    error?: string;   // Dettaglio errore dal proxy
    details?: any;    // Ulteriori dettagli (es. errore Meta)
}


// Interfaccia personalizzata per descrivere un errore Axios
interface MyAxiosError extends Error { // Estende Error per avere name, message, stack
    isAxiosError: true; // Proprietà chiave per identificare l'errore Axios
    response?: {
        data?: any; // Il corpo della risposta dell'errore
        status?: number; // Codice di stato HTTP (es. 400, 401, 500)
        headers?: any; // Headers della risposta
    };
    request?: any; // L'oggetto richiesta che ha generato l'errore
    config?: any;  // La configurazione Axios usata per la richiesta
    code?: string; // Codice errore specifico (es. 'ECONNABORTED')
}



// --- INIZIO MODIFICHE PER TEMPLATE WHATSAPP ---
// Interfaccia per i parametri del messaggio da inviare via proxy
interface ProxyMessagePayload {
    to: string;
    text?: string; // Per messaggi di testo semplici
    templateName?: string; // Per messaggi template
    templateLanguageCode?: string; // Es. "it", opzionale
    templateParams?: (string | number | null | undefined)[]; // Parametri per il template
    hostId?: string; // Per contesto nel log del proxy
    propertyId?: string; // Per contesto nel log del proxy
    relatedTaskId?: string; // Per contesto nel log del proxy
}
// --- FINE MODIFICHE PER TEMPLATE WHATSAPP ---


// --- Funzioni Helper ---

async function getPropertyDetails(hostId: string, propertyId: string): Promise<PropertyData | null> {
    try {
        const propertyDocRef = firestore.collection(USERS_COLLECTION).doc(hostId).collection(PROPERTIES_SUBCOLLECTION).doc(propertyId);
        const propertySnapshot = await propertyDocRef.get();
        if (!propertySnapshot.exists) {
            console.error(`Workflow: Property not found: hostId=${hostId}, propertyId=${propertyId}`);
            return null;
        }
        return propertySnapshot.data() as PropertyData;
    } catch (error) {
        console.error(`Workflow: Error fetching property details ${propertyId}:`, error);
        return null;
    }
}

async function getClientDetails(clientId: string): Promise<{ name?: string; email?: string; whatsappPhoneNumber?: string } | null> {
    try {
        const clientDocRef = firestore.collection(USERS_COLLECTION).doc(clientId);
        const clientSnapshot = await clientDocRef.get();
        if (!clientSnapshot.exists) {
            console.error(`Workflow: Client (UID: ${clientId}) not found.`);
            return null;
        }
        const data = clientSnapshot.data();
        return {
            name: data?.name,
            email: data?.email,
            whatsappPhoneNumber: data?.whatsappPhoneNumber // Deve essere E.164
        };
    } catch (error) {
        console.error(`Workflow: Error fetching client details for UID ${clientId}:`, error);
        return null;
    }
}


// --- INIZIO MODIFICHE PER TEMPLATE WHATSAPP ---
async function sendWhatsAppMessageViaProxy(
    recipientPhoneNumberE164: string,
    messageOrTemplateName: string, // Può essere il testo del messaggio o il nome del template
    // Se il terzo parametro è un array, è templateParams. Altrimenti è l'oggetto context.
    paramsOrContext?: (string | number | null | undefined)[] | { taskId?: string; clientId?: string; hostId?: string; propertyId?: string; relatedTaskId?: string },
    optionalContext?: { taskId?: string; clientId?: string; hostId?: string; propertyId?: string; relatedTaskId?: string }
): Promise<boolean> {
    if (!GEMINI_PROXY_SERVICE_URL) {
        console.error("Workflow: GEMINI_PROXY_SERVICE_URL is not configured. Cannot send WhatsApp.");
        return false;
    }
    if (!WORKFLOW_TO_GEMINI_PROXY_API_KEY) {
        console.error("Workflow: WORKFLOW_TO_GEMINI_PROXY_API_KEY is not configured. Cannot send WhatsApp.");
        return false;
    }
    if (!recipientPhoneNumberE164 || !messageOrTemplateName) {
        console.error("Workflow: Recipient phone number or message/template name missing for sendWhatsAppMessageViaProxy.");
        return false;
    }

    const finalRecipientNumber = recipientPhoneNumberE164.startsWith('+')
        ? recipientPhoneNumberE164
        : `+${recipientPhoneNumberE164}`;

    const payload: ProxyMessagePayload = { // Usa l'interfaccia ProxyMessagePayload
        to: finalRecipientNumber,
    };

    let context: { taskId?: string; clientId?: string; hostId?: string; propertyId?: string; relatedTaskId?: string } | undefined;
    let logPreview: string;

    if (Array.isArray(paramsOrContext)) { // È un invio di template
        payload.templateName = messageOrTemplateName;
        // Assicura che i parametri siano stringhe o stringhe vuote se null/undefined
        payload.templateParams = paramsOrContext.map(p => (p === null || p === undefined) ? "" : String(p));
        payload.templateLanguageCode = "it"; // Puoi renderlo parametrizzabile se necessario
        context = optionalContext;
        logPreview = `template '${payload.templateName}' with params ${JSON.stringify(payload.templateParams.slice(0,2))}...`; // Log dei primi parametri
    } else { // È un invio di messaggio di testo semplice
        payload.text = messageOrTemplateName;
        context = paramsOrContext as { taskId?: string; clientId?: string; hostId?: string; propertyId?: string; relatedTaskId?: string } | undefined;
        logPreview = `text "${(payload.text || '').substring(0, 50)}..."`;
    }

    // Aggiungi il contesto al payload se presente
    if (context) {
        payload.hostId = context.hostId;
        payload.propertyId = context.propertyId;
        payload.relatedTaskId = context.taskId || context.relatedTaskId;
    }

    try {
        console.log(`Workflow: Attempting to send WA to ${finalRecipientNumber} via proxy: ${logPreview}`);
        const response = await axios.post<GeminiProxySendWaResponse>(
            GEMINI_PROXY_SEND_WA_ENDPOINT,
            payload,
            {
                headers: {
                    'x-system-api-key': WORKFLOW_TO_GEMINI_PROXY_API_KEY,
                    'Content-Type': 'application/json',
                },
                timeout: 20000, // Timeout leggermente aumentato
            }
        );
        console.log(`Workflow: WhatsApp send request (type: ${payload.templateName ? 'template' : 'text'}) to ${finalRecipientNumber} forwarded to proxy. Proxy response status: ${response.status}, Proxy success: ${response.data?.success}`);

        if (response.status === 200 && response.data?.success === true) {
            return true;
        } else {
            console.warn(`Workflow: Proxy indicated failure or non-200 status for WA send to ${finalRecipientNumber}. Status: ${response.status}, Data:`, response.data);
            // Logga i dettagli dell'errore di Meta se il proxy li inoltra
            if (response.data?.details) {
                console.error('Workflow: Meta Template Error Details (from proxy):', response.data.details);
            }
            return false;
        }
    } catch (error: any) {
        console.error(`Workflow: Error sending WhatsApp message to ${finalRecipientNumber} via proxy:`);
        // Controlla se l'errore è un AxiosError verificando la presenza della proprietà 'isAxiosError'
        // e che il suo valore sia true. Questo è un type guard più sicuro.
        if (error && typeof error === 'object' && error.isAxiosError === true) {
            // Ora TypeScript sa che 'error' è di tipo AxiosError (o qualcosa che si comporta come tale)
            const axiosError = error as MyAxiosError; // Type assertion usando l'AxiosError importato
            const errResponse = axiosError.response;
            console.error('Proxy Error Status:', errResponse?.status);
            console.error('Proxy Error Data:', JSON.stringify(errResponse?.data, null, 2));
            // Prova ad accedere a errResponse.data.details in modo sicuro
            const responseData = errResponse?.data as any; // Cast a 'any' se la struttura di 'data' non è nota
            if (responseData?.details) {
                console.error('Workflow: Meta Template Error Details (from proxy via catch):', responseData.details);
            }
        } else if (error && typeof error === 'object' && 'message' in error) {
            console.error('Generic WA send error:', (error as { message: string }).message);
        } else {
            console.error('Unknown WA send error:', JSON.stringify(error));
        }
        return false;
    }
}

async function getReservationDetails(
    currentClientId: string,
    propertyId: string,
    hostId: string // Incluso per coerenza, anche se non usato direttamente nelle query qui
): Promise<{ checkoutDate: string; nextCheckinDateForProperty: string }> {
    // Valori di fallback nel caso non si trovino informazioni
    let checkoutDateStr: string = "Non specificato";
    let nextCheckinDateForPropertyStr: string = "Non ancora programmato";

    const now = admin.firestore.Timestamp.now();
    const reservationsRef = firestore.collection(RESERVATIONS_COLLECTION);

    try {
        // 1. Trova la prenotazione del cliente corrente per questa proprietà che è attiva o appena terminata
        const clientReservationSnapshot = await reservationsRef
            .where('propertyId', '==', propertyId)
            .where('clientId', '==', currentClientId)
            // Considera prenotazioni che terminano da poco o sono in corso
            // .where('endDate', '>=', admin.firestore.Timestamp.fromDate(new Date(now.toDate().getTime() - (7 * 24 * 60 * 60 * 1000)))) // Opzionale: ultimi 7gg
            .orderBy('endDate', 'desc')
            .limit(1)
            .get();

        let clientReservationData: admin.firestore.DocumentData | undefined;
        let clientCheckoutDate: Date | null = null;

        if (!clientReservationSnapshot.empty) {
            clientReservationData = clientReservationSnapshot.docs[0].data();
            if (clientReservationData.endDate && clientReservationData.endDate.toDate) {
                clientCheckoutDate = clientReservationData.endDate.toDate();
            } else if (clientReservationData.endDate && typeof clientReservationData.endDate === 'string') {
                 clientCheckoutDate = new Date(clientReservationData.endDate);
            }
        } else {
            console.warn(`Workflow: No current/recent reservation found for client ${currentClientId} on property ${propertyId} to determine exact checkout time.`);
        }

        // Formattazione Data Checkout Cliente
        // Assumi che esista un campo 'allDayCheckout' (boolean) nella prenotazione se l'orario non è rilevante
        const checkoutFormatOptions: Intl.DateTimeFormatOptions = { day: '2-digit', month: 'long', year: 'numeric', timeZone: 'Europe/Rome' };
        if (clientCheckoutDate && !(clientReservationData?.allDayCheckout === true)) {
            checkoutFormatOptions.hour = '2-digit';
            checkoutFormatOptions.minute = '2-digit';
        }
        if (clientCheckoutDate) {
            checkoutDateStr = clientCheckoutDate.toLocaleDateString('it-IT', checkoutFormatOptions);
        }


        // 2. Trova il prossimo check-in per la proprietà, dopo il checkout del cliente (se disponibile) o da ora
        const referenceDateForNextCheckin = clientCheckoutDate || now.toDate(); // Usa checkout del cliente o 'ora' come riferimento

        const nextPropertyReservationSnapshot = await reservationsRef
            .where('propertyId', '==', propertyId)
            .where('startDate', '>', admin.firestore.Timestamp.fromDate(referenceDateForNextCheckin)) // Strettamente DOPO
            .orderBy('startDate', 'asc')
            .limit(1)
            .get();

        let nextCheckinDate: Date | null = null;
        if (!nextPropertyReservationSnapshot.empty) {
            const nextReservationData = nextPropertyReservationSnapshot.docs[0].data();
            // Assicurati che non sia la stessa prenotazione del cliente (improbabile con startDate > reference)
            if (nextPropertyReservationSnapshot.docs[0].id !== clientReservationSnapshot.docs[0]?.id) {
                if (nextReservationData.startDate && nextReservationData.startDate.toDate) {
                    nextCheckinDate = nextReservationData.startDate.toDate();
                } else if (nextReservationData.startDate && typeof nextReservationData.startDate === 'string') {
                    nextCheckinDate = new Date(nextReservationData.startDate);
                }
            }
        } else {
            console.log(`Workflow: No upcoming reservations found for property ${propertyId} after ${referenceDateForNextCheckin.toISOString()}.`);
        }

        // Formattazione Data Prossimo Check-in
        const checkinFormatOptions: Intl.DateTimeFormatOptions = { day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Rome' };
        if (nextCheckinDate) {
            nextCheckinDateForPropertyStr = nextCheckinDate.toLocaleDateString('it-IT', checkinFormatOptions);
        }

    } catch (error) {
        console.error(`Workflow: Error fetching reservation details for property ${propertyId} (client: ${currentClientId}):`, error);
        // I valori di fallback verranno usati
    }
    console.log(`Workflow: Reservation details for cleaning: Checkout=${checkoutDateStr}, NextCheckin=${nextCheckinDateForPropertyStr}`);
    return { checkoutDate: checkoutDateStr, nextCheckinDateForProperty: nextCheckinDateForPropertyStr };
}
// --- FINE MODIFICHE PER TEMPLATE WHATSAPP ---


async function saveTask(taskData: any): Promise<string | null> {
    try {
        const taskRef = firestore.collection(PROPERTY_TASKS_COLLECTION).doc();
        const dataToSave = {
            ...taskData,
            createdAt: FieldValue.serverTimestamp(),
            updatedAt: FieldValue.serverTimestamp(),
        };
        await taskRef.set(dataToSave);
        console.log(`Workflow: Task ${taskRef.id} created in Firestore. Data:`, JSON.stringify(dataToSave, null, 2));
        return taskRef.id;
    } catch (error) {
        console.error(`Workflow: Errore durante il salvataggio del task in Firestore:`, error);
        return null;
    }
}

async function updateTaskStatus(taskId: string, status: string, additionalUpdates: any = {}): Promise<boolean> {
    if (!taskId) {
        console.error("Workflow: updateTaskStatus chiamato senza taskId.");
        return false;
    }
    try {
        const taskRef = firestore.collection(PROPERTY_TASKS_COLLECTION).doc(taskId);
        const updatesToApply: any = {
            status: status,
            updatedAt: FieldValue.serverTimestamp(),
            ...additionalUpdates
        };
        Object.keys(updatesToApply).forEach(key => {
            if (updatesToApply[key] === undefined && !(updatesToApply[key] instanceof admin.firestore.FieldValue)) {
                delete updatesToApply[key];
            }
        });

        await taskRef.update(updatesToApply);
        console.log(`Workflow: Task ${taskId} aggiornato allo stato '${status}'. Updates:`, JSON.stringify(updatesToApply, null, 2));
        return true;
    } catch (error) {
        console.error(`Workflow: Errore durante l'aggiornamento dello stato del task ${taskId}:`, error);
        return false;
    }
}

async function handleProviderResponse(payload: ProviderResponsePayload): Promise<void> {
    const { providerPhoneNumber, providerMessageText, relatedTaskId, originalClientContext } = payload;
    console.log(`Workflow: Handling provider response from ${providerPhoneNumber} for task ${relatedTaskId}. Original client ${originalClientContext.clientId} (channel: ${originalClientContext.originalChannel}).`);

    const taskDocRef = firestore.collection(PROPERTY_TASKS_COLLECTION).doc(relatedTaskId);
    const taskSnapshot = await taskDocRef.get();

    if (!taskSnapshot.exists) {
        console.error(`Workflow: Task ${relatedTaskId} not found for provider response from ${providerPhoneNumber}. Cannot process.`);
        return;
    }
    const taskData = taskSnapshot.data();
    if (!taskData) {
        console.error(`Workflow: Task data missing for task ${relatedTaskId}. Cannot process.`);
        return;
    }

    if (taskData.providerContactInfo?.phone !== providerPhoneNumber) {
        console.warn(`Workflow: Provider phone number ${providerPhoneNumber} in payload does not match phone ${taskData.providerContactInfo?.phone} in task ${relatedTaskId}. Considering response for security, but logging warning.`);
        // Potrebbe essere una decisione di business se ignorare o processare comunque. Per ora, processiamo con un warning.
    }

    let newStatus = taskData.status;
    let clientNotificationMessage = `Aggiornamento per il tuo task ID ${relatedTaskId} (${taskData.taskType || 'N/A'}): Il fornitore (${taskData.providerContactInfo?.name || providerPhoneNumber}) ha risposto: "${providerMessageText}"`;
    let appointmentDetailsToSave: any = taskData.appointmentDetails || null;

    const lowerMessage = providerMessageText.toLowerCase();
    if (lowerMessage.includes("confermato") || lowerMessage.includes("ok") || lowerMessage.includes("va bene") || lowerMessage.includes("sì") || lowerMessage.includes("presente") || lowerMessage.includes("sarò lì")) {
        newStatus = "provider_confirmed";
        const timeMatch = providerMessageText.match(/(\d{1,2}\s*[:.]\s*\d{2})/);
        const dateKeywords = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica", "domani", "oggi"];
        const dateMatch = providerMessageText.match(new RegExp(`(${dateKeywords.join("|")})?\\s*(\\d{1,2}\\s*(?:gen(?:naio)?|feb(?:braio)?|mar(?:zo)?|apr(?:ile)?|mag(?:gio)?|giu(?:gno)?|lug(?:lio)?|ago(?:sto)?|set(?:tembre)?|ott(?:obre)?|nov(?:embre)?|dic(?:embre)?|[/-]?\\d{1,2}(?:[/-]?\\d{2,4})?))`, "i"));

        if (timeMatch || dateMatch) {
            newStatus = "appointment_scheduled";
            appointmentDetailsToSave = {
                fullProviderResponse: providerMessageText,
                extractedTime: timeMatch ? timeMatch[0].replace(/\s/g, '') : (appointmentDetailsToSave?.extractedTime || null),
                extractedDateInfo: dateMatch ? dateMatch[0].trim() : (appointmentDetailsToSave?.extractedDateInfo || null),
            };
            clientNotificationMessage = `L'operatore per il task ${relatedTaskId} (${taskData.taskType || 'N/A'}) ha fornito un aggiornamento sull'appuntamento. Dettagli: "${providerMessageText}"`;
            if (appointmentDetailsToSave.extractedDateInfo && appointmentDetailsToSave.extractedTime) {
                 clientNotificationMessage = `Appuntamento per il task ${relatedTaskId} (${taskData.taskType || 'N/A'}) fissato per ${appointmentDetailsToSave.extractedDateInfo} alle ${appointmentDetailsToSave.extractedTime}.`;
            } else if (appointmentDetailsToSave.extractedDateInfo) {
                clientNotificationMessage = `Appuntamento per il task ${relatedTaskId} (${taskData.taskType || 'N/A'}) fissato per ${appointmentDetailsToSave.extractedDateInfo}. L'orario esatto verrà confermato a breve.`;
            } else if (appointmentDetailsToSave.extractedTime) {
                clientNotificationMessage = `Appuntamento per il task ${relatedTaskId} (${taskData.taskType || 'N/A'}) fissato per le ore ${appointmentDetailsToSave.extractedTime}. La data esatta verrà confermata a breve.`;
            }
        }
    } else if (lowerMessage.includes("non posso") || lowerMessage.includes("annulla") || lowerMessage.includes("impossibile") || lowerMessage.includes("non disponibile")) {
        newStatus = "provider_declined";
        clientNotificationMessage = `L'operatore per il task ${relatedTaskId} (${taskData.taskType || 'N/A'}) ha indicato di non essere disponibile o ha annullato. Messaggio: "${providerMessageText}". Stiamo cercando alternative o verrai ricontattato.`;
    }

    await updateTaskStatus(relatedTaskId, newStatus, {
        providerResponse: providerMessageText,
        appointmentDetails: appointmentDetailsToSave || FieldValue.delete(),
        lastProviderResponseAt: FieldValue.serverTimestamp()
    });
    console.log(`Workflow: Task ${relatedTaskId} updated to status '${newStatus}'. Notifying client ${originalClientContext.clientId}.`);

    if (originalClientContext.originalChannel === "whatsapp") {
        const clientInfo = await getClientDetails(originalClientContext.clientId);
        if (clientInfo?.whatsappPhoneNumber) {
            // Invia testo semplice al cliente
            await sendWhatsAppMessageViaProxy(
                clientInfo.whatsappPhoneNumber,
                clientNotificationMessage, // Testo del messaggio
                { taskId: relatedTaskId, clientId: originalClientContext.clientId, hostId: originalClientContext.hostId, propertyId: originalClientContext.propertyId } // Contesto
            );
        } else {
            console.error(`Workflow: Cannot notify client UID ${originalClientContext.clientId} via WhatsApp: WhatsApp number not found.`);
        }
    } else if (originalClientContext.originalChannel === "app") {
        try {
            await firestore.collection(CHAT_LOG_COLLECTION).add({
                userId: originalClientContext.clientId,
                hostId: originalClientContext.hostId,
                propertyId: originalClientContext.propertyId,
                channel: "system",
                aiResponse: clientNotificationMessage,
                timestamp: FieldValue.serverTimestamp(),
                isSystemUpdate: true,
                relatedTaskId: relatedTaskId,
                userMessage: null, toolCallPublished: null, promptSent: null, wasBlocked: false, blockReason: null, processingError: null
            });
            console.log(`Workflow: System message update for task ${relatedTaskId} written to chat log for app user ${originalClientContext.clientId}.`);
        } catch (logError) {
            console.error(`Workflow: Error saving system update to chat log for user ${originalClientContext.clientId}:`, logError);
        }
    }
}


async function handleInitiateCleaning(payload: ToolCallPayload): Promise<void> {
    const { context, toolArgs } = payload;
    const { propertyId, hostId, clientId, originalUserMessage, originalChannel } = context;
    const args = toolArgs as InitiateCleaningArgs;

    console.log(`Workflow: Handling 'initiateCleaning' for property ${propertyId}, client ${clientId} (channel: ${originalChannel}).`);

    const propertyData = await getPropertyDetails(hostId, propertyId);
    if (!propertyData) {
        console.error(`Workflow: Property data ${propertyId} not found for cleaning task.`);
        return;
    }

    const cleaningContactPhone = propertyData.cleaningContactPhone;
    const contactName = propertyData.cleaningContactName || propertyData.cleaningAgencyName || "Servizio Pulizie";
    const propertyName = propertyData.name || "Proprietà Sconosciuta";

    const taskPayload: any = {
        propertyId, hostId, clientId, originalChannel,
        taskType: "cleaning",
        details: `Pulizia per '${propertyName}'. Note: ${args.clientNotes || 'N/A'}. Msg Utente: "${originalUserMessage}"`,
        providerContactInfo: { name: contactName, type: "Pulizie" }
    };

    if (!cleaningContactPhone) {
        console.warn(`Workflow: Cleaning contact not configured for property ${propertyId}.`);
        taskPayload.status = "failed_configuration";
        taskPayload.failureReason = "Contatto telefonico pulizie (E.164) non trovato/configurato.";
        await saveTask(taskPayload);
        // TODO: Notificare cliente/host del fallimento se necessario (potrebbe essere gestito da un messaggio di fallback dal proxy)
        return;
    }
    taskPayload.providerContactInfo.phone = cleaningContactPhone;
    taskPayload.status = "requested_by_client";

    const taskId = await saveTask(taskPayload);
    if (!taskId) {
        console.error("Workflow: Failed to create cleaning task in Firestore for property", propertyId);
        return;
    }

    // --- INIZIO MODIFICHE PER TEMPLATE ---
    const reservationDates = await getReservationDetails(clientId, propertyId, hostId);

    const templateParamsForCleaning = [
        contactName,                                                // {{1}} Nome Fornitore Pulizie
        propertyName,                                               // {{2}} Nome Alloggio
        reservationDates.checkoutDate,                              // {{3}} Check-out Ospite Precedente (già formattato)
        args.clientNotes || originalUserMessage.substring(0,200) || "Nessuna nota specifica.", // {{4}} Note Cliente (o messaggio utente come fallback)
        reservationDates.nextCheckinDateForProperty,                // {{5}} Prossimo Check-in Previsto (già formattato)
        taskId                                                      // {{6}} Task ID
    ];

    console.log(`Workflow: Preparing template 'notifica_pulizia_alloggio' for ${cleaningContactPhone} with params:`, JSON.stringify(templateParamsForCleaning));

    const waSent = await sendWhatsAppMessageViaProxy(
        cleaningContactPhone,
        "notifica_pulizia_alloggio",    // Nome del template
        templateParamsForCleaning,      // Parametri
        { taskId, clientId, hostId, propertyId } // Contesto
    );
    // --- FINE MODIFICHE PER TEMPLATE ---

    if (waSent) {
        await updateTaskStatus(taskId, "provider_notified");
    } else {
        await updateTaskStatus(taskId, "failed_provider_notification", { failureReason: "Impossibile inviare notifica WhatsApp (template pulizia) all'addetto pulizie." });
    }
    console.log(`Workflow: 'initiateCleaning' for ${propertyId} completed. Task status: ${waSent ? 'provider_notified' : 'failed_provider_notification'}.`);
}

async function handleRequestTechnician(payload: ToolCallPayload): Promise<void> {
    const { context, toolArgs } = payload;
    const { propertyId, hostId, clientId, originalUserMessage, originalChannel } = context;
    const args = toolArgs as RequestTechnicianArgs;

    console.log(`Workflow: Handling 'requestTechnician' (${args.technicianType}) for property ${propertyId}. Issue: "${args.issueDescription}" (Client: ${clientId}, Channel: ${originalChannel})`);

    const propertyData = await getPropertyDetails(hostId, propertyId);
    if (!propertyData) {
        console.error(`Workflow: Property data ${propertyId} not found for technician request.`);
        // Potrebbe essere utile notificare il cliente che i dati della proprietà non sono trovati,
        // ma questo potrebbe già avvenire a livello di proxy/Gemini se non può costruire il prompt.
        return;
    }

    const contacts: ProviderContact[] = propertyData.contacts || [];
    const technicianContact = contacts.find(c =>
        c.type?.trim().toLowerCase() === args.technicianType.trim().toLowerCase() && c.phone
    );
    const propertyName = propertyData.name || "Proprietà Sconosciuta";

    const taskBasePayload = {
        propertyId, hostId, clientId, originalChannel,
        taskType: `maintenance_${args.technicianType.toLowerCase().replace(/\s+/g, '_')}`,
        details: `Richiesta ${args.technicianType} per '${propertyName}'. Problema: "${args.issueDescription}". Msg Utente: "${originalUserMessage}"`,
    };

    if (!technicianContact || !technicianContact.phone) {
        console.warn(`Workflow: Contact for ${args.technicianType} not found/valid for property ${propertyId}.`);
        const failureReason = `Contatto per ${args.technicianType} non configurato o numero di telefono (E.164) non valido.`;
        const tempTaskId = (await saveTask({
            ...taskBasePayload,
            status: "failed_configuration",
            failureReason: failureReason,
            providerContactInfo: { type: args.technicianType, name: technicianContact?.name }
        })) || `failed-config-${Date.now()}`; // Fallback ID se saveTask dovesse dare null

        const clientInfo = await getClientDetails(clientId);
        const clientNotification = `Mi dispiace, al momento non è stato possibile trovare un contatto valido per ${args.technicianType} per il problema "${args.issueDescription}". L'host è stato informato. TaskID: ${tempTaskId}`;
        if (originalChannel === "whatsapp" && clientInfo?.whatsappPhoneNumber) {
            await sendWhatsAppMessageViaProxy(
                clientInfo.whatsappPhoneNumber,
                clientNotification, // Testo del messaggio
                { taskId: tempTaskId, clientId, hostId, propertyId } // Contesto
            );
        } else if (originalChannel === "app") {
            try {
                await firestore.collection(CHAT_LOG_COLLECTION).add({
                    userId: clientId, hostId, propertyId, channel: "system", aiResponse: clientNotification,
                    timestamp: FieldValue.serverTimestamp(), isSystemUpdate: true, relatedTaskId: tempTaskId,
                    userMessage: null, toolCallPublished: null, promptSent: null, wasBlocked: false, blockReason: null, processingError: null
                });
                console.log(`Workflow: System message for config failure (technician) sent to app user ${clientId}.`);
            } catch (logError) { console.error(`Workflow: Error saving system update to chat log for user ${clientId}:`, logError); }
        }
        // TODO: Notificare anche l'host di questa `failed_configuration`.
        return;
    }

    const taskId = await saveTask({
        ...taskBasePayload,
        status: "requested_by_client",
        providerContactInfo: technicianContact
    });

    if (!taskId) {
        console.error("Workflow: Failed to create task for technician request for property", propertyId);
        // TODO: Notificare cliente/host se il salvataggio del task fallisce.
        return;
    }

    // --- INIZIO MODIFICHE PER TEMPLATE ---
    const templateParamsForTechnician = [
        technicianContact.name || args.technicianType, // {{1}} Nome Tecnico
        propertyName,                                  // {{2}} Nome Alloggio
        args.issueDescription,                         // {{3}} Descrizione Problema Cliente
        taskId                                         // {{4}} Task ID
    ];

    console.log(`Workflow: Preparing template 'richiesta_intervento_generico' for ${technicianContact.phone} with params:`, JSON.stringify(templateParamsForTechnician));

    const waSent = await sendWhatsAppMessageViaProxy(
        technicianContact.phone,
        "richiesta_intervento_generico", // Nome del template
        templateParamsForTechnician,     // Parametri
        { taskId, clientId, hostId, propertyId } // Contesto
    );
    // --- FINE MODIFICHE PER TEMPLATE ---

    if (waSent) {
        await updateTaskStatus(taskId, "provider_notified");
    } else {
        await updateTaskStatus(taskId, "failed_provider_notification", { failureReason: `Impossibile inviare notifica WhatsApp (template tecnico) a ${args.technicianType}.` });
        // TODO: Notificare host e cliente originale del fallimento invio.
    }
    console.log(`Workflow: 'requestTechnician' (${args.technicianType}) for ${propertyId} completed. Task status: ${waSent ? 'provider_notified' : 'failed_provider_notification'}.`);
}

// --- Endpoint Principale per Ricevere Azioni da Pub/Sub ---
app.post('/receive-action', async (req: Request, res: Response) => {
    console.log('Workflow: Received new message via Pub/Sub push.');

    if (!req.body || !req.body.message || !req.body.message.data) {
        console.error('Workflow: Invalid Pub/Sub message format:', JSON.stringify(req.body, null, 2));
        res.status(400).send('Bad Request: Invalid Pub/Sub message format.');
        return;
    }

    let actionPayload: any;
    try {
        const pubsubMessage = req.body.message;
        const messageDataString = Buffer.from(pubsubMessage.data, 'base64').toString('utf-8');
        actionPayload = JSON.parse(messageDataString);

        console.log('Workflow: Decoded Action Payload:', JSON.stringify(actionPayload, null, 2));

        if (actionPayload.toolName && actionPayload.context) {
            const toolCall = actionPayload as ToolCallPayload;
            console.log(`Workflow: Processing toolCall '${toolCall.toolName}' for client '${toolCall.context.clientId}' from channel '${toolCall.context.originalChannel}'`);
            switch (toolCall.toolName) {
               case 'initiateCleaning':
                   await handleInitiateCleaning(toolCall);
                   break;
               case 'requestTechnician':
                   await handleRequestTechnician(toolCall);
                   break;
               default:
                   console.warn(`Workflow: Unrecognized toolName received: ${toolCall.toolName}`);
            }
        } else if (actionPayload.source === "provider_response") {
            console.log(`Workflow: Received provider_response to process.`);
            await handleProviderResponse(actionPayload as ProviderResponsePayload);
        }
        else {
            console.warn('Workflow: Unrecognized action payload structure:', actionPayload);
        }
        res.status(204).send(); // Conferma ricezione a Pub/Sub
        return;

    } catch (error: any) {
        console.error('Workflow: Error processing Pub/Sub message:', error.message, error.stack);
        if (error instanceof SyntaxError) {
            res.status(400).send('Bad Request: Malformed JSON payload in Pub/Sub message.');
        } else {
            res.status(500).send('Internal Server Error processing message.');
        }
        return; // Assicura che la risposta sia inviata solo una volta
    }
});

// --- Endpoint di Health Check ---
app.get('/_health', (req: Request, res: Response) => {
  res.status(200).send('OK');
});

// --- Avvio Server Express ---
if (process.env.NODE_ENV !== 'test') { // Non avviare il server durante i test
    app.listen(PORT, () => {
        console.log(`workflow-service listening on port ${PORT}`);
        console.log(`Ready to receive actions via Pub/Sub push at /receive-action`);
        if (!GEMINI_PROXY_SERVICE_URL) {
            console.warn("Workflow WARNING: GEMINI_PROXY_SERVICE_URL is not set. Sending WA will fail.");
        }
         if (!WORKFLOW_TO_GEMINI_PROXY_API_KEY) {
            console.warn("Workflow WARNING: WORKFLOW_TO_GEMINI_PROXY_API_KEY is not set. Calls to Proxy for WA will fail.");
        }
    });
}

process.on('uncaughtException', (err, origin) => { console.error(`[WORKFLOW] UNHANDLED EXCEPTION! Origin: ${origin}`, err); });
process.on('unhandledRejection', (reason, promise) => { console.error('[WORKFLOW] UNHANDLED REJECTION!', reason); });

export { app }; // Per i test