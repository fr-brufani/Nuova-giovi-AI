"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.app = void 0;
// gemini-proxy-service/src/server.ts
const express_1 = __importDefault(require("express"));
const cors_1 = __importDefault(require("cors"));
const admin = __importStar(require("firebase-admin"));
const generative_ai_1 = require("@google/generative-ai");
const secret_manager_1 = require("@google-cloud/secret-manager");
const pubsub_1 = require("@google-cloud/pubsub");
const axios_1 = __importDefault(require("axios"));
const mail_1 = __importDefault(require("@sendgrid/mail"));
const multer_1 = __importDefault(require("multer"));
// --- NUOVE IMPORTAZIONI ---
const googleapis_1 = require("googleapis"); // Auth.OAuth2Client è in google.auth.OAuth2
const crypto_1 = __importDefault(require("crypto"));
// --- Inizializzazioni ---
admin.initializeApp();
const firestore = admin.firestore();
const FieldValue = admin.firestore.FieldValue;
const secretManager = new secret_manager_1.SecretManagerServiceClient();
const pubsub = new pubsub_1.PubSub();
const app = (0, express_1.default)();
exports.app = app;
const upload = (0, multer_1.default)();
// --- Costanti e Configurazioni ---
const PORT = process.env.PORT || 8080;
const SENDGRID_SECRET_NAME_IN_MANAGER = 'sendgrid-api-key'; // Nome canonico del segreto in Secret Manager
const SYSTEM_EMAIL_FROM = process.env.SYSTEM_EMAIL_FROM || `"Giovi Concierge" <concierge@giovi.ai>`;
let sendgridApiKeyLoaded = false;
const GEMINI_SECRET_ID = 'gemini-api-key';
const WHATSAPP_TOKEN_SECRET_ID = 'whatsapp-system-token-definitivo';
const WHATSAPP_VERIFY_TOKEN_SECRET_ID = 'whatsapp-verify-token';
const WHATSAPP_API_VERSION = 'v20.0';
const YOUR_PHONE_NUMBER_ID = process.env.YOUR_PHONE_NUMBER_ID || '983247740626705'; // Fallback, da impostare via env
const CHAT_LOG_COLLECTION = 'gioviAiChatDataset';
const PROPERTY_TASKS_COLLECTION = 'propertyTasks';
const CONCIERGE_ACTIONS_TOPIC_NAME = 'concierge-actions-topic';
const WORKFLOW_SERVICE_API_KEY_SECRET_ID = 'workflow-service-api-key';
let EXPECTED_WORKFLOW_SYSTEM_KEY = null;
// --- INIZIO BLOCCO NUOVE COSTANTI E VARIABILI GLOBALI (Modifica 2) ---
const GOOGLE_OAUTH_CLIENT_ID_SECRET_ID = 'google-oauth-client-id';
const GOOGLE_OAUTH_CLIENT_SECRET_SECRET_ID = 'google-oauth-client-secret'; // Assicurati che questo sia il NOME ESATTO del tuo segreto in Secret Manager
const TOKEN_ENCRYPTION_KEY_SECRET_ID = 'host-token-encryption-key'; // Segreto che DEVI creare con una chiave di 32 byte
const HOST_EMAIL_INTEGRATIONS_COLLECTION = 'hostEmailIntegrations';
const GMAIL_NOTIFICATIONS_PUB_SUB_TOPIC_NAME = process.env.GMAIL_NOTIFICATIONS_PUB_SUB_TOPIC_NAME || 'gmail-notifications-giovi-ai';
const GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly', // Leggere email, metadati, history
    'https://www.googleapis.com/auth/gmail.send', // Inviare email per conto dell'utente
    'https://www.googleapis.com/auth/gmail.modify', // Marcare email come lette, spostare, etc. (opzionale ma utile)
];
let GOOGLE_OAUTH_CLIENT_ID = null;
let GOOGLE_OAUTH_CLIENT_SECRET = null;
let TOKEN_ENCRYPTION_KEY = null; // Sarà un Buffer di 32 byte
const GMAIL_BOOKING_CHAT_SENDER_DOMAIN = '@mchat.booking.com';
// Path per il redirect URI. Assicurati che l'URI completo sia configurato in Google Cloud Console.
// Esempio: https://<your-cloud-run-url>/oauth2callback/google
const OAUTH2_REDIRECT_URI_PATH = '/oauth2callback/google';
const getBaseUrl = (req) => {
    // Per Cloud Run, è ALTAMENTE RACCOMANDATO impostare una variabile d'ambiente BASE_URL
    // con l'URL pubblico del servizio Cloud Run (es. https://gemini-proxy-service-xxxxx.run.app).
    if (process.env.BASE_URL) {
        return process.env.BASE_URL;
    }
    // Per sviluppo locale con request object
    if (req && !process.env.K_SERVICE) {
        return `${req.protocol}://${req.get('host')}`;
    }
    // Fallback per Cloud Run - forza HTTPS per domini .run.app
    if (process.env.K_SERVICE) {
        console.warn("Proxy WARN: BASE_URL environment variable not set for Cloud Run. Using generated URL for OAuth redirect.");
        // Per Cloud Run, l'URL è tipicamente https://SERVICE-HASH-REGION.a.run.app
        // Ma se non abbiamo l'hash, proviamo con il formato tipico
        if (req && req.get('host')?.includes('.run.app')) {
            // Se abbiamo una richiesta da Cloud Run, usiamo l'host ma forziamo HTTPS
            return `https://${req.get('host')}`;
        }
        // Placeholder che evidenzia il problema
        console.error("Proxy CRITICAL: Cannot reliably construct Cloud Run URL. Please set BASE_URL environment variable.");
        return `https://your-service-name.run.app`;
    }
    // Fallback per sviluppo locale
    const port = process.env.PORT || 8080;
    return `http://localhost:${port}`;
};
// --- FINE BLOCCO NUOVE COSTANTI E VARIABILI GLOBALI (Modifica 2) ---
if (YOUR_PHONE_NUMBER_ID === '656411320878547' && !process.env.YOUR_PHONE_NUMBER_ID) {
    console.warn("Proxy WARN: YOUR_PHONE_NUMBER_ID is using a hardcoded fallback. Set via environment variable for production.");
}
// --- Middleware ---
app.use((0, cors_1.default)({ origin: true }));
app.use(express_1.default.json());
app.use(express_1.default.urlencoded({ extended: true })); // <--- AGGIUNGI QUESTA RIGA
const checkAuth = async (req, res, next) => {
    const authorization = req.headers.authorization;
    if (!authorization || !authorization.startsWith('Bearer ')) {
        res.status(401).send({ error: 'Unauthorized: Missing Authorization header.' });
        return;
    }
    const idToken = authorization.split('Bearer ')[1];
    if (!idToken) {
        res.status(401).send({ error: 'Unauthorized: Empty token.' });
        return;
    }
    try {
        const decodedToken = await admin.auth().verifyIdToken(idToken);
        req.user = decodedToken;
        next();
        return;
    }
    catch (error) {
        console.error('Error verifying Firebase ID token:', error);
        res.status(403).send({ error: 'Forbidden: Invalid or expired token.' });
        return;
    }
};
const checkSystemAuth = async (req, res, next) => {
    if (!EXPECTED_WORKFLOW_SYSTEM_KEY) {
        try {
            EXPECTED_WORKFLOW_SYSTEM_KEY = await getSecret(WORKFLOW_SERVICE_API_KEY_SECRET_ID);
        }
        catch (error) {
            console.error("CRITICAL: Failed to load WORKFLOW_SERVICE_API_KEY from Secret Manager.", error);
            res.status(500).send({ error: 'Internal configuration error preventing system authentication.' });
            return;
        }
    }
    const systemApiKey = req.headers['x-system-api-key'];
    if (systemApiKey && systemApiKey === EXPECTED_WORKFLOW_SYSTEM_KEY) {
        next();
        return;
    }
    else {
        console.warn('Unauthorized system access attempt. Provided key:', systemApiKey ? 'Present' : 'No key');
        res.status(403).send({ error: 'Forbidden: Invalid system API key.' });
        return;
    }
};
const secretsCache = {};
async function getSecret(secretId) {
    // Controlla la cache prima
    if (secretsCache[secretId]) {
        const cachedSecret = secretsCache[secretId];
        // Se è il segreto di SendGrid (identificato dal suo NOME REALE IN SECRET MANAGER)
        // e la chiave API è in cache MA sgMail non è ancora inizializzato con essa,
        // allora inizializza sgMail. Questo può accadere se ensureSendGridInitialized non è stato chiamato prima.
        if (secretId === SENDGRID_SECRET_NAME_IN_MANAGER && !sendgridApiKeyLoaded) {
            try {
                mail_1.default.setApiKey(cachedSecret);
                sendgridApiKeyLoaded = true;
                console.log(`Proxy: SendGrid API Key configured with sgMail using CACHED value for '${secretId}'.`);
            }
            catch (error) {
                console.error(`Proxy: ERROR configuring SendGrid with cached API Key for '${secretId}'. Email sending might fail.`, error);
                // Non rilanciare l'errore qui, altrimenti il getSecret non restituirebbe il valore dalla cache.
            }
        }
        return cachedSecret; // Restituisci sempre dalla cache se presente
    }
    let projectId = process.env.GOOGLE_CLOUD_PROJECT;
    if (!projectId) {
        try {
            projectId = await secretManager.getProjectId();
        }
        catch (e) {
            console.error("Proxy: Could not determine Project ID for Secret Manager.", e.message);
            throw new Error("Project ID for Secret Manager is not available.");
        }
    }
    if (!projectId) {
        throw new Error('Proxy: Project ID could not be determined for Secret Manager.');
    }
    const name = `projects/${projectId}/secrets/${secretId}/versions/latest`;
    try {
        const [version] = await secretManager.accessSecretVersion({ name });
        const payload = version.payload?.data?.toString();
        if (!payload) {
            throw new Error(`Secret payload is empty for ${name}`);
        }
        secretsCache[secretId] = payload;
        console.log(`Proxy: Secret for '${secretId}' successfully retrieved from Secret Manager and cached.`);
        // Se è la chiave API di SendGrid (identificata dal NOME REALE del segreto in Secret Manager)
        // e sgMail non è ancora stato inizializzato, allora inizializzalo.
        if (secretId === SENDGRID_SECRET_NAME_IN_MANAGER) {
            if (!sendgridApiKeyLoaded) { // Solo se non già caricata (es. da ENV diretta o cache precedente)
                try {
                    mail_1.default.setApiKey(payload);
                    sendgridApiKeyLoaded = true;
                    console.log("Proxy: SendGrid API Key loaded from Secret Manager and configured with sgMail.");
                }
                catch (error) {
                    console.error(`Proxy: ERROR configuring SendGrid with API Key from Secret Manager for '${secretId}'. Email sending might fail.`, error);
                }
            }
            else {
                console.log(`Proxy: Secret '${secretId}' (SendGrid API Key) retrieved from Secret Manager, but sgMail was already initialized.`);
            }
        }
        return payload;
    }
    catch (error) {
        const errorMessage = error.message || String(error);
        console.error(`Proxy: CRITICAL ERROR retrieving secret '${secretId}' from project '${projectId}':`, errorMessage, error.stack);
        if (error.code === 5) { // NOT_FOUND
            throw new Error(`Secret '${secretId}' not found in project '${projectId || 'UNKNOWN'}'. Please ensure it exists and the service account has 'Secret Manager Secret Accessor' role.`);
        }
        else if (error.code === 7) { // PERMISSION_DENIED
            throw new Error(`Permission denied for Secret '${secretId}' in project '${projectId || 'UNKNOWN'}'. Check IAM permissions for the service account.`);
        }
        else { // Altri errori
            throw new Error(`Failed to retrieve Secret '${secretId}'. Code: ${error.code || 'N/A'}, Message: ${errorMessage}`);
        }
    }
}
const getGeminiApiKey = () => getSecret(GEMINI_SECRET_ID);
const getWhatsAppToken = () => getSecret(WHATSAPP_TOKEN_SECRET_ID);
async function ensureSendGridInitialized() {
    if (sendgridApiKeyLoaded) {
        return; // Già inizializzato, nulla da fare.
    }
    // In Cloud Run, la variabile d'ambiente che hai chiamato 'SENDGRID_API_KEY_SECRET_ID'
    // è configurata come "Riferimento a un secret", quindi process.env.SENDGRID_API_KEY_SECRET_ID
    // conterrà il VALORE del segreto (es. SG.xxxx...).
    const apiKeyFromEnv = process.env.SENDGRID_API_KEY_SECRET_ID;
    if (apiKeyFromEnv && apiKeyFromEnv.startsWith('SG.')) {
        // La variabile d'ambiente contiene la chiave API effettiva. Usala.
        try {
            mail_1.default.setApiKey(apiKeyFromEnv);
            sendgridApiKeyLoaded = true;
            // Opzionale: Metti in cache il valore ottenuto da ENV, usando il nome canonico del segreto come chiave.
            // Questo permette a getSecret(SENDGRID_SECRET_NAME_IN_MANAGER) di trovarlo in cache se chiamato in seguito.
            secretsCache[SENDGRID_SECRET_NAME_IN_MANAGER] = apiKeyFromEnv;
            console.log("Proxy: SendGrid API Key configured directly from environment variable (SENDGRID_API_KEY_SECRET_ID in Cloud Run).");
            return; // Inizializzazione riuscita da ENV
        }
        catch (error) {
            console.error("Proxy: CRITICAL - Failed to initialize SendGrid with API Key from environment variable. Email sending will fail.", error);
            // Nonostante l'errore, sendgridApiKeyLoaded rimane false.
            // Consideriamo un errore qui come fatale per l'inizializzazione di SendGrid da ENV.
            return;
        }
    }
    // Se siamo qui, significa che:
    // 1. process.env.SENDGRID_API_KEY_SECRET_ID non era impostata, oppure
    // 2. process.env.SENDGRID_API_KEY_SECRET_ID non iniziava con 'SG.' (quindi non era la chiave API diretta).
    if (apiKeyFromEnv) { // Era impostata ma non era la chiave diretta
        console.log(`Proxy: Environment variable SENDGRID_API_KEY_SECRET_ID (value starts with: "${apiKeyFromEnv.substring(0, 10)}...") does not appear to be a direct API key. Will attempt to fetch '${SENDGRID_SECRET_NAME_IN_MANAGER}' from Secret Manager.`);
    }
    else { // Non era impostata
        console.log(`Proxy: Environment variable SENDGRID_API_KEY_SECRET_ID not set or empty. Attempting to fetch '${SENDGRID_SECRET_NAME_IN_MANAGER}' from Secret Manager.`);
    }
    // Procedi a recuperare da Secret Manager usando il NOME canonico del segreto.
    try {
        // getSecret con il NOME del segreto si occuperà di chiamare sgMail.setApiKey 
        // e impostare sendgridApiKeyLoaded se ha successo e non era già caricata.
        await getSecret(SENDGRID_SECRET_NAME_IN_MANAGER);
        if (!sendgridApiKeyLoaded) { // Ricontrolla dopo aver chiamato getSecret
            console.error(`Proxy: CRITICAL - Failed to initialize SendGrid API Key via Secret Manager (attempted to fetch '${SENDGRID_SECRET_NAME_IN_MANAGER}'). Email sending will fail.`);
        }
    }
    catch (error) { // Errore dal recupero del segreto stesso tramite getSecret
        console.error(`Proxy: CRITICAL - Error during getSecret('${SENDGRID_SECRET_NAME_IN_MANAGER}') for SendGrid initialization. Email sending will fail.`, error);
    }
}
// --- INIZIO BLOCCO FUNZIONI CRITTOGRAFIA (Modifica 3) ---
const TOKEN_CRYPTO_ALGORITHM = 'aes-256-cbc';
// Per AES, la lunghezza dell'IV (Initialization Vector) è sempre 16 byte.
const TOKEN_CRYPTO_IV_LENGTH = 16;
async function ensureTokenEncryptionKey() {
    if (TOKEN_ENCRYPTION_KEY) {
        return TOKEN_ENCRYPTION_KEY;
    }
    const keyString = await getSecret(TOKEN_ENCRYPTION_KEY_SECRET_ID);
    // aes-256-cbc richiede una chiave di 32 byte (256 bit).
    if (keyString.length < 32) {
        const errorMsg = `Proxy: CRITICAL - Token encryption key from Secret Manager ('${TOKEN_ENCRYPTION_KEY_SECRET_ID}') is too short. Needs 32 bytes (UTF-8 characters), got ${keyString.length}. Please ensure the secret contains a secure random string of at least 32 UTF-8 characters.`;
        console.error(errorMsg);
        throw new Error("Token encryption key is not properly configured (too short).");
    }
    // Prendi i primi 32 byte della stringa per la chiave.
    TOKEN_ENCRYPTION_KEY = Buffer.from(keyString.substring(0, 32), 'utf-8');
    console.log("Proxy: Token encryption key loaded and configured.");
    return TOKEN_ENCRYPTION_KEY;
}
async function encryptToken(text) {
    const key = await ensureTokenEncryptionKey();
    const iv = crypto_1.default.randomBytes(TOKEN_CRYPTO_IV_LENGTH);
    const cipher = crypto_1.default.createCipheriv(TOKEN_CRYPTO_ALGORITHM, key, iv);
    let encrypted = cipher.update(text, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    // Prependi l'IV in formato esadecimale, separato da due punti.
    return iv.toString('hex') + ':' + encrypted;
}
async function decryptToken(text) {
    const key = await ensureTokenEncryptionKey();
    const textParts = text.split(':');
    // Assicurati che ci siano due parti (IV e testo cifrato).
    if (textParts.length !== 2) {
        console.error("Proxy: Invalid encrypted token format for decryption. Expected 'iv:encryptedText'.");
        throw new Error("Invalid encrypted token format.");
    }
    const iv = Buffer.from(textParts.shift(), 'hex'); // La prima parte è l'IV.
    const encryptedText = textParts.join(':'); // La seconda parte è il testo cifrato.
    const decipher = crypto_1.default.createDecipheriv(TOKEN_CRYPTO_ALGORITHM, key, iv);
    let decrypted = decipher.update(encryptedText, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    return decrypted;
}
// --- FINE BLOCCO FUNZIONI CRITTOGRAFIA (Modifica 3) ---
// Nuova funzione per recuperare la cronologia delle conversazioni
async function getConversationHistory(userId, propertyId, limit = 10) {
    try {
        const conversationsRef = firestore
            .collection('users')
            .doc(userId)
            .collection('propertyInteractions')
            .doc(propertyId)
            .collection('conversations');
        const snapshot = await conversationsRef
            .orderBy('timestamp', 'desc')
            .limit(limit)
            .get();
        const conversations = [];
        snapshot.forEach(doc => {
            const data = doc.data();
            // Include solo conversazioni con contenuto utile (non errori o blocchi)
            if (data.userMessage && data.aiResponse && !data.wasBlocked) {
                conversations.push(data);
            }
        });
        // Ritorna in ordine cronologico (dal più vecchio al più recente)
        return conversations.reverse();
    }
    catch (error) {
        console.error(`Proxy: Error retrieving conversation history for user ${userId}, property ${propertyId}:`, error.message);
        return [];
    }
}
// Nuova funzione ottimizzata per formattare la cronologia per il prompt
function formatConversationForPrompt(conversationHistory) {
    if (!conversationHistory || conversationHistory.length === 0) {
        return { formattedHistory: "", historyLength: 0, conversationsUsed: 0 };
    }
    let historyText = "\n\nCRONOLOGIA CONVERSAZIONE PRECEDENTE:\n";
    let conversationsUsed = 0;
    // Includi TUTTE le conversazioni disponibili (Gemini Flash supporta 1M+ token)
    conversationHistory.forEach((interaction, index) => {
        const userMsg = interaction.userMessage || "";
        const aiMsg = interaction.aiResponse || "";
        historyText += `\n--- Interazione ${index + 1} ---\n`;
        historyText += `OSPITE: ${userMsg}\n`;
        historyText += `GIOVI AI: ${aiMsg}\n`;
        conversationsUsed++;
    });
    historyText += "\n--- FINE CRONOLOGIA ---\n\n";
    return {
        formattedHistory: historyText,
        historyLength: historyText.length,
        conversationsUsed: conversationsUsed
    };
}
async function saveChatInteraction(logData // La fine della definizione del tipo logData
) {
    try {
        const logEntry = { ...logData, timestamp: FieldValue.serverTimestamp() };
        Object.keys(logEntry).forEach(key => {
            if (logEntry[key] === undefined) {
                delete logEntry[key];
            }
            // Questo blocco per troncare è opzionale, ma può essere utile
            if (typeof logEntry[key] === 'string' && logEntry[key].length > 1450) {
                console.warn(`Proxy: Truncating long string in logData for field '${key}' (original length: ${logEntry[key].length})`);
                logEntry[key] = logEntry[key].substring(0, 1450) + "...(truncated)";
            }
        }); // Fine del forEach
        // Nuova struttura gerarchica per le conversazioni
        if (logData.userId && logData.propertyId && logData.hostId) {
            try {
                const conversationRef = firestore
                    .collection('users')
                    .doc(logData.userId)
                    .collection('propertyInteractions')
                    .doc(logData.propertyId)
                    .collection('conversations')
                    .doc(); // Genera automaticamente un ID univoco
                await conversationRef.set(logEntry);
                console.log(`Proxy: Interaction [${logData.channel}] for ${logData.userId} saved to new structure: users/${logData.userId}/propertyInteractions/${logData.propertyId}/conversations/${conversationRef.id}`);
            }
            catch (newStructureError) {
                console.error(`Proxy: Error saving to new conversation structure:`, newStructureError.message);
                // Fallback alla struttura vecchia in caso di errore
                const docRef = await firestore.collection(CHAT_LOG_COLLECTION).add(logEntry);
                console.log(`Proxy: Fallback - Interaction saved to old structure: ${CHAT_LOG_COLLECTION}/${docRef.id}`);
            }
        }
        else {
            // Per interazioni di sistema o senza contesto completo, usa ancora la vecchia struttura
            const docRef = await firestore.collection(CHAT_LOG_COLLECTION).add(logEntry);
            console.log(`Proxy: System interaction [${logData.channel}] for ${logData.userId} (Task: ${logData.relatedTaskId || 'N/A'}) saved to ${CHAT_LOG_COLLECTION}/${docRef.id}`);
        }
    }
    catch (logError) {
        console.error(`Proxy: ERROR saving log:`, logError.message || logError);
    }
}
// const tools: Tool[] = [ // Riga dopo la tua saveChatInteraction (indicativa)
const tools = [
    {
        functionDeclarations: [
            {
                name: "initiateCleaning",
                description: "Avvia il processo di pulizia per un alloggio, solitamente dopo che un ospite ha comunicato la sua partenza o ha effettuato il check-out.",
                parameters: {
                    type: generative_ai_1.FunctionDeclarationSchemaType.OBJECT,
                    properties: {
                        clientNotes: {
                            type: generative_ai_1.FunctionDeclarationSchemaType.STRING,
                            description: "Eventuali note aggiuntive fornite dal cliente riguardo al check-out o alla pulizia."
                        }
                    },
                }
            },
            {
                name: "requestTechnician",
                description: "Contatta un tecnico (es. idraulico, elettricista) per un problema specifico segnalato dall'ospite nell'alloggio.",
                parameters: {
                    type: generative_ai_1.FunctionDeclarationSchemaType.OBJECT,
                    properties: {
                        technicianType: {
                            type: generative_ai_1.FunctionDeclarationSchemaType.STRING,
                            description: "Il tipo di tecnico richiesto (es. 'Idraulico', 'Elettricista', 'Manutenzione Generale'). Gemini dovrebbe dedurlo dal messaggio del cliente.",
                        },
                        issueDescription: {
                            type: generative_ai_1.FunctionDeclarationSchemaType.STRING,
                            description: "Una descrizione chiara e concisa del problema tecnico segnalato dall'ospite."
                        }
                    },
                    required: ["technicianType", "issueDescription"]
                }
            }
        ]
    }
];
async function sendWhatsAppMessageInternal(to, messageConfig) {
    const recipientNumber = to.startsWith('+') ? to.substring(1) : to;
    let logMessagePreview = "";
    if (messageConfig.type === "text") {
        logMessagePreview = `"${messageConfig.body.substring(0, 50)}..."`;
    }
    else if (messageConfig.type === "template") {
        const bodyComponent = messageConfig.components.find(c => c.type === 'body');
        const paramsPreview = bodyComponent?.parameters.map(p => p.text).slice(0, 2) || [];
        logMessagePreview = `template '${messageConfig.name}' with params: ${JSON.stringify(paramsPreview)}...`;
    }
    console.log(`Proxy: Sending WhatsApp message to ${recipientNumber}: ${logMessagePreview}`);
    try {
        const whatsappToken = await getWhatsAppToken();
        const url = `https://graph.facebook.com/${WHATSAPP_API_VERSION}/${YOUR_PHONE_NUMBER_ID}/messages`;
        let payload;
        if (messageConfig.type === "text") {
            payload = {
                messaging_product: "whatsapp",
                to: recipientNumber,
                type: "text",
                text: { preview_url: false, body: messageConfig.body }
            };
        }
        else if (messageConfig.type === "template") {
            payload = {
                messaging_product: "whatsapp",
                to: recipientNumber,
                type: "template",
                template: {
                    name: messageConfig.name,
                    language: { code: messageConfig.languageCode || "it" }, // Default a 'it'
                    components: messageConfig.components
                }
            };
        }
        else {
            // Questo caso non dovrebbe mai accadere con i tipi definiti
            console.error(`Proxy: Unknown messageConfig type in sendWhatsAppMessageInternal for ${recipientNumber}`);
            return null;
        }
        const response = await axios_1.default.post(url, payload, {
            headers: { 'Authorization': `Bearer ${whatsappToken}`, 'Content-Type': 'application/json' }
        });
        console.log(`Proxy: WhatsApp message (type: ${messageConfig.type}) sent to ${recipientNumber}. Meta ID: ${response.data?.messages?.[0]?.id}`);
        return response.data;
    }
    catch (error) {
        console.error(`Proxy: ERROR sending WhatsApp message (type: ${messageConfig.type}) to ${recipientNumber}:`);
        if (axios_1.default.isAxiosError(error)) {
            const axiosError = error;
            console.error('Status:', axiosError.response?.status);
            console.error('Data:', JSON.stringify(axiosError.response?.data, null, 2));
            if (messageConfig.type === "template" && axiosError.response?.data?.error?.error_data?.details) {
                console.error('Meta Template Error Details:', axiosError.response.data.error.error_data.details);
            }
        }
        else {
            console.error('Generic error:', error.message);
        }
        return null;
    }
}
// --- FINE MODIFICHE PER TEMPLATE WHATSAPP ---
async function getPropertyData(hostId, propertyId) {
    const propertyDocRef = firestore.collection('users').doc(hostId).collection('properties').doc(propertyId);
    const propertySnapshot = await propertyDocRef.get();
    if (!propertySnapshot.exists) {
        throw new Error(`Property details not found for host ${hostId}, property ${propertyId}.`);
    }
    const propertyData = propertySnapshot.data();
    if (!propertyData) {
        throw new Error(`Corrupted property data for host ${hostId}, property ${propertyId}.`);
    }
    return propertyData;
}
async function generateGeminiPrompt(propertyData, userMessage, conversationHistory) {
    let contextString = "INFORMAZIONI SULL'ALLOGGIO FORNITE DALL'HOST:\n";
    for (const [key, value] of Object.entries(propertyData)) {
        if (key !== "createdAt" && key !== "photos" && key !== "mainPhotoUrl" && value !== null && value !== "" && (!Array.isArray(value) || value.length > 0)) {
            if (Array.isArray(value) && value.length > 0) {
                contextString += `- ${key}:\n`;
                value.forEach((item) => {
                    let itemString = '';
                    if (item && typeof item === 'object') {
                        itemString = Object.entries(item).map(([k, v]) => `${k}: ${v}`).join(", ");
                    }
                    else {
                        itemString = String(item);
                    }
                    contextString += `  - ${itemString}\n`;
                });
            }
            else if (!Array.isArray(value)) {
                contextString += `- ${key}: ${value}\n`;
            }
        }
    }
    // Aggiungi la cronologia delle conversazioni se disponibile
    const historyInfo = conversationHistory && conversationHistory.length > 0
        ? formatConversationForPrompt(conversationHistory)
        : { formattedHistory: "", historyLength: 0, conversationsUsed: 0 };
    const prompt = `Sei "Giovi AI", un assistente concierge virtuale amichevole, preciso e disponibile per l'alloggio chiamato
"${propertyData.name}". Il tuo compito è:
1. Se la domanda dell'utente può essere risolta con un'azione specifica che richiede un intervento esterno (come contattare un tecnico, avviare le pulizie), utilizza il tool appropriato. Fornisci SOLO la chiamata al tool.
2. Se la domanda è informativa e l'informazione è presente nel contesto fornito, rispondi in modo completo.
3. Se l'informazione richiesta NON è presente o è incompleta nel contesto fornito: Rispondi: "Mi dispiace, non ho questa informazione specifica nei dettagli forniti dall'host." Se appropriato, puoi aggiungere: "Ti suggerisco di verificare direttamente con l'host." NON inventare dettagli.
4. Se la domanda è ambigua, chiedi gentilmente di specificare meglio.
5. IMPORTANTE: Se hai già risposto a domande simili nelle conversazioni precedenti, puoi fare riferimento a quelle risposte per mantenere coerenza.
Rispondi in modo cortese e con frasi complete.

${contextString}${historyInfo.formattedHistory}

DOMANDA OSPITE / RICHIESTA ATTUALE:
"${userMessage}"

Se devi usare un tool, fornisci SOLO la chiamata al tool. Altrimenti, fornisci la risposta testuale.`;
    // Metadati del contesto per debugging
    const contextMetadata = {
        propertyName: propertyData.name || "N/A",
        propertyDataFields: Object.keys(propertyData).length,
        conversationHistoryLength: conversationHistory?.length || 0,
        conversationsUsedInPrompt: historyInfo.conversationsUsed,
        historyTextLength: historyInfo.historyLength,
        totalPromptLength: prompt.length,
        model: "gemini-1.5-flash-latest" // Supporta 1M+ token
    };
    return { prompt, contextMetadata };
}
async function sendEmailInternal(toEmail, subject, textBody, htmlBody // htmlBody è opzionale
) {
    // Assicura che la chiave API di SendGrid sia caricata e sgMail sia inizializzato
    await ensureSendGridInitialized();
    if (!sendgridApiKeyLoaded) { // Controlla di nuovo il flag dopo il tentativo di inizializzazione
        console.error("Proxy: SendGrid API Key not available or sgMail not initialized. Cannot send email.");
        return { success: false, errorDetails: "Email service not configured (API Key missing or sgMail not init)." };
    }
    const msg = {
        to: toEmail,
        from: SYSTEM_EMAIL_FROM, // Usa la costante globale che abbiamo definito
        subject: subject,
        text: textBody,
        html: htmlBody || textBody, // Se htmlBody non è fornito, usa textBody anche per la parte HTML
    };
    try {
        // Invia l'email usando la libreria sgMail
        const response = await mail_1.default.send(msg);
        // SendGrid restituisce un array, il primo elemento è la risposta del server HTTP.
        // L'header 'x-message-id' contiene l'ID del messaggio univoco di SendGrid.
        const messageId = response[0].headers['x-message-id'];
        console.log(`Proxy: Email sent to ${toEmail}. Subject: "${subject.substring(0, 50)}...". Message ID: ${messageId}`);
        return { success: true, messageId };
    }
    catch (error) {
        console.error(`Proxy: ERROR sending email to ${toEmail}. Subject: "${subject.substring(0, 50)}...":`);
        // error.response.body spesso contiene un JSON con dettagli utili dell'errore da SendGrid
        if (error.response && error.response.body) {
            console.error("SendGrid Error Body:", JSON.stringify(error.response.body, null, 2));
            return { success: false, errorDetails: JSON.stringify(error.response.body) };
        }
        else {
            console.error("Generic Send Email Error:", error.message || error);
            return { success: false, errorDetails: error.message || "Unknown email sending error" };
        }
    }
}
// --- INIZIO BLOCCO HELPER OAUTH2 CLIENT (Modifica 5) ---
function getGoogleOAuth2ClientInstance(req) {
    if (!GOOGLE_OAUTH_CLIENT_ID || !GOOGLE_OAUTH_CLIENT_SECRET) {
        console.error("Proxy: CRITICAL - Google OAuth Client ID or Secret not loaded from secrets. Cannot create OAuth2Client instance.");
        throw new Error("OAuth2 client credentials not available. Check server startup logs.");
    }
    const redirectUri = `${getBaseUrl(req)}${OAUTH2_REDIRECT_URI_PATH}`;
    if ((redirectUri.includes('placeholder') || redirectUri.includes('localhost')) && process.env.NODE_ENV === 'production' && !process.env.BASE_URL) {
        const errMsg = "Proxy: CRITICAL - getBaseUrl() is likely misconfigured for production. OAuth redirect URI is '" + redirectUri + "'. Ensure BASE_URL environment variable is correctly set to your Cloud Run service's public URL.";
        console.error(errMsg);
        throw new Error(errMsg); // <-- QUESTA RIGA ASSICURA CHE IL PERCORSO ESCA
    }
    // Per debug, puoi decommentare:
    // console.log(`Proxy: Creating new Google OAuth2Client with redirect URI: ${redirectUri}`);
    return new googleapis_1.google.auth.OAuth2(// Questa è la riga ~628
    GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, redirectUri);
}
// --- FINE BLOCCO HELPER OAUTH2 CLIENT (Modifica 5) ---
// --- INIZIO BLOCCO ENDPOINT OAUTH2 GMAIL (Modifica 6) ---
const GMAIL_OAUTH_STATE_PREFIX = 'gmail_oauth_state_'; // Prefisso per lo state in Firestore
/**
 * @route POST /auth/google/initiate
 * @description Inizia il flusso di autorizzazione OAuth2 per Gmail.
 * Richiede l'autenticazione dell'host (tramite checkAuth).
 * L'hostId viene preso dal token Firebase.
 * Restituisce l'URL di consenso Google a cui il frontend deve reindirizzare l'utente.
 */
// Riga ~627 nel tuo file completo
app.post('/auth/google/initiate', checkAuth, async (req, res) => {
    const hostUid = req.user.uid;
    if (!hostUid) {
        res.status(403).send({ error: 'Forbidden: Host UID not found in token.' });
        return; // Esplicito return
    }
    try {
        const oauth2Client = getGoogleOAuth2ClientInstance(req); // Passa req per getBaseUrl
        const uniqueState = GMAIL_OAUTH_STATE_PREFIX + crypto_1.default.randomBytes(16).toString('hex');
        const stateDocRef = firestore.collection('oauthStates').doc(uniqueState);
        await stateDocRef.set({
            hostUid: hostUid,
            createdAt: FieldValue.serverTimestamp(),
            expiresAt: admin.firestore.Timestamp.fromMillis(Date.now() + 15 * 60 * 1000)
        });
        console.log(`Proxy: OAuth state ${uniqueState} saved for host ${hostUid}.`);
        const authorizeUrl = oauth2Client.generateAuthUrl({
            access_type: 'offline',
            scope: GMAIL_SCOPES,
            prompt: 'consent',
            state: uniqueState,
        });
        console.log(`Proxy: Generated Google Auth URL for host ${hostUid} (state: ${uniqueState}). URL starts with: ${authorizeUrl.substring(0, 150)}...`);
        res.status(200).send({ authorizeUrl });
        return; // Esplicito return dopo aver inviato la risposta
    }
    catch (error) {
        console.error(`Proxy: Error initiating Google OAuth for host ${hostUid}:`, error.message, error.stack);
        res.status(500).send({ error: 'Failed to initiate Google OAuth flow.', details: error.message });
        return; // Esplicito return dopo aver inviato la risposta d'errore
    }
});
/**
 * @route GET /oauth2callback/google
 * @description Callback da Google dopo che l'utente ha concesso/negato l'autorizzazione.
 * Scambia il codice di autorizzazione per i token, li salva (crittografati),
 * e imposta la sottoscrizione watch() alla Gmail API.
 */
app.get(OAUTH2_REDIRECT_URI_PATH, async (req, res) => {
    const code = req.query.code;
    const stateFromGoogle = req.query.state;
    const errorFromGoogle = req.query.error;
    const frontendSettingsUrl = process.env.FRONTEND_SETTINGS_URL || `${getBaseUrl(req)}/app-settings-page`; // URL del frontend a cui reindirizzare
    if (errorFromGoogle) {
        console.warn(`Proxy: Google OAuth callback error: ${errorFromGoogle}`);
        return res.redirect(`${frontendSettingsUrl}?gmail_auth_status=error&details=${encodeURIComponent("Accesso negato o errore da Google: " + errorFromGoogle)}`);
    }
    if (!code || !stateFromGoogle) {
        console.warn('Proxy: Google OAuth callback missing authorization code or state.');
        return res.redirect(`${frontendSettingsUrl}?gmail_auth_status=error&details=${encodeURIComponent("Parametri mancanti dal callback di Google.")}`);
    }
    console.log(`Proxy: Google OAuth callback received. Code starts with: ${code.substring(0, 20)}..., State: ${stateFromGoogle}`);
    // Verifica lo state
    const stateDocRef = firestore.collection('oauthStates').doc(stateFromGoogle);
    let hostUid;
    try {
        const stateDoc = await stateDocRef.get();
        if (!stateDoc.exists || !stateDoc.data()?.hostUid || !stateDoc.data()?.expiresAt || stateDoc.data().expiresAt.toMillis() < Date.now()) {
            console.error(`Proxy: Invalid or expired OAuth state received: ${stateFromGoogle}. Doc exists: ${stateDoc.exists}`);
            if (stateDoc.exists)
                await stateDocRef.delete(); // Pulisci lo state usato o scaduto
            return res.redirect(`${frontendSettingsUrl}?gmail_auth_status=error&details=${encodeURIComponent("Stato di autorizzazione non valido o scaduto. Riprova.")}`);
        }
        hostUid = stateDoc.data().hostUid;
        await stateDocRef.delete(); // State valido e usato, cancellalo
        console.log(`Proxy: OAuth state ${stateFromGoogle} validated for host ${hostUid}.`);
    }
    catch (stateError) {
        console.error(`Proxy: Error validating OAuth state ${stateFromGoogle}:`, stateError);
        return res.redirect(`${frontendSettingsUrl}?gmail_auth_status=error&details=${encodeURIComponent("Errore interno nella validazione dello stato.")}`);
    }
    try {
        const oauth2Client = getGoogleOAuth2ClientInstance(req); // Passa req per getBaseUrl
        const { tokens } = await oauth2Client.getToken(code);
        oauth2Client.setCredentials(tokens);
        console.log(`Proxy: Tokens received for host ${hostUid}. Has refresh_token: ${!!tokens.refresh_token}, Access token expires: ${tokens.expiry_date ? new Date(tokens.expiry_date).toISOString() : 'N/A'}`);
        if (!tokens.access_token || !tokens.refresh_token) {
            console.error(`Proxy: CRITICAL - Missing access_token or refresh_token for host ${hostUid}. This can happen if 'offline' access wasn't granted or if 'prompt: consent' wasn't used and it's not the first authorization.`);
            return res.redirect(`${frontendSettingsUrl}?gmail_auth_status=error&details=${encodeURIComponent("Token di accesso o di aggiornamento mancanti da Google. Assicurati di concedere l'accesso offline e riprova. Potrebbe essere necessario revocare l'accesso dalle impostazioni del tuo account Google.")}`);
        }
        const gmail = googleapis_1.google.gmail({ version: 'v1', auth: oauth2Client });
        const profile = await gmail.users.getProfile({ userId: 'me' });
        const emailAddress = profile.data.emailAddress;
        if (!emailAddress) {
            console.error(`Proxy: Could not retrieve email address for host ${hostUid} after OAuth.`);
            return res.redirect(`${frontendSettingsUrl}?gmail_auth_status=error&details=${encodeURIComponent("Impossibile recuperare l'indirizzo email da Google.")}`);
        }
        console.log(`Proxy: Host ${hostUid} authorized Gmail account: ${emailAddress}`);
        const encryptedAccessToken = await encryptToken(tokens.access_token);
        const encryptedRefreshToken = await encryptToken(tokens.refresh_token);
        const hostIntegrationRef = firestore.collection(HOST_EMAIL_INTEGRATIONS_COLLECTION).doc(emailAddress); // Usa l'email come ID per unicità e facile lookup
        // Prima di salvare, verifica se esiste già un'integrazione per questa email ma per un host DIVERSO.
        // Questo scenario dovrebbe essere gestito in base alle tue policy (es. permettere solo un host per email).
        const existingDoc = await hostIntegrationRef.get();
        if (existingDoc.exists && existingDoc.data()?.hostId !== hostUid) {
            console.warn(`Proxy: Gmail account ${emailAddress} is already linked to a different host (${existingDoc.data()?.hostId}). Denying linkage for host ${hostUid}.`);
            return res.redirect(`${frontendSettingsUrl}?gmail_auth_status=error&details=${encodeURIComponent(`L'account Gmail ${emailAddress} è già collegato a un altro host. Contatta il supporto se ritieni sia un errore.`)}`);
        }
        // Controlla se questo hostUid ha già un'altra email collegata. Se sì, rimuovi la vecchia prima di aggiungere la nuova.
        const existingIntegrationsForHostQuery = firestore.collection(HOST_EMAIL_INTEGRATIONS_COLLECTION).where('hostId', '==', hostUid);
        const existingIntegrationsForHostSnapshot = await existingIntegrationsForHostQuery.get();
        for (const doc of existingIntegrationsForHostSnapshot.docs) {
            if (doc.id !== emailAddress) { // Se è un'email diversa da quella che stiamo aggiungendo
                console.log(`Proxy: Host ${hostUid} had a previous Gmail integration with ${doc.id}. Removing old one...`);
                // TODO: Idealmente, chiamare anche users.stop() per la vecchia integrazione se era attiva
                await doc.ref.delete();
            }
        }
        const integrationData = {
            hostId: hostUid,
            emailAddress: emailAddress, // Duplicato per query, anche se l'ID doc è l'email
            provider: 'google',
            encryptedAccessToken: encryptedAccessToken,
            encryptedRefreshToken: encryptedRefreshToken,
            tokenExpiryDate: tokens.expiry_date ? admin.firestore.Timestamp.fromMillis(tokens.expiry_date) : null,
            scopes: tokens.scope,
            status: 'active', // Inizialmente attivo
            lastHistoryIdProcessed: null,
            watchSubscription: null, // Rinominiamo da bookingComWatchSubscriptionId
            createdAt: FieldValue.serverTimestamp(),
            updatedAt: FieldValue.serverTimestamp(),
        };
        // Rimuovi i campi null/undefined dal data object prima di salvare, tranne quelli che devono essere null (es. lastHistoryIdProcessed)
        Object.keys(integrationData).forEach(key => {
            if (integrationData[key] === undefined && key !== 'lastHistoryIdProcessed' && key !== 'watchSubscription' && key !== 'tokenExpiryDate') {
                delete integrationData[key];
            }
        });
        await hostIntegrationRef.set(integrationData, { merge: true });
        console.log(`Proxy: Tokens for host ${hostUid} (email: ${emailAddress}) saved to Firestore.`);
        // Imposta il watch sulla casella di posta dell'utente (la funzione la implementeremo dopo)
        try {
            await setupGmailWatch(emailAddress, oauth2Client); // Passiamo l'emailAddress (che è l'ID del doc)
        }
        catch (watchError) {
            console.error(`Proxy: Failed to setup Gmail watch for ${emailAddress} during initial OAuth callback. Error: ${watchError.message}. Integration saved, but watch needs retry.`);
            // Nonostante l'errore nel watch, l'integrazione è salvata. L'utente potrebbe dover riprovare a connettersi o un processo batch potrebbe tentare di riattivare il watch.
            // Aggiorna lo stato in Firestore per riflettere il problema con il watch.
            await hostIntegrationRef.update({ status: 'error_watch_setup', watchError: watchError.message, updatedAt: FieldValue.serverTimestamp() });
            return res.redirect(`${frontendSettingsUrl}?gmail_auth_status=error&details=${encodeURIComponent("Collegamento Gmail riuscito, ma si è verificato un problema nell'attivare il monitoraggio delle email. Riprova o contatta il supporto.")}`);
        }
        console.log(`Proxy: Gmail integration for ${emailAddress} (host ${hostUid}) successfully completed and watch initiated.`);
        return res.redirect(`${frontendSettingsUrl}?gmail_auth_status=success`);
    }
    catch (error) {
        console.error(`Proxy: Error in Google OAuth callback processing for state ${stateFromGoogle} (HostUID was ${hostUid || 'UNKNOWN'}):`, error.response ? JSON.stringify(error.response.data) : error.message, error.stack);
        return res.redirect(`${frontendSettingsUrl}?gmail_auth_status=error&details=${encodeURIComponent(error.message || "Errore sconosciuto durante il processo di autorizzazione Gmail.")}`);
    }
});
// --- FINE BLOCCO ENDPOINT OAUTH2 GMAIL (Modifica 6) ---
// --- INIZIO BLOCCO GMAIL WATCH E REFRESH TOKEN (Modifica 7) ---
/**
 * Ottiene un client OAuth2 valido per un dato host, gestendo il refresh del token se necessario.
 * @param emailAddress L'indirizzo email dell'host (usato come ID documento in Firestore).
 * @returns Un Auth.OAuth2Client configurato e pronto all'uso, o null se fallisce.
 */
async function getAuthenticatedGmailClient(emailAddress) {
    const integrationRef = firestore.collection(HOST_EMAIL_INTEGRATIONS_COLLECTION).doc(emailAddress);
    const doc = await integrationRef.get();
    if (!doc.exists) {
        console.error(`Proxy: No Gmail integration found for email ${emailAddress} to get authenticated client.`);
        return null;
    }
    const data = doc.data();
    if (!data || data.status !== 'active' || !data.encryptedRefreshToken) {
        console.warn(`Proxy: Gmail integration for ${emailAddress} is not active or missing refresh token. Status: ${data?.status}`);
        return null;
    }
    const oauth2Client = getGoogleOAuth2ClientInstance(); // Non passa req, userà il base URL di fallback o da env
    try {
        const refreshToken = await decryptToken(data.encryptedRefreshToken);
        oauth2Client.setCredentials({ refresh_token: refreshToken });
        // Tenta di ottenere un nuovo access token per verificare il refresh token e aggiornarlo se necessario
        // Google API client gestisce il refresh automaticamente se l'access token è scaduto
        // quando si effettua una chiamata API, ma possiamo forzarlo per verifica.
        const { token: newAccessToken, res } = await oauth2Client.getAccessToken(); // Forza il refresh se necessario
        if (!newAccessToken) {
            console.error(`Proxy: Failed to refresh access token for ${emailAddress}. The refresh token might be revoked.`);
            await integrationRef.update({ status: 'error_token_refresh', updatedAt: FieldValue.serverTimestamp() });
            return null;
        }
        // Se l'access token è stato effettivamente rinfrescato (o se è la prima volta dopo il setCredentials),
        // salviamo il nuovo access token (se diverso) e la sua scadenza.
        // La libreria googleapis potrebbe non restituire sempre un nuovo refresh_token.
        // Il refresh_token originale dovrebbe rimanere valido.
        if (newAccessToken !== (await decryptToken(data.encryptedAccessToken))) { // Confronta con il vecchio access token
            console.log(`Proxy: Access token for ${emailAddress} was refreshed. Updating in Firestore.`);
            const newEncryptedAccessToken = await encryptToken(newAccessToken);
            const updateData = {
                encryptedAccessToken: newEncryptedAccessToken,
                updatedAt: FieldValue.serverTimestamp()
            };
            // La proprietà 'expiry_date' potrebbe essere nel corpo della risposta 'res' o in 'oauth2Client.credentials'
            const expiryDate = oauth2Client.credentials.expiry_date || res?.data?.expiry_date;
            if (expiryDate) {
                updateData.tokenExpiryDate = admin.firestore.Timestamp.fromMillis(expiryDate);
            }
            await integrationRef.update(updateData);
        }
        return oauth2Client;
    }
    catch (error) {
        console.error(`Proxy: Error getting authenticated Gmail client for ${emailAddress}:`, error.message);
        if (error.message?.toLowerCase().includes('token has been expired or revoked')) {
            await integrationRef.update({ status: 'revoked', updatedAt: FieldValue.serverTimestamp() });
            console.warn(`Proxy: Refresh token for ${emailAddress} seems revoked. Marked integration as 'revoked'.`);
        }
        else {
            await integrationRef.update({ status: 'error_token_refresh', updatedAt: FieldValue.serverTimestamp() });
        }
        return null;
    }
}
// server.ts
// ... (altre funzioni come getAuthenticatedGmailClient) ...
/**
 * Imposta o rinnova il "watch" sulla casella di posta Gmail di un utente.
 * @param emailAddress L'indirizzo email dell'utente (ID del documento in Firestore).
 * @param oauth2Client Un client OAuth2 autenticato (opzionale, se non fornito verrà recuperato).
 */
async function setupGmailWatch(emailAddress, oauth2Client) {
    console.log(`Proxy: Attempting to set up Gmail watch for ${emailAddress}...`);
    const client = oauth2Client || await getAuthenticatedGmailClient(emailAddress);
    if (!client) {
        console.error(`Proxy: Cannot setup Gmail watch for ${emailAddress}, failed to get authenticated client.`);
        throw new Error(`Failed to get authenticated client for ${emailAddress} to setup watch.`);
    }
    const gmail = googleapis_1.google.gmail({ version: 'v1', auth: client });
    const integrationRef = firestore.collection(HOST_EMAIL_INTEGRATIONS_COLLECTION).doc(emailAddress);
    try {
        const currentIntegrationDoc = await integrationRef.get();
        const currentIntegrationData = currentIntegrationDoc.data();
        if (currentIntegrationData?.watchSubscription?.subscriptionId && currentIntegrationData.watchSubscription.historyId) {
            console.log(`Proxy: Found existing watch subscription for ${emailAddress}. Attempting to stop it first.`);
            try {
                await gmail.users.stop({ userId: 'me' });
                console.log(`Proxy: Successfully stopped previous watch for ${emailAddress}.`);
            }
            catch (stopError) {
                if (stopError.code === 404) {
                    console.log(`Proxy: Previous watch for ${emailAddress} not found or already stopped (404), proceeding.`);
                }
                else {
                    console.warn(`Proxy: Could not stop existing watch for ${emailAddress}, but proceeding to set new one. Error:`, stopError.message);
                }
            }
        }
        // COSTRUZIONE DEL NOME DEL TOPIC PUB/SUB
        const projectIdForTopic = process.env.GOOGLE_CLOUD_PROJECT || (await secretManager.getProjectId());
        if (!projectIdForTopic) {
            const errMsg = "Proxy: CRITICAL - Could not determine Project ID for Pub/Sub topic name in setupGmailWatch. Ensure GOOGLE_CLOUD_PROJECT env var is set or service account has permissions to get project ID.";
            console.error(errMsg);
            throw new Error(errMsg); // Fallisci chiaramente qui
        }
        // GMAIL_NOTIFICATIONS_PUB_SUB_TOPIC_NAME è già definita come costante globale.
        const fullTopicName = `projects/${projectIdForTopic.toLowerCase()}/topics/${GMAIL_NOTIFICATIONS_PUB_SUB_TOPIC_NAME}`; // Assicurati che projectId sia lowercase
        console.log(`Proxy: Using Pub/Sub topic name for Gmail watch: ${fullTopicName}`); // LOGGA QUESTO
        const watchRequest = {
            userId: 'me',
            requestBody: {
                labelIds: ['INBOX'],
                topicName: fullTopicName, // Usa la variabile costruita
            },
        };
        const response = await gmail.users.watch(watchRequest);
        const { historyId, expiration } = response.data;
        if (!historyId || !expiration) {
            console.error(`Proxy: Gmail watch response for ${emailAddress} missing historyId or expiration.`, response.data);
            await integrationRef.update({ status: 'error_watch_response', watchError: 'Missing historyId/expiration', updatedAt: FieldValue.serverTimestamp() });
            throw new Error('Gmail watch response missing historyId or expiration.');
        }
        const watchSubscription = {
            subscriptionId: `custom_watch_for_${emailAddress}_${Date.now()}`,
            historyId: historyId,
            expiration: admin.firestore.Timestamp.fromMillis(Number(expiration)),
            lastTriggered: null,
        };
        await integrationRef.update({
            status: 'active',
            watchSubscription: watchSubscription,
            lastHistoryIdProcessed: historyId,
            updatedAt: FieldValue.serverTimestamp(),
            watchError: FieldValue.delete()
        });
        console.log(`Proxy: Gmail watch successfully set up for ${emailAddress}. HistoryId: ${historyId}, Expires: ${new Date(Number(expiration)).toISOString()}`);
    }
    catch (error) {
        console.error(`Proxy: CRITICAL ERROR setting up Gmail watch for ${emailAddress}:`, error.code, error.message, error.errors ? JSON.stringify(error.errors) : '');
        await integrationRef.update({
            status: 'error_watch_setup',
            watchError: error.message || 'Unknown error during watch setup.',
            watchSubscription: FieldValue.delete(),
            updatedAt: FieldValue.serverTimestamp()
        });
        throw new Error(`Failed to set up Gmail watch for ${emailAddress}: ${error.message}`);
    }
}
// --- INIZIO BLOCCO WEBHOOK NOTIFICHE GMAIL (Modifica 8) ---
/**
 * @route POST /webhook/google/gmail-notifications
 * @description Riceve notifiche push da Google Pub/Sub quando ci sono nuove email
 * per un account Gmail monitorato.
 */
app.post('/webhook/google/gmail-notifications', async (req, res) => {
    console.log('Proxy: Received push notification from Google Pub/Sub for Gmail.');
    // Verifica che il messaggio Pub/Sub sia valido
    if (!req.body || !req.body.message || !req.body.message.data) {
        console.error('Proxy: Invalid Pub/Sub message format received for Gmail notification:', JSON.stringify(req.body));
        return res.status(400).send('Bad Request: Invalid Pub/Sub message format.');
    }
    try {
        const pubsubMessage = req.body.message;
        const messageDataString = Buffer.from(pubsubMessage.data, 'base64').toString('utf-8');
        const notificationPayload = JSON.parse(messageDataString);
        console.log('Proxy: Decoded Gmail Pub/Sub notification payload:', notificationPayload);
        if (!notificationPayload.emailAddress || !notificationPayload.historyId) {
            console.error('Proxy: Gmail notification payload missing emailAddress or historyId.');
            // Invia ack a Pub/Sub per evitare reinvii, ma logga l'errore.
            return res.status(204).send(); // No Content - Ack
        }
        // Processa le nuove email in background, non bloccare la risposta a Pub/Sub
        processNewGmailHistory(notificationPayload.emailAddress, notificationPayload.historyId)
            .then(() => {
            console.log(`Proxy: Successfully processed Gmail history for ${notificationPayload.emailAddress} up to historyId ${notificationPayload.historyId}.`);
        })
            .catch(error => {
            console.error(`Proxy: Error processing Gmail history for ${notificationPayload.emailAddress} (historyId ${notificationPayload.historyId}):`, error.message);
            // Qui potresti voler implementare una logica di retry o notifica all'admin
        });
        // Rispondi immediatamente a Pub/Sub con 204 No Content per confermare la ricezione
        // e prevenire reinvii del messaggio. L'elaborazione effettiva avviene in background.
        return res.status(204).send();
    }
    catch (error) {
        console.error('Proxy: Error decoding or handling Pub/Sub message for Gmail notification:', error.message, error.stack);
        // Anche in caso di errore nel parsing, invia un ack per evitare loop di reinvii se il messaggio è malformato.
        // Se l'errore è critico e vuoi che Pub/Sub ritenti, potresti inviare un 500.
        // Per ora, preferiamo evitare reinvii su messaggi malformati.
        return res.status(204).send(); // No Content - Ack
    }
});
// --- FUNZIONE MODIFICATA ---
// Incolla questo blocco di codice per sostituire la tua funzione esistente "processNewGmailHistory".
/**
 * Processa i record di history di Gmail per trovare e gestire nuove email da Booking.com.
 * Implementa un blocco di idempotenza per messaggio per evitare risposte multiple.
 * @param emailAddress L'indirizzo email dell'host (ID del documento di integrazione).
 * @param notifiedHistoryId L'historyId ricevuto dalla notifica Pub/Sub.
 */
async function processNewGmailHistory(emailAddress, notifiedHistoryId) {
    console.log(`Proxy: Processing Gmail history for ${emailAddress}, notified historyId: ${notifiedHistoryId}.`);
    const integrationRef = firestore.collection(HOST_EMAIL_INTEGRATIONS_COLLECTION).doc(emailAddress);
    const integrationDoc = await integrationRef.get();
    if (!integrationDoc.exists || !integrationDoc.data()) {
        console.error(`Proxy: No integration data found for ${emailAddress} in processNewGmailHistory. Cannot proceed.`);
        return;
    }
    const integrationData = integrationDoc.data();
    const startHistoryId = integrationData.lastHistoryIdProcessed || integrationData.watchSubscription?.historyId;
    if (!startHistoryId) {
        console.error(`Proxy: Missing startHistoryId for ${emailAddress}. Cannot fetch history. Last processed: ${integrationData.lastHistoryIdProcessed}, Watch sub historyId: ${integrationData.watchSubscription?.historyId}`);
        await integrationRef.update({ status: 'error_missing_history_id', updatedAt: FieldValue.serverTimestamp() });
        return;
    }
    if (BigInt(notifiedHistoryId) <= BigInt(startHistoryId)) {
        console.log(`Proxy: Notified historyId ${notifiedHistoryId} is not newer than last processed ${startHistoryId} for ${emailAddress}. Skipping.`);
        // Anche se saltiamo, è bene aggiornare il timestamp per mostrare che il servizio è vivo.
        await integrationRef.update({ 'watchSubscription.lastTriggered': FieldValue.serverTimestamp(), updatedAt: FieldValue.serverTimestamp() });
        return;
    }
    const oauth2Client = await getAuthenticatedGmailClient(emailAddress);
    if (!oauth2Client) {
        console.error(`Proxy: Failed to get authenticated Gmail client for ${emailAddress} in processNewGmailHistory. Watch may need reset.`);
        return;
    }
    const gmail = googleapis_1.google.gmail({ version: 'v1', auth: oauth2Client });
    try {
        console.log(`Proxy: Fetching Gmail history for ${emailAddress} from startHistoryId: ${startHistoryId}.`);
        const historyResponse = await gmail.users.history.list({
            userId: 'me',
            startHistoryId: startHistoryId,
            historyTypes: ['messageAdded'],
        });
        const historyRecords = historyResponse.data.history;
        if (historyRecords && historyRecords.length > 0) {
            for (const record of historyRecords) {
                if (record.messagesAdded) {
                    for (const msgAdded of record.messagesAdded) {
                        if (msgAdded.message?.id && msgAdded.message.labelIds?.includes('INBOX')) {
                            const messageId = msgAdded.message.id;
                            // --- INIZIO BLOCCO IDEMPOTENZA ---
                            // Definiamo un riferimento a un "documento-semaforo" usando l'ID univoco del messaggio.
                            const processedMessageRef = integrationRef.collection('processedMessageIds').doc(messageId);
                            try {
                                // Usiamo una transazione atomica per verificare e creare il semaforo.
                                // Questo garantisce che solo una istanza del servizio possa "rivendicare" il messaggio.
                                await firestore.runTransaction(async (transaction) => {
                                    const doc = await transaction.get(processedMessageRef);
                                    if (doc.exists) {
                                        // Se il documento esiste, un altro processo ha già preso in carico questo messaggio.
                                        // Lanciamo un errore per uscire dalla transazione e segnalare che dobbiamo saltare.
                                        throw new Error('ALREADY_PROCESSED');
                                    }
                                    // Se non esiste, lo creiamo noi. Da ora, questo messaggio è "nostro".
                                    transaction.create(processedMessageRef, {
                                        processedAt: FieldValue.serverTimestamp(),
                                        historyId: notifiedHistoryId
                                    });
                                });
                                console.log(`Proxy: [${emailAddress}] Lock acquired for message ${messageId}. Proceeding.`);
                                // --- ELABORAZIONE EFFETTIVA DEL MESSAGGIO (solo se abbiamo acquisito il lock) ---
                                const msgResponse = await gmail.users.messages.get({
                                    userId: 'me',
                                    id: messageId,
                                    format: 'full',
                                });
                                const fullMessage = msgResponse.data;
                                if (!fullMessage) {
                                    console.warn(`Proxy: [${emailAddress}] Could not retrieve full message for ID ${messageId}.`);
                                    continue;
                                }
                                const parsedEmailData = parseBookingComEmail(fullMessage, emailAddress);
                                if (parsedEmailData) {
                                    console.log(`Proxy: [${emailAddress}] Parsed Booking.com email. From: ${parsedEmailData.guestChatEmail}, Subject: ${parsedEmailData.subject.substring(0, 50)}...`);
                                    const bookingContext = await getBookingContextFromNumber(parsedEmailData.bookingNumber, emailAddress, integrationData.hostId);
                                    if (bookingContext) {
                                        console.log(`Proxy: [${emailAddress}] Booking context found: Property ${bookingContext.propertyId}, Host ${bookingContext.hostId}. Proceeding with Gemini.`);
                                        // La chiamata a Gemini e l'invio della risposta avvengono qui
                                        await handleChatMessageWithGemini("email_booking", `booking:${parsedEmailData.bookingNumber}`, parsedEmailData.guestMessageBody, bookingContext.hostId, bookingContext.propertyId, undefined, // replyToClientEmail
                                        parsedEmailData.guestChatEmail, // replyToBookingChatEmail
                                        parsedEmailData.originalMessageId, parsedEmailData.subject);
                                        try {
                                            await gmail.users.messages.modify({
                                                userId: 'me',
                                                id: messageId,
                                                requestBody: { removeLabelIds: ['UNREAD'] }
                                            });
                                            console.log(`Proxy: [${emailAddress}] Marked message ${messageId} as read.`);
                                        }
                                        catch (modifyError) {
                                            console.warn(`Proxy: [${emailAddress}] Failed to mark message ${messageId} as read:`, modifyError);
                                        }
                                    }
                                    else {
                                        console.warn(`Proxy: [${emailAddress}] Could not find booking context for number ${parsedEmailData.bookingNumber}. Email not processed with AI.`);
                                    }
                                }
                                else {
                                    // Non è un'email di Booking.com - prova a parsare come email generica del cliente
                                    const parsedClientEmail = parseGenericClientEmail(fullMessage, emailAddress);
                                    if (parsedClientEmail) {
                                        console.log(`Proxy: [${emailAddress}] Parsed generic client email. From: ${parsedClientEmail.clientEmail}, Subject: ${parsedClientEmail.subject.substring(0, 50)}...`);
                                        // Cerca il cliente nel database
                                        const clientContext = await findClientByEmail(parsedClientEmail.clientEmail, integrationData.hostId);
                                        if (clientContext) {
                                            console.log(`Proxy: [${emailAddress}] Client context found via ${clientContext.matchType}: UID ${clientContext.clientUid}, Host ${clientContext.hostId}, Property ${clientContext.propertyId}. Proceeding with Gemini.`);
                                            await handleChatMessageWithGemini("email_client", clientContext.clientUid, parsedClientEmail.messageBody, clientContext.hostId, clientContext.propertyId, parsedClientEmail.clientEmail, // replyToClientEmail
                                            undefined, // replyToBookingChatEmail
                                            parsedClientEmail.originalMessageId, parsedClientEmail.subject);
                                            try {
                                                await gmail.users.messages.modify({
                                                    userId: 'me',
                                                    id: messageId,
                                                    requestBody: { removeLabelIds: ['UNREAD'] }
                                                });
                                                console.log(`Proxy: [${emailAddress}] Marked client message ${messageId} as read.`);
                                            }
                                            catch (modifyError) {
                                                console.warn(`Proxy: [${emailAddress}] Failed to mark client message ${messageId} as read:`, modifyError);
                                            }
                                        }
                                        else {
                                            console.warn(`Proxy: [${emailAddress}] Could not find client context for email ${parsedClientEmail.clientEmail}. Email from unrecognized sender - not processed.`);
                                        }
                                    }
                                    else {
                                        console.log(`Proxy: [${emailAddress}] Message ${messageId} could not be parsed as either Booking.com or generic client email. Skipping.`);
                                    }
                                }
                                // --- FINE ELABORAZIONE EFFETTIVA ---
                            }
                            catch (error) {
                                // Se l'errore è "ALREADY_PROCESSED", è il nostro segnale per saltare il messaggio.
                                if (error.message === 'ALREADY_PROCESSED') {
                                    console.log(`Proxy: [${emailAddress}] Skipping message ${messageId} as it's already being processed.`);
                                }
                                else {
                                    // Se è un altro tipo di errore, lo logghiamo come un problema.
                                    console.error(`Proxy: [${emailAddress}] Error during transaction or processing for message ${messageId}:`, error);
                                }
                                // In entrambi i casi di errore per un singolo messaggio, continuiamo con il prossimo.
                                continue;
                            }
                            // --- FINE BLOCCO IDEMPOTENZA ---
                        }
                    }
                }
            }
        }
        else {
            console.log(`Proxy: [${emailAddress}] No new message history found since ${startHistoryId}.`);
        }
        // Aggiorna lo stato solo alla fine di tutto il ciclo, usando l'historyId della notifica.
        await integrationRef.update({
            lastHistoryIdProcessed: notifiedHistoryId,
            'watchSubscription.lastTriggered': FieldValue.serverTimestamp(),
            updatedAt: FieldValue.serverTimestamp()
        });
        console.log(`Proxy: [${emailAddress}] Updated lastHistoryIdProcessed to ${notifiedHistoryId}.`);
        // --- BLOCCO ESATTO DA INSERIRE (Nuova Versione con Logging Migliorato) ---
    }
    catch (error) {
        // Estrae un messaggio di errore leggibile, indipendentemente dal tipo di errore.
        const errorMessage = error instanceof Error ? error.message : String(error);
        // Logga in modo molto dettagliato per un debug efficace.
        // Stampa un messaggio chiaro, l'intero oggetto errore (convertito in JSON per sicurezza)
        // e lo stack trace per sapere esattamente da dove proviene l'errore.
        console.error(`Proxy: CRITICAL Error processing Gmail history for ${emailAddress} (startHistoryId: ${startHistoryId}). Error message: ${errorMessage}`, {
            // Questa tecnica assicura che tutte le proprietà dell'oggetto errore vengano stampate.
            fullErrorObject: JSON.parse(JSON.stringify(error, Object.getOwnPropertyNames(error))),
            stack: error.stack || 'No stack trace available'
        });
        // Aggiorna lo stato su Firestore per mettere in pausa l'integrazione.
        await integrationRef.update({
            status: 'error_history_processing',
            watchError: `History processing failed: ${errorMessage}`, // Usa il messaggio di errore pulito.
            updatedAt: FieldValue.serverTimestamp()
        });
        // Controlla specificamente se l'errore è dovuto a un token revocato/scaduto.
        // Questo è un controllo importante per una diagnosi più rapida.
        // Usiamo 'errorMessage' che è garantito essere una stringa.
        if (error.code === 401 || errorMessage.toLowerCase().includes('unauthorized') || errorMessage.toLowerCase().includes('revoked')) {
            console.warn(`Proxy: Token for ${emailAddress} likely revoked during history processing. Marking integration as 'revoked'.`);
            // Sovrascrive lo stato con 'revoked' perché è più specifico e importante di 'error_history_processing'.
            await integrationRef.update({ status: 'revoked' });
        }
    }
}
/**
 * Estrae informazioni rilevanti da un'email della chat di Booking.com.
 * @param message L'oggetto messaggio completo da Gmail API.
 * @param hostEmail L'email dell'host a cui è stata inviata l'email di Booking.
 * @returns Un oggetto con i dati parsati, o null se non è un'email rilevante.
 */
function parseBookingComEmail(message, hostEmail) {
    if (!message.payload?.headers || !message.id)
        return null;
    const headers = message.payload.headers;
    const fromHeader = headers.find(h => h.name?.toLowerCase() === 'from')?.value || '';
    // const toHeader = headers.find(h => h.name?.toLowerCase() === 'to')?.value || ''; // <-- RIGA RIMOSSA/COMMENTATA (riga ~1187 nel tuo file)
    const subjectHeader = headers.find(h => h.name?.toLowerCase() === 'subject')?.value || '';
    const messageIdHeader = headers.find(h => h.name?.toLowerCase() === 'message-id')?.value || '';
    const senderMatch = fromHeader.match(/<([^>]+)>/);
    const guestChatEmail = senderMatch ? senderMatch[1].toLowerCase() : fromHeader.toLowerCase();
    if (!guestChatEmail.endsWith(GMAIL_BOOKING_CHAT_SENDER_DOMAIN)) {
        return null;
    }
    let guestName = fromHeader.split('<')[0].trim().replace('via Booking.com', '').trim();
    if (guestName.endsWith(","))
        guestName = guestName.slice(0, -1);
    let bodyData = '';
    if (message.payload.parts) {
        const textPart = findEmailTextPart(message.payload.parts);
        if (textPart?.body?.data) {
            bodyData = Buffer.from(textPart.body.data, 'base64').toString('utf-8');
        }
    }
    else if (message.payload.body?.data) {
        bodyData = Buffer.from(message.payload.body.data, 'base64').toString('utf-8');
    }
    if (!bodyData) {
        console.warn(`Proxy: [${hostEmail}] Could not extract text body from message ${message.id}`);
        return null;
    }
    let guestMessage = "";
    let bookingNumber = "";
    const bookingNumberRegex = /(?:Numero di conferma|Numero di prenotazione|Booking number|Confirmation number):\s*(\S+)/i;
    const bookingRefRegex = /Booking ref\.:\s*(\w+)/i;
    const guestMessageMatch = bodyData.match(/([\s\S]+)ha scritto:\s*([\s\S]*?)(?=Dati della prenotazione|Booking details|Rispondi|\n##- Scrivi la tua risposta sopra questa riga -##|© Copyright Booking.com)/i);
    if (guestMessageMatch && guestMessageMatch[2]) {
        guestMessage = guestMessageMatch[2].trim();
    }
    else {
        const fallbackMatch = bodyData.match(/([\s\S]*?)(?=Dati della prenotazione|Booking details|Rispondi|\n##- Scrivi la tua risposta sopra questa riga -##|© Copyright Booking.com)/i);
        if (fallbackMatch && fallbackMatch[1]) {
            guestMessage = fallbackMatch[1].replace(/Nuovo messaggio da un ospite\s*/i, "").trim();
        }
        else {
            console.warn(`Proxy: [${hostEmail}] Could not reliably extract guest message from body for message ${message.id}. Body starts with: ${bodyData.substring(0, 200)}`);
            guestMessage = bodyData.trim();
        }
    }
    // Estrai numero prenotazione dal corpo
    const lines = bodyData.split(/\r\n|\r|\n/);
    for (const line of lines) {
        if (bookingNumber)
            break; // Trovato, esci
        let match = line.match(bookingNumberRegex);
        if (match && match[1]) {
            bookingNumber = match[1].trim();
        }
        else {
            match = line.match(bookingRefRegex);
            if (match && match[1]) {
                bookingNumber = match[1].trim();
            }
        }
    }
    if (!bookingNumber && subjectHeader) {
        const subjectBookingMatch = subjectHeader.match(bookingNumberRegex);
        if (subjectBookingMatch && subjectBookingMatch[1]) {
            bookingNumber = subjectBookingMatch[1].trim();
        }
    }
    if (!bookingNumber && guestChatEmail) {
        const emailBookingMatch = guestChatEmail.match(/^(\d+)-/);
        if (emailBookingMatch && emailBookingMatch[1]) {
            bookingNumber = emailBookingMatch[1];
        }
    }
    if (!guestMessage.trim() || !bookingNumber) {
        console.warn(`Proxy: [${hostEmail}] Failed to parse essential data from Booking.com email ${message.id}. Guest Msg Empty: ${!guestMessage.trim()}, Booking Num Empty: ${!bookingNumber}. Subject: ${subjectHeader}`);
        return null;
    }
    return {
        guestChatEmail,
        guestName,
        guestMessageBody: guestMessage.trim(),
        bookingNumber,
        subject: subjectHeader,
        originalMessageId: messageIdHeader
    };
}
/**
 * Trova la parte di testo (text/plain) in un messaggio email multipart.
 */
function findEmailTextPart(parts) {
    for (const part of parts) {
        if (part.mimeType === 'text/plain') {
            return part;
        }
        if (part.parts) { // Ricerca ricorsiva per parti nidificate
            const nestedPart = findEmailTextPart(part.parts);
            if (nestedPart)
                return nestedPart;
        }
    }
    // Come fallback, se non c'è text/plain, prova text/html (ma richiederà stripping HTML)
    for (const part of parts) {
        if (part.mimeType === 'text/html') {
            // console.log("Proxy DEBUG: Found HTML part as fallback for email body.");
            return part; // Per ora restituiamo, la logica di parsing dovrà gestire HTML se necessario
        }
    }
    return null;
}
// --- INIZIO BLOCCO FUNZIONE INVIO RISPOSTA GMAIL BOOKING (Modifica 11) ---
/**
 * Invia un'email di risposta per conto dell'host usando la Gmail API.
 * @param gmailClient Client Gmail API autenticato.
 * @param fromHostEmail L'indirizzo email dell'host da cui inviare.
 * @param toGuestChatEmail L'indirizzo email fittizio @mchat.booking.com a cui rispondere.
 * @param originalSubject L'oggetto dell'email originale dell'ospite.
 * @param replyBody Il corpo testuale della risposta da inviare.
 * @param originalMessageId L'ID del messaggio originale dell'ospite, per threading (In-Reply-To).
 */
async function sendGmailReplyForBooking(gmailClient, fromHostEmail, toGuestChatEmail, originalSubject, replyBody, originalMessageId) {
    console.log(`Proxy: Preparing to send Gmail reply from ${fromHostEmail} to ${toGuestChatEmail}. Original Subject: "${originalSubject.substring(0, 50)}..."`);
    // Assicura che l'oggetto inizi con "Re: " a meno che non lo faccia già.
    const subject = originalSubject.toLowerCase().startsWith("re:")
        ? originalSubject
        : `Re: ${originalSubject}`;
    // Costruisci l'email in formato RFC822 (MIME message)
    // Questo è necessario per specificare correttamente gli header In-Reply-To e References.
    const emailLines = [
        `From: ${fromHostEmail}`, // Gmail imposterà il nome visualizzato se l'account lo ha configurato.
        `To: ${toGuestChatEmail}`,
        `Subject: ${subject}`,
        `In-Reply-To: ${originalMessageId}`,
        `References: ${originalMessageId}`, // Per un corretto threading
        "Content-Type: text/plain; charset=utf-8",
        // "Content-Transfer-Encoding: 7bit", // 7bit è ok per la maggior parte del testo UTF-8 semplice.
        // Per maggiore sicurezza con tutti i caratteri, 'base64' o 'quoted-printable' sono opzioni,
        // ma text/plain con UTF-8 è generalmente ben gestito.
        "", // Riga vuota obbligatoria prima del corpo
        replyBody,
    ];
    const email = emailLines.join("\r\n");
    // Codifica l'email in base64url (richiesto da Gmail API per il campo 'raw')
    const base64EncodedEmail = Buffer.from(email)
        .toString('base64')
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, ''); // Rimuovi il padding '=' alla fine, come richiesto da base64url
    try {
        const response = await gmailClient.users.messages.send({
            userId: 'me', // 'me' si riferisce all'utente autenticato (l'host)
            requestBody: {
                raw: base64EncodedEmail,
            },
        });
        console.log(`Proxy: Gmail reply successfully sent from ${fromHostEmail} to ${toGuestChatEmail}. Message ID: ${response.data.id}, Thread ID: ${response.data.threadId}. Subject: "${subject.substring(0, 50)}..."`);
    }
    catch (error) {
        console.error(`Proxy: CRITICAL - Error sending Gmail reply from ${fromHostEmail} to ${toGuestChatEmail}. Subject: "${subject.substring(0, 50)}...":`, error.code, error.message, error.errors ? JSON.stringify(error.errors) : '');
        // Rilancia l'errore in modo che handleChatMessageWithGemini possa catturarlo e loggarlo
        // nel processingErrorText dell'interazione.
        throw new Error(`Gmail API send error: ${error.message} (Code: ${error.code || 'N/A'})`);
    }
}
// --- FINE BLOCCO FUNZIONE INVIO RISPOSTA GMAIL BOOKING (Modifica 11) ---
/**
 * Invia un'email di risposta diretta a un cliente usando la Gmail API.
 * @param gmailClient Client Gmail API autenticato.
 * @param fromHostEmail L'indirizzo email dell'host da cui inviare.
 * @param toClientEmail L'indirizzo email diretto del cliente.
 * @param originalSubject L'oggetto dell'email originale del cliente.
 * @param replyBody Il corpo testuale della risposta da inviare.
 * @param originalMessageId L'ID del messaggio originale del cliente, per threading (In-Reply-To).
 */
async function sendGmailDirectReply(gmailClient, fromHostEmail, toClientEmail, originalSubject, replyBody, originalMessageId) {
    console.log(`Proxy: Preparing to send direct Gmail reply from ${fromHostEmail} to ${toClientEmail}. Original Subject: "${originalSubject.substring(0, 50)}..."`);
    // Assicura che l'oggetto inizi con "Re: " a meno che non lo faccia già.
    const subject = originalSubject.toLowerCase().startsWith("re:")
        ? originalSubject
        : `Re: ${originalSubject}`;
    // Costruisci l'email in formato RFC822 (MIME message)
    const emailLines = [
        `From: ${fromHostEmail}`,
        `To: ${toClientEmail}`,
        `Subject: ${subject}`,
        `In-Reply-To: ${originalMessageId}`,
        `References: ${originalMessageId}`,
        "Content-Type: text/plain; charset=utf-8",
        "",
        replyBody,
    ];
    const email = emailLines.join("\r\n");
    // Codifica l'email in base64url
    const base64EncodedEmail = Buffer.from(email)
        .toString('base64')
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '');
    try {
        const response = await gmailClient.users.messages.send({
            userId: 'me',
            requestBody: {
                raw: base64EncodedEmail,
            },
        });
        console.log(`Proxy: Direct Gmail reply successfully sent from ${fromHostEmail} to ${toClientEmail}. Message ID: ${response.data.id}, Thread ID: ${response.data.threadId}. Subject: "${subject.substring(0, 50)}..."`);
    }
    catch (error) {
        console.error(`Proxy: CRITICAL - Error sending direct Gmail reply from ${fromHostEmail} to ${toClientEmail}. Subject: "${subject.substring(0, 50)}...":`, error.code, error.message, error.errors ? JSON.stringify(error.errors) : '');
        throw new Error(`Gmail API send error: ${error.message} (Code: ${error.code || 'N/A'})`);
    }
}
// ... (dopo la funzione sendGmailReplyForBooking)
// --- INIZIO FUNZIONE getBookingContextFromNumber (COMPLETA E MODIFICATA) ---
/**
 * Recupera il contesto della prenotazione (propertyId, hostId)
 * basandosi sul numero di conferma/prenotazione di Booking.com.
 * QUESTA FUNZIONE DEVE ESSERE ADATTATA ALLA TUA STRUTTURA DATI ESATTA.
 * @param bookingComConfirmationNumber Il numero di conferma/prenotazione di Booking.com.
 * @param emailReceivingHost L'email dell'host che ha ricevuto la notifica Gmail.
 * @param integrationOwnerHostId L'hostId (Firebase UID) associato all'integrazione Gmail attiva.
 * @returns Un oggetto con propertyId e hostId, o null se non trovato o non autorizzato.
 */
async function getBookingContextFromNumber(bookingComConfirmationNumber, emailReceivingHost, // Utile per logging e potenziali controlli futuri
integrationOwnerHostId // L'UID Firebase dell'host che ha collegato l'account Gmail
) {
    console.log(`Proxy: [HostEmail: ${emailReceivingHost}] Attempting to find booking context for Booking.com Confirmation #: ${bookingComConfirmationNumber}. Gmail integration owner HostId: ${integrationOwnerHostId}.`);
    if (!bookingComConfirmationNumber || bookingComConfirmationNumber.trim() === "") {
        console.warn(`Proxy: [HostEmail: ${emailReceivingHost}] Booking.com confirmation number is missing or empty. Cannot find context.`);
        return null;
    }
    try {
        // Dichiarazione di reservationsRef all'interno della funzione
        const reservationsRef = firestore.collection('reservations');
        // Query per trovare la prenotazione basata sul numero di conferma di Booking.com.
        // !!! IMPORTANTE: Sostituisci 'bookingComNumeroConferma' con il nome ESATTO
        // del campo nel tuo documento 'reservations' che contiene il numero di conferma di Booking.com !!!
        const querySnapshot = await reservationsRef
            .where('numeroConfermaBooking', '==', bookingComConfirmationNumber.trim()) // Usa .trim() per sicurezza
            .limit(1)
            .get();
        if (querySnapshot.empty) {
            console.warn(`Proxy: [HostEmail: ${emailReceivingHost}] No reservation found in Firestore with Booking.com Confirmation #: ${bookingComConfirmationNumber}.`);
            // TODO: Considerare logica di fallback o notifica all'amministratore.
            return null;
        }
        const reservationDoc = querySnapshot.docs[0];
        const reservationData = reservationDoc.data();
        if (!reservationData) {
            console.error(`Proxy: [HostEmail: ${emailReceivingHost}] Reservation document ${reservationDoc.id} (for Booking.com #${bookingComConfirmationNumber}) has no data.`);
            return null;
        }
        const propertyId = reservationData.propertyId;
        const hostIdFromReservation = reservationData.hostId; // L'host a cui è effettivamente assegnata questa prenotazione
        if (!propertyId || !hostIdFromReservation) {
            console.error(`Proxy: [HostEmail: ${emailReceivingHost}] Reservation document ${reservationDoc.id} (for Booking.com #${bookingComConfirmationNumber}) is missing 'propertyId' or 'hostId' fields. PropertyId: ${propertyId}, HostId: ${hostIdFromReservation}`);
            return null;
        }
        // Controllo di sicurezza FONDAMENTALE:
        // L'host che ha collegato l'account Gmail (integrationOwnerHostId)
        // DEVE essere lo stesso host a cui è assegnata la prenotazione (hostIdFromReservation).
        if (hostIdFromReservation !== integrationOwnerHostId) {
            console.error(`Proxy: SECURITY ALERT! [HostEmail: ${emailReceivingHost}] Mismatch for Booking.com #${bookingComConfirmationNumber}. Reservation HostID ('${hostIdFromReservation}') does not match Gmail Integration Owner HostID ('${integrationOwnerHostId}'). Denying processing.`);
            // Potresti voler inviare una notifica di sicurezza all'amministratore qui.
            return null;
        }
        console.log(`Proxy: [HostEmail: ${emailReceivingHost}] Successfully found context for Booking.com #${bookingComConfirmationNumber}. PropertyID: ${propertyId}, HostID: ${hostIdFromReservation}.`);
        return { propertyId, hostId: hostIdFromReservation };
    }
    catch (error) {
        console.error(`Proxy: [HostEmail: ${emailReceivingHost}] Error querying Firestore for Booking.com Confirmation #${bookingComConfirmationNumber}:`, error.message, error.stack);
        return null;
    }
}
// --- FINE FUNZIONE getBookingContextFromNumber ---
/**
 * Estrae informazioni rilevanti da un'email generica di un cliente.
 * @param message L'oggetto messaggio completo da Gmail API.
 * @param hostEmail L'email dell'host a cui è stata inviata l'email.
 * @returns Un oggetto con i dati parsati, o null se l'email non può essere parsata.
 */
function parseGenericClientEmail(message, hostEmail) {
    if (!message.payload?.headers || !message.id)
        return null;
    const headers = message.payload.headers;
    const fromHeader = headers.find(h => h.name?.toLowerCase() === 'from')?.value || '';
    const subjectHeader = headers.find(h => h.name?.toLowerCase() === 'subject')?.value || '';
    const messageIdHeader = headers.find(h => h.name?.toLowerCase() === 'message-id')?.value || '';
    const senderMatch = fromHeader.match(/<([^>]+)>/);
    const clientEmail = senderMatch ? senderMatch[1].toLowerCase() : fromHeader.toLowerCase();
    if (!clientEmail || clientEmail === hostEmail.toLowerCase()) {
        return null; // Evita email dall'host stesso
    }
    let clientName = fromHeader.split('<')[0].trim();
    if (clientName.endsWith(","))
        clientName = clientName.slice(0, -1);
    if (!clientName)
        clientName = clientEmail.split('@')[0]; // Fallback al username dell'email
    let bodyData = '';
    if (message.payload.parts) {
        const textPart = findEmailTextPart(message.payload.parts);
        if (textPart?.body?.data) {
            bodyData = Buffer.from(textPart.body.data, 'base64').toString('utf-8');
        }
    }
    else if (message.payload.body?.data) {
        bodyData = Buffer.from(message.payload.body.data, 'base64').toString('utf-8');
    }
    if (!bodyData) {
        console.warn(`Proxy: [${hostEmail}] Could not extract text body from generic client message ${message.id}`);
        return null;
    }
    // Pulisci il messaggio da firme automatiche e contenuti di risposta
    const cleanedBody = cleanEmailBody(bodyData);
    if (!cleanedBody.trim()) {
        console.warn(`Proxy: [${hostEmail}] Email body became empty after cleaning for message ${message.id}`);
        return null;
    }
    return {
        clientEmail,
        clientName,
        messageBody: cleanedBody.trim(),
        subject: subjectHeader,
        originalMessageId: messageIdHeader
    };
}
/**
 * Pulisce il corpo dell'email da firme, contenuti di risposta e altri elementi non necessari.
 */
function cleanEmailBody(bodyData) {
    const lines = bodyData.split('\n');
    let cleanedLines = [];
    const stopPatterns = [
        /^On.*wrote:$/im, /^Il giorno.*ha scritto:$/im,
        /^> ?/m,
        /^\s*From:/im, /^\s*Sent:/im, /^\s*To:/im, /^\s*Date:/im, /^\s*Subject:/im,
        /^\s*Da:/im, /^\s*Inviato:/im, /^\s*A:/im, /^\s*Data:/im, /^\s*Oggetto:/im,
        /^\s*---*Original Message---*/im, /^\s*---*Messaggio Originale---*/im,
        /^\s*_{20,}/im,
        /^\s*Risposta inoltrata/im, /^\s*Messaggio inoltrato/im,
        /^\s*Forwarded message/im,
        /^\s*--\s*$/im, // Separatore firma comune
        /^\s*Best regards/im, /^\s*Cordiali saluti/im,
        /^\s*Sent from my/im, /^\s*Inviato da/im
    ];
    for (const line of lines) {
        if (stopPatterns.some(pattern => pattern.test(line))) {
            break; // Smetti di aggiungere linee dopo aver trovato un pattern di stop
        }
        cleanedLines.push(line);
    }
    return cleanedLines.join('\n');
}
/**
 * Cerca un cliente nel database basandosi sull'email del mittente.
 * Controlla sia nel campo 'email' (email diretta) che 'emailBooking' (email Booking.com).
 * @param senderEmail L'email del mittente da cercare.
 * @param integrationOwnerHostId L'hostId dell'integrazione Gmail attiva.
 * @returns Un oggetto con i dati del cliente trovato o null se non trovato.
 */
async function findClientByEmail(senderEmail, integrationOwnerHostId) {
    console.log(`Proxy: Searching for client with email: ${senderEmail} (integration owner: ${integrationOwnerHostId})`);
    const senderEmailLower = senderEmail.toLowerCase();
    const usersRef = firestore.collection('users');
    try {
        // Prima cerca nell'email diretta del cliente
        const directEmailQuery = await usersRef
            .where('role', '==', 'client')
            .where('email', '==', senderEmailLower)
            .limit(1)
            .get();
        if (!directEmailQuery.empty) {
            const userDoc = directEmailQuery.docs[0];
            const userData = userDoc.data();
            const assignedHostId = userData.assignedHostId;
            const assignedPropertyId = userData.assignedPropertyId;
            // Verifica che il cliente sia assegnato all'host che ha l'integrazione Gmail
            if (assignedHostId === integrationOwnerHostId) {
                console.log(`Proxy: Client found by direct email: ${senderEmail} → UID: ${userDoc.id}, Host: ${assignedHostId}, Property: ${assignedPropertyId}`);
                return {
                    clientUid: userDoc.id,
                    hostId: assignedHostId,
                    propertyId: assignedPropertyId,
                    clientData: userData,
                    matchType: 'email'
                };
            }
            else {
                console.warn(`Proxy: Client found by direct email ${senderEmail} but assigned to different host (${assignedHostId}) than integration owner (${integrationOwnerHostId}). Ignoring.`);
            }
        }
        // Se non trovato nell'email diretta, cerca nell'email di Booking
        const bookingEmailQuery = await usersRef
            .where('role', '==', 'client')
            .where('emailBooking', '==', senderEmailLower)
            .limit(1)
            .get();
        if (!bookingEmailQuery.empty) {
            const userDoc = bookingEmailQuery.docs[0];
            const userData = userDoc.data();
            const assignedHostId = userData.assignedHostId;
            const assignedPropertyId = userData.assignedPropertyId;
            // Verifica che il cliente sia assegnato all'host che ha l'integrazione Gmail
            if (assignedHostId === integrationOwnerHostId) {
                console.log(`Proxy: Client found by Booking email: ${senderEmail} → UID: ${userDoc.id}, Host: ${assignedHostId}, Property: ${assignedPropertyId}`);
                return {
                    clientUid: userDoc.id,
                    hostId: assignedHostId,
                    propertyId: assignedPropertyId,
                    clientData: userData,
                    matchType: 'emailBooking'
                };
            }
            else {
                console.warn(`Proxy: Client found by Booking email ${senderEmail} but assigned to different host (${assignedHostId}) than integration owner (${integrationOwnerHostId}). Ignoring.`);
            }
        }
        console.log(`Proxy: No client found for email: ${senderEmail} with integration owner: ${integrationOwnerHostId}`);
        return null;
    }
    catch (error) {
        console.error(`Proxy: Error searching for client by email ${senderEmail}:`, error.message, error.stack);
        return null;
    }
}
// Funzione handleChatMessageWithGemini COMPLETA E MODIFICATA (Modifica 10)
async function handleChatMessageWithGemini(channel, // <--- Tipo channel aggiornato
userId, // Per "email_booking", questo sarà tipo `booking:${bookingNumber}`; per "email_client" sarà l'UID del cliente
userMessage, hostId, propertyId, 
// Parametri opzionali per canali email
replyToClientEmail, // Per email_client: email diretta del cliente
replyToBookingChatEmail, // Per email_booking: email @mchat.booking.com
originalMessageId, originalSubject) {
    let generatedPrompt = null;
    let contextMetadata = null; // Metadati del contesto per debugging
    let aiTextResponseToClient = "";
    let toolCallToPublish = null;
    let wasBlockedBySafety = false;
    let blockReasonText = null;
    let processingErrorText = null;
    const MAX_EMAIL_REPLY_LENGTH = 15000; // Limite per il corpo dell'email
    try {
        const propertyData = await getPropertyData(hostId, propertyId);
        // console.log(`Proxy: Property data for "${propertyData.name}" retrieved for ${channel} user ${userId}.`); // Rimosso log ridondante se propertyData.name non esiste
        if (propertyData && propertyData.name) { // Aggiunto controllo
            console.log(`Proxy: Property data for "${propertyData.name}" retrieved for ${channel} user ${userId}.`);
        }
        else {
            console.warn(`Proxy: Property data retrieved for ${channel} user ${userId} (Host: ${hostId}, Prop: ${propertyId}), but property name is missing.`);
        }
        // Recupera la cronologia delle conversazioni per mantenere il contesto
        let conversationHistory = [];
        try {
            // Solo per canali diretti (app, whatsapp, email_client) dove userId è l'ID effettivo dell'utente
            if (channel === "app" || channel === "whatsapp" || channel === "email_client") {
                conversationHistory = await getConversationHistory(userId, propertyId, 10);
                console.log(`Proxy: Retrieved ${conversationHistory.length} previous conversations for ${channel} user ${userId} on property ${propertyId}`);
            }
            // Per email_booking, userId è nel formato "booking:${bookingNumber}", quindi skippiamo la cronologia
        }
        catch (historyError) {
            console.warn(`Proxy: Could not retrieve conversation history for ${channel} user ${userId}: ${historyError.message}`);
            // Continua senza cronologia in caso di errore
        }
        const promptResult = await generateGeminiPrompt(propertyData, userMessage, conversationHistory);
        generatedPrompt = promptResult.prompt;
        contextMetadata = promptResult.contextMetadata;
        // console.log(`Proxy: --- START GEMINI PROMPT (${channel} - ${userId}) ---\n${generatedPrompt.substring(0, 500)}...\n--- END GEMINI PROMPT ---`); // Log opzionale
        console.log(`Proxy: Generated prompt for ${channel} user ${userId}. Length: ${contextMetadata.totalPromptLength}, History: ${contextMetadata.conversationsUsedInPrompt}/${contextMetadata.conversationHistoryLength} conversations`);
        const apiKey = await getGeminiApiKey();
        const genAI = new generative_ai_1.GoogleGenerativeAI(apiKey);
        const geminiModel = genAI.getGenerativeModel({
            model: "gemini-1.5-flash-latest", // O il modello che preferisci
            tools: tools,
        });
        // Chiamata diretta a Gemini (supporta 1M+ token, nessun limite artificiale)
        const result = await geminiModel.generateContent({
            contents: [{ role: "user", parts: [{ text: generatedPrompt }] }],
        });
        const response = result.response;
        if (!response) {
            console.warn(`Proxy: No response object from Gemini for ${channel} user ${userId}.`);
            aiTextResponseToClient = "Non ho ricevuto una risposta dall'assistente AI in questo momento. Riprova più tardi.";
            wasBlockedBySafety = true;
            blockReasonText = "NO_RESPONSE_FROM_GEMINI";
            processingErrorText = "Gemini API did not return a response object.";
        }
        else if (response.promptFeedback?.blockReason) {
            const reason = response.promptFeedback.blockReason;
            console.warn(`Proxy: Gemini response blocked for ${channel} user ${userId} (Safety Reason: ${reason}). Ratings: ${JSON.stringify(response.promptFeedback?.safetyRatings)}`);
            aiTextResponseToClient = `Non posso elaborare questa richiesta a causa delle policy di sicurezza (Motivo: ${reason}).`;
            wasBlockedBySafety = true;
            blockReasonText = reason;
        }
        else {
            const functionCallPart = response.candidates?.[0]?.content?.parts?.find((part) => part.functionCall);
            if (functionCallPart && functionCallPart.functionCall) {
                const functionCall = functionCallPart.functionCall;
                console.log(`Proxy: Gemini requested Function Call for ${channel} user ${userId}:`, JSON.stringify(functionCall, null, 2));
                toolCallToPublish = {
                    toolName: functionCall.name,
                    toolArgs: functionCall.args || {},
                    context: { propertyId, hostId, clientId: userId, originalUserMessage: userMessage, originalChannel: channel }
                };
                aiTextResponseToClient = `Ok, ho preso in carico la tua richiesta riguardo a "${functionCall.name}". Ti terrò aggiornato.`; // Messaggio di acknowledgement
                try {
                    const dataBuffer = Buffer.from(JSON.stringify(toolCallToPublish));
                    await pubsub.topic(CONCIERGE_ACTIONS_TOPIC_NAME).publishMessage({ data: dataBuffer });
                    console.log(`Proxy: Tool call published to Pub/Sub topic '${CONCIERGE_ACTIONS_TOPIC_NAME}':`, toolCallToPublish);
                }
                catch (pubsubError) {
                    console.error(`Proxy: Error publishing tool call to Pub/Sub topic '${CONCIERGE_ACTIONS_TOPIC_NAME}':`, pubsubError);
                    processingErrorText = `Failed to publish action to Pub/Sub: ${pubsubError.message}`;
                    aiTextResponseToClient = "Si è verificato un problema nell'avviare la tua richiesta. Per favore, riprova più tardi o contatta l'host."; // Sovrascrive il messaggio di ack
                    toolCallToPublish = null;
                }
            }
            else {
                aiTextResponseToClient = response.text() || "Non sono riuscito a generare una risposta testuale al momento.";
                if ((channel === "email" || channel === "email_booking") && aiTextResponseToClient.length > MAX_EMAIL_REPLY_LENGTH) {
                    console.warn(`Proxy: Gemini email response for ${userId} was too long (${aiTextResponseToClient.length} chars) and was truncated.`);
                    aiTextResponseToClient = aiTextResponseToClient.substring(0, MAX_EMAIL_REPLY_LENGTH - 20) + "\n...(messaggio troncato)...";
                }
                console.log(`Proxy: Text response from Gemini for ${channel} user ${userId} received: "${aiTextResponseToClient.substring(0, 100)}..."`);
            }
        }
    }
    catch (error) {
        console.error(`Proxy: Error in handleChatMessageWithGemini for ${channel} user ${userId}:`, error.message || error, error.stack);
        processingErrorText = error.message || 'Unknown server error during Gemini processing';
        aiTextResponseToClient = "Si è verificato un errore interno durante l'elaborazione della tua richiesta. Riprova fra poco.";
    }
    // --- INIZIO BLOCCO INVIO EMAIL PER CANALI EMAIL (Aggiornato) ---
    if (channel === "email_booking") {
        if (aiTextResponseToClient && replyToBookingChatEmail && originalMessageId && originalSubject) {
            console.log(`Proxy: [Host: ${hostId}, Property: ${propertyId}] Attempting to send Gmail reply for Booking.com chat. To: ${replyToBookingChatEmail}`);
            try {
                // Recupera l'email dell'host per l'integrazione attiva
                const hostIntegrationSnapshot = await firestore.collection(HOST_EMAIL_INTEGRATIONS_COLLECTION)
                    .where('hostId', '==', hostId)
                    .where('status', '==', 'active')
                    .limit(1)
                    .get();
                if (!hostIntegrationSnapshot.empty) {
                    const hostEmailForSending = hostIntegrationSnapshot.docs[0].id; // L'ID del documento è l'email dell'host
                    const gmailClient = await getAuthenticatedGmailClient(hostEmailForSending);
                    if (gmailClient) { // gmailClient è Auth.OAuth2Client | null
                        // --- INIZIO CORREZIONE TIPO ---
                        const gmailApiInstance = googleapis_1.google.gmail({ version: 'v1', auth: gmailClient });
                        // --- FINE CORREZIONE TIPO ---
                        await sendGmailReplyForBooking(gmailApiInstance, // <-- Corretto: ora è di tipo gmail_v1.Gmail
                        hostEmailForSending, replyToBookingChatEmail, originalSubject, aiTextResponseToClient, originalMessageId);
                        console.log(`Proxy: [Host: ${hostId}] Reply to Booking.com chat email request processed for ${replyToBookingChatEmail}.`);
                    }
                    else {
                        const errMsg = `Failed to get authenticated Gmail client for host ${hostId} (email ${hostEmailForSending}). Cannot send Booking.com reply.`;
                        console.error(`Proxy: ${errMsg}`);
                        processingErrorText = (processingErrorText ? processingErrorText + "; " : "") + errMsg;
                    }
                }
                else {
                    const errMsg = `No active Gmail integration found for host ${hostId} to send Booking.com reply. Cannot send email.`;
                    console.error(`Proxy: ${errMsg}`);
                    processingErrorText = (processingErrorText ? processingErrorText + "; " : "") + errMsg;
                }
            }
            catch (emailError) {
                const errMsg = `Error sending Booking.com reply email to ${replyToBookingChatEmail} for host ${hostId}: ${emailError.message}`;
                console.error(`Proxy: ${errMsg}`, emailError.stack);
                processingErrorText = (processingErrorText ? processingErrorText + "; " : "") + errMsg;
            }
        }
        else {
            const warnMsg = `Proxy: [Host: ${hostId}] Cannot send Booking.com reply for channel 'email_booking' due to missing parameters. HasReplyText: ${!!aiTextResponseToClient}, HasReplyTo: ${!!replyToBookingChatEmail}, HasOrigMsgId: ${!!originalMessageId}, HasOrigSubj: ${!!originalSubject}`;
            console.warn(warnMsg);
            if (!aiTextResponseToClient)
                processingErrorText = (processingErrorText ? processingErrorText + "; " : "") + "No AI response generated to send.";
            else
                processingErrorText = (processingErrorText ? processingErrorText + "; " : "") + "Missing critical email parameters for Booking.com reply.";
        }
    }
    else if (channel === "email_client") {
        // Gestione invio risposta email diretta al cliente
        if (aiTextResponseToClient && replyToClientEmail && originalMessageId && originalSubject) {
            console.log(`Proxy: [Host: ${hostId}, Property: ${propertyId}] Attempting to send direct email reply to client: ${replyToClientEmail}`);
            try {
                // Recupera l'email dell'host per l'integrazione attiva
                const hostIntegrationSnapshot = await firestore.collection(HOST_EMAIL_INTEGRATIONS_COLLECTION)
                    .where('hostId', '==', hostId)
                    .where('status', '==', 'active')
                    .limit(1)
                    .get();
                if (!hostIntegrationSnapshot.empty) {
                    const hostEmailForSending = hostIntegrationSnapshot.docs[0].id; // L'ID del documento è l'email dell'host
                    const gmailClient = await getAuthenticatedGmailClient(hostEmailForSending);
                    if (gmailClient) {
                        const gmailApiInstance = googleapis_1.google.gmail({ version: 'v1', auth: gmailClient });
                        await sendGmailDirectReply(gmailApiInstance, hostEmailForSending, replyToClientEmail, originalSubject, aiTextResponseToClient, originalMessageId);
                        console.log(`Proxy: [Host: ${hostId}] Direct email reply sent to client ${replyToClientEmail}.`);
                    }
                    else {
                        const errMsg = `Failed to get authenticated Gmail client for host ${hostId} (email ${hostEmailForSending}). Cannot send client email reply.`;
                        console.error(`Proxy: ${errMsg}`);
                        processingErrorText = (processingErrorText ? processingErrorText + "; " : "") + errMsg;
                    }
                }
                else {
                    const errMsg = `No active Gmail integration found for host ${hostId} to send client email reply. Cannot send email.`;
                    console.error(`Proxy: ${errMsg}`);
                    processingErrorText = (processingErrorText ? processingErrorText + "; " : "") + errMsg;
                }
            }
            catch (emailError) {
                const errMsg = `Error sending direct email reply to ${replyToClientEmail} for host ${hostId}: ${emailError.message}`;
                console.error(`Proxy: ${errMsg}`, emailError.stack);
                processingErrorText = (processingErrorText ? processingErrorText + "; " : "") + errMsg;
            }
        }
        else {
            const warnMsg = `Proxy: [Host: ${hostId}] Cannot send direct client email reply for channel 'email_client' due to missing parameters. HasReplyText: ${!!aiTextResponseToClient}, HasReplyTo: ${!!replyToClientEmail}, HasOrigMsgId: ${!!originalMessageId}, HasOrigSubj: ${!!originalSubject}`;
            console.warn(warnMsg);
            if (!aiTextResponseToClient)
                processingErrorText = (processingErrorText ? processingErrorText + "; " : "") + "No AI response generated to send.";
            else
                processingErrorText = (processingErrorText ? processingErrorText + "; " : "") + "Missing critical email parameters for client reply.";
        }
    }
    // --- FINE BLOCCO INVIO EMAIL ---
    // Salva l'interazione, inclusa la risposta AI che è stata (o si è tentato di) inviare
    await saveChatInteraction({
        userId, hostId, propertyId, channel, // userId per email_booking è tipo `booking:${bookingNumber}`
        userMessage, aiResponse: aiTextResponseToClient, toolCallPublished: toolCallToPublish,
        promptSent: generatedPrompt, wasBlocked: wasBlockedBySafety, blockReason: blockReasonText,
        processingError: processingErrorText, // Ora include eventuali errori di invio email
        contextMetadata: contextMetadata || null // Include metadati del contesto per debugging
    });
    let clientErrorDetail = processingErrorText ? 'Internal Server Error processing your request.' : undefined;
    if (processingErrorText) {
        const lowerError = processingErrorText.toLowerCase();
        if (lowerError.includes('property details') || lowerError.includes('property information not found')) {
            clientErrorDetail = 'Property information not found.';
        }
        else if (lowerError.includes('secret') || lowerError.includes('permission denied') || lowerError.includes('api key')) {
            clientErrorDetail = 'Configuration error (API keys).';
        }
        else if (lowerError.includes('gmail reply')) {
            clientErrorDetail = 'Error sending reply email. Please check integration or contact support.';
        }
    }
    return { reply: aiTextResponseToClient, toolCallPublished: toolCallToPublish, error: clientErrorDetail };
}
app.post('/webhook/email-received', upload.any(), async (req, res) => {
    console.log('Proxy: --- INBOUND EMAIL WEBHOOK RECEIVED (processed with multer) ---');
    // Logga per vedere cosa multer ha parsato. Molto utile per il debug iniziale!
    // Scommenta queste righe durante i tuoi primi test per vedere il payload esatto.
    // console.log('Proxy: Email Webhook req.body (after multer):', JSON.stringify(req.body, null, 2));
    // console.log('Proxy: Email Webhook req.files (after multer):', JSON.stringify(req.files, null, 2)); // Per vedere eventuali allegati
    // console.log('Proxy: Email Webhook Headers:', JSON.stringify(req.headers, null, 2)); // Utile per vedere Content-Type originale
    res.status(200).send('OK'); // Rispondi SUBITO a SendGrid per evitare timeout e reinvii
    try {
        // Estrazione dei dati principali. Con multer che processa multipart/form-data,
        // i campi di testo dovrebbero essere in req.body.
        const fromHeader = req.body.from || "";
        const subject = req.body.subject || "Nessun Oggetto";
        let text = req.body.text || "";
        const toHeader = req.body.to || ""; // L'indirizzo a cui l'email era originariamente indirizzata (es. concierge@giovi.ai)
        // const html: string = req.body.html || ""; // Corpo HTML, se vuoi usarlo in futuro
        // Il campo 'envelope' è spesso una stringa JSON che deve essere parsata quando si usa multipart
        let envelope = null;
        if (req.body.envelope) {
            if (typeof req.body.envelope === 'string') {
                try {
                    envelope = JSON.parse(req.body.envelope);
                }
                catch (e) {
                    console.warn("Proxy: Failed to parse 'envelope' string from webhook (after multer):", req.body.envelope, e.message);
                }
            }
            else if (typeof req.body.envelope === 'object') { // A volte potrebbe essere già un oggetto
                envelope = req.body.envelope;
            }
        }
        // Priorità a envelope.from per l'email del mittente originale
        const senderEmailOriginal = envelope?.from || "";
        let senderEmailForLookup = senderEmailOriginal.toLowerCase();
        // Fallback se envelope.from non è presente o è vuoto
        if (!senderEmailForLookup) {
            const fromMatch = fromHeader.match(/<([^>]+)>/); // Estrae email da "Nome <email@example.com>"
            senderEmailForLookup = fromMatch ? fromMatch[1].toLowerCase() : fromHeader.toLowerCase();
        }
        // Controlli essenziali prima di procedere
        if (!senderEmailForLookup || !text.trim()) {
            console.warn('Proxy: Email webhook (multer) received missing critical sender email or text body. Sender Attempted:', senderEmailForLookup, 'Body Empty After Trim:', !text.trim(), 'Original From Header:', fromHeader);
            return;
        }
        console.log(`Proxy: (Multer) Processing inbound email. Actual Sender Determined: ${senderEmailForLookup}, Original To: ${toHeader}, Subject: "${subject.substring(0, 50)}..."`);
        // Pulizia del corpo dell'email da firme e testo di risposte/inoltri
        const replyLines = text.split('\n');
        let mainMessageBody = "";
        const stopPatterns = [
            /^On.*wrote:$/im, /^Il giorno.*ha scritto:$/im,
            /^> ?/m,
            /^\s*From:/im, /^\s*Sent:/im, /^\s*To:/im, /^\s*Date:/im, /^\s*Subject:/im,
            /^\s*Da:/im, /^\s*Inviato:/im, /^\s*A:/im, /^\s*Data:/im, /^\s*Oggetto:/im,
            /^\s*---*Original Message---*/im, /^\s*---*Messaggio Originale---*/im,
            /^\s*_{20,}/im,
            /^\s*Risposta inoltrata/im, /^\s*Messaggio inoltrato/im,
            /^\s*Forwarded message/im
        ];
        for (const line of replyLines) {
            if (stopPatterns.some(pattern => pattern.test(line))) {
                console.log(`Proxy: Stripping reply content at line starting with: "${line.substring(0, 70)}..."`);
                break;
            }
            mainMessageBody += line + "\n";
        }
        text = mainMessageBody.trim();
        if (!text) {
            console.warn(`Proxy: (Multer) Email body became empty after stripping reply content. From: ${senderEmailForLookup}, Subject: "${subject}"`);
            await saveChatInteraction({
                userId: `email:${senderEmailForLookup}`, hostId: null, propertyId: null, channel: "email",
                userMessage: req.body.text || "Original body was also empty or only reply after parsing (multer).",
                aiResponse: "Il corpo dell'email è risultato vuoto dopo la rimozione del testo di risposta/inoltro.",
                toolCallPublished: null, promptSent: null, wasBlocked: true,
                blockReason: "EMPTY_BODY_CLEANED_MULTER", processingError: null
            });
            return;
        }
        // Variabili per il contesto del cliente
        let firebaseClientUid = null;
        let hostId = null;
        let propertyId = null;
        let userIdForLog = `email:${senderEmailForLookup}`;
        // 1. Identifica se il mittente è un CLIENTE noto
        const usersRef = firestore.collection('users');
        const clientSnapshot = await usersRef
            .where('role', '==', 'client')
            .where('email', '==', senderEmailForLookup) // Assicurati che le email in Firestore siano normalizzate (es. lowercase)
            .limit(1)
            .get();
        if (!clientSnapshot.empty) {
            const userDoc = clientSnapshot.docs[0];
            const userData = userDoc.data();
            firebaseClientUid = userDoc.id;
            hostId = userData.assignedHostId;
            propertyId = userData.assignedPropertyId;
            userIdForLog = firebaseClientUid;
            if (!hostId || !propertyId) {
                console.error(`Proxy: Client ${firebaseClientUid} (Email: ${senderEmailForLookup}) found but missing assignment data (hostId/propertyId).`);
                const replyText = "Si è verificato un problema nel recuperare i dettagli della tua prenotazione. Per favore, contatta direttamente l'host o il supporto specificando la tua richiesta e la proprietà di riferimento.";
                await sendEmailInternal(senderEmailForLookup, `Re: ${subject || "Richiesta non processata"}`, replyText);
                await saveChatInteraction({ userId: userIdForLog, hostId, propertyId, channel: "email", userMessage: text, aiResponse: replyText, toolCallPublished: null, promptSent: null, wasBlocked: true, blockReason: "MISSING_ASSIGNMENT_EMAIL", processingError: "Host/Property ID missing for recognized client via email." });
                return;
            }
            console.log(`Proxy: Email User ${senderEmailForLookup} identified as client ${firebaseClientUid}, Host: ${hostId}, Property: ${propertyId}. Processing with Gemini...`);
            // 2. Processa il messaggio con Gemini
            const geminiResult = await handleChatMessageWithGemini("email", firebaseClientUid, text, hostId, propertyId);
            // 3. Invia la risposta di Gemini via email
            if (geminiResult.reply) {
                await sendEmailInternal(senderEmailForLookup, `Re: ${subject || "Risposta alla tua richiesta"}`, geminiResult.reply);
            }
            else {
                console.warn(`Proxy: Gemini did not provide a direct reply for ${senderEmailForLookup}. Tool call: ${!!geminiResult.toolCallPublished}. Error: ${geminiResult.error}`);
                // Invia comunque un acknowledgement se Gemini non ha dato una reply diretta (es. solo tool call)
                // ma handleChatMessageWithGemini dovrebbe già restituire un messaggio di presa in carico.
                // Questa è una sicurezza aggiuntiva.
                const ackReply = geminiResult.toolCallPublished ?
                    `La tua richiesta (${subject || 'N/D'}) è stata presa in carico e la stiamo elaborando.` :
                    "Abbiamo ricevuto la tua email. Verrai ricontattato a breve se necessario.";
                await sendEmailInternal(senderEmailForLookup, `Re: ${subject || "Richiesta ricevuta"}`, ackReply);
            }
            // Il log di saveChatInteraction è già gestito DENTRO handleChatMessageWithGemini
        }
        else {
            // Mittente non riconosciuto come cliente
            console.log(`Proxy: Email from ${senderEmailForLookup} not recognized as an active client. Original recipient: ${toHeader}, Subject: "${subject.substring(0, 50)}..."`);
            const replyText = "Ciao! Il tuo indirizzo email non risulta associato a una prenotazione attiva o a un utente cliente nel nostro sistema. Se sei un nostro ospite, assicurati di scrivere dall'email utilizzata per la prenotazione o contatta il supporto fornendo i dettagli della tua prenotazione e della proprietà di riferimento.";
            await sendEmailInternal(senderEmailForLookup, `Re: ${subject || "Contatto non riconosciuto"}`, replyText);
            await saveChatInteraction({ userId: userIdForLog, hostId: null, propertyId: null, channel: "email", userMessage: text, aiResponse: replyText, toolCallPublished: null, promptSent: null, wasBlocked: true, blockReason: "UNRECOGNIZED_SENDER_EMAIL", processingError: null });
        }
    }
    catch (error) {
        console.error(`Proxy: CRITICAL Error processing inbound email webhook pipeline (after multer):`, error.message || error, error.stack);
        const requestBodySample = typeof req.body === 'string' ? req.body.substring(0, 500) : JSON.stringify(req.body).substring(0, 500);
        await saveChatInteraction({
            userId: `webhook_error_multer`,
            hostId: null, propertyId: null, channel: "email",
            userMessage: `Webhook payload (multer) sample: ${requestBodySample}`,
            aiResponse: null, toolCallPublished: null, promptSent: null,
            wasBlocked: true, blockReason: "WEBHOOK_PIPELINE_ERROR_MULTER",
            processingError: error.message || "Unknown webhook pipeline error"
        });
    }
});
// FINE BLOCCO DELL'ENDPOINT /webhook/email-received
// RIGA DOPO CUI INSERIRE (indicativa, dopo la fine dell'endpoint /webhook/email-received):
// }); // Fine di app.post('/webhook/email-received')
// --- ENDPOINT PROTETTO PER INVIARE EMAIL DAL WORKFLOW SERVICE (NUOVO E COMPLETO) ---
app.post('/system/send-email', checkSystemAuth, async (req, res) => {
    const { to, // Destinatario email (stringa)
    subject, // Oggetto dell'email (stringa)
    text, // Corpo dell'email in formato testo semplice (stringa)
    html, // Corpo dell'email in formato HTML (stringa, opzionale)
    hostId, // ID dell'host per contesto nel logging (stringa, opzionale)
    propertyId, // ID della proprietà per contesto nel logging (stringa, opzionale)
    relatedTaskId // ID del task correlato per contesto nel logging (stringa, opzionale)
     } = req.body;
    // Validazione dei parametri minimi richiesti
    if (!to || !subject || !text) {
        console.warn("Proxy: /system/send-email - Bad Request: Missing 'to', 'subject', or 'text' parameter.");
        return res.status(400).send({ error: 'Bad Request: Missing "to", "subject", or "text" parameter for email.' });
    }
    console.log(`Proxy: Request /system/send-email - Attempting to send to ${to}. Subject: "${subject.substring(0, 50)}..."`);
    // La funzione ensureSendGridInitialized() è chiamata all'interno di sendEmailInternal,
    // quindi non è necessario chiamarla esplicitamente qui di nuovo se sendEmailInternal la gestisce.
    const sendResult = await sendEmailInternal(to, subject, text, html); // Passa html se presente
    if (sendResult.success) {
        // Logga l'interazione di invio email di sistema
        await saveChatInteraction({
            userId: `system_to_email:${to}`, // Identificativo per messaggi inviati dal sistema via email
            hostId: hostId || null, // Usa null se non fornito
            propertyId: propertyId || null, // Usa null se non fornito
            channel: "system_email_sent",
            userMessage: `Subject: ${subject}\nText: ${text.substring(0, 200)}...`, // Logga parte del messaggio inviato
            aiResponse: null, // Non è una risposta AI in questo caso
            toolCallPublished: null,
            promptSent: null,
            wasBlocked: false,
            blockReason: null,
            processingError: null,
            relatedTaskId: relatedTaskId || null // Usa null se non fornito
        });
        console.log(`Proxy: /system/send-email - Email to ${to} sent successfully. Message ID: ${sendResult.messageId}`);
        return res.status(200).send({
            success: true,
            messageId: sendResult.messageId,
            message: "Email inviata con successo dal sistema."
        });
    }
    else {
        // L'errore è già loggato da sendEmailInternal
        console.error(`Proxy: /system/send-email - Failed to send email to ${to}. Details: ${sendResult.errorDetails}`);
        return res.status(500).send({
            success: false,
            error: "Invio email fallito dal sistema.",
            details: sendResult.errorDetails
        });
    }
});
app.post('/chat', checkAuth, async (req, res) => {
    const clientUid = req.user.uid;
    const { message, hostId, propertyId } = req.body;
    if (!message || !hostId || !propertyId) {
        res.status(400).send({ error: 'Bad Request: Missing parameters.' });
        return;
    }
    console.log(`Proxy: Request /chat from App User: ${clientUid}, Host: ${hostId}, Property: ${propertyId}, Msg: "${message.substring(0, 50)}..."`);
    try {
        const clientDoc = await firestore.collection('users').doc(clientUid).get();
        if (!clientDoc.exists || clientDoc.data()?.role !== 'client' || clientDoc.data()?.assignedHostId !== hostId || clientDoc.data()?.assignedPropertyId !== propertyId) {
            console.warn(`Proxy: App User ${clientUid} not authorized for /chat (assignment mismatch or role).`);
            res.status(403).send({ error: 'Forbidden: Client assignment or role mismatch.' });
            return;
        }
    }
    catch (dbError) {
        console.error(`Proxy: Error fetching user ${clientUid} for /chat auth:`, dbError);
        res.status(500).send({ error: 'Internal error during user authorization.' });
        return;
    }
    const result = await handleChatMessageWithGemini("app", clientUid, message, hostId, propertyId);
    if (result.error) {
        let statusCode = 500;
        if (result.error.includes('Property information not found'))
            statusCode = 404;
        else if (result.error.includes('Configuration error'))
            statusCode = 500; // Internal server error
        res.status(statusCode).send({ error: result.error, reply: result.reply });
        return;
    }
    res.status(200).send({ reply: result.reply });
    return;
});
app.get('/whatsapp', async (req, res) => {
    console.log('Proxy: GET /whatsapp - Webhook verification request');
    const mode = req.query['hub.mode'];
    const token = req.query['hub.verify_token'];
    const challenge = req.query['hub.challenge'];
    try {
        const verifyTokenFromSecret = await getSecret(WHATSAPP_VERIFY_TOKEN_SECRET_ID);
        if (mode === 'subscribe' && token === verifyTokenFromSecret) {
            console.log('Proxy: WEBHOOK_VERIFIED');
            res.status(200).send(challenge);
            return;
        }
        else {
            console.warn('Proxy: Webhook verification failed. Mode or token mismatch.');
            res.sendStatus(403);
            return;
        }
    }
    catch (error) {
        console.error("Proxy: Error during webhook verification:", error.message, error.stack);
        res.sendStatus(500);
        return;
    }
});
app.post('/whatsapp', async (req, res) => {
    console.log('Proxy: POST /whatsapp - Notification from Meta');
    res.sendStatus(200); // Rispondi subito a Meta
    const body = req.body;
    if (body.object === 'whatsapp_business_account' && body.entry?.length > 0) {
        for (const entry of body.entry) {
            for (const change of entry.changes) {
                if (change.field === 'messages' && change.value?.messages?.length > 0) {
                    const messageData = change.value.messages[0];
                    const senderIdRaw = messageData.from; // Numero del mittente, es. "393331234567"
                    const messageText = messageData.text?.body;
                    if (messageData.type === 'text' && messageText) {
                        console.log(`Proxy: WhatsApp message from ${senderIdRaw}: "${messageText.substring(0, 100)}..."`);
                        const senderIdE164 = senderIdRaw.startsWith('+') ? senderIdRaw : `+${senderIdRaw}`; // Assicura formato E.164
                        let firebaseClientUid = null;
                        let hostId = null;
                        let propertyId = null;
                        let userIdForLog = `whatsapp:${senderIdE164}`; // Default per log
                        try {
                            // 1. Verifica se il mittente è un CLIENTE noto
                            const usersRef = firestore.collection('users');
                            const clientSnapshot = await usersRef
                                .where('role', '==', 'client')
                                .where('whatsappPhoneNumber', '==', senderIdE164) // Assumendo che whatsappPhoneNumber sia E.164
                                .limit(1)
                                .get();
                            if (!clientSnapshot.empty) {
                                const userDoc = clientSnapshot.docs[0];
                                const userData = userDoc.data();
                                firebaseClientUid = userDoc.id; // UID Firebase del cliente
                                hostId = userData.assignedHostId;
                                propertyId = userData.assignedPropertyId;
                                userIdForLog = firebaseClientUid; // Usa UID per log se cliente noto
                                if (!hostId || !propertyId) {
                                    console.error(`Proxy: User ${firebaseClientUid} (WA: ${senderIdE164}) found but missing assignment data (hostId/propertyId).`);
                                    const replyText = "Si è verificato un problema nel recuperare i dettagli della tua prenotazione. Per favore, contatta direttamente l'host.";
                                    await sendWhatsAppMessageInternal(senderIdE164, { type: "text", body: replyText });
                                    await saveChatInteraction({ userId: userIdForLog, hostId, propertyId, channel: "whatsapp", userMessage: messageText, aiResponse: replyText, toolCallPublished: null, promptSent: null, wasBlocked: true, blockReason: "MISSING_ASSIGNMENT_DATA", processingError: "Host/Property ID missing for recognized client." });
                                    continue; // Processa il prossimo messaggio/change
                                }
                                console.log(`Proxy: WA User ${senderIdE164} identified as client ${firebaseClientUid}, H:${hostId}, P:${propertyId}`);
                                const result = await handleChatMessageWithGemini("whatsapp", firebaseClientUid, messageText, hostId, propertyId);
                                await sendWhatsAppMessageInternal(senderIdE164, { type: "text", body: result.reply });
                            }
                            else {
                                // 2. Se non è un cliente, verifica se è un FORNITORE che risponde a un TASK ATTIVO
                                console.log(`Proxy: Number ${senderIdE164} not a client. Checking if it's a provider for an active task...`);
                                const tasksRef = firestore.collection(PROPERTY_TASKS_COLLECTION);
                                // Query per task che aspettano una risposta dal fornitore con questo numero
                                const providerTaskSnapshot = await tasksRef
                                    .where('providerContactInfo.phone', '==', senderIdE164)
                                    .where('status', 'in', ['provider_notified', 'requested_by_client', 'provider_confirmed', 'appointment_scheduled']) // Stati in cui ci si aspetta risposta
                                    .orderBy('createdAt', 'desc') // Prendi il task più recente se ce ne sono multipli (improbabile ma sicuro)
                                    .limit(1)
                                    .get();
                                if (!providerTaskSnapshot.empty) {
                                    const taskDoc = providerTaskSnapshot.docs[0];
                                    const taskData = taskDoc.data();
                                    if (taskData && taskData.clientId && taskData.hostId && taskData.propertyId && taskData.originalChannel) {
                                        const providerResponsePayload = {
                                            source: "provider_response",
                                            providerPhoneNumber: senderIdE164,
                                            providerMessageText: messageText,
                                            relatedTaskId: taskDoc.id,
                                            originalClientContext: {
                                                clientId: taskData.clientId, // UID Firebase del cliente
                                                hostId: taskData.hostId,
                                                propertyId: taskData.propertyId,
                                                originalChannel: taskData.originalChannel // 'app' o 'whatsapp'
                                            }
                                        };
                                        const dataBuffer = Buffer.from(JSON.stringify(providerResponsePayload));
                                        await pubsub.topic(CONCIERGE_ACTIONS_TOPIC_NAME).publishMessage({ data: dataBuffer });
                                        console.log(`Proxy: Provider response from ${senderIdE164} for task ${taskDoc.id} (client ${taskData.clientId}) published to Pub/Sub.`);
                                        // Log specifico per la risposta del fornitore
                                        await saveChatInteraction({ userId: senderIdE164, hostId: taskData.hostId, propertyId: taskData.propertyId, channel: "provider_wa_reply", userMessage: messageText, aiResponse: null, toolCallPublished: null, promptSent: null, wasBlocked: false, blockReason: null, processingError: null, relatedTaskId: taskDoc.id });
                                    }
                                    else {
                                        console.warn(`Proxy: Task ${taskDoc.id} found for provider ${senderIdE164} but is missing essential context data (clientId, hostId, propertyId, or originalChannel). Cannot process provider response.`);
                                    }
                                }
                                else {
                                    // 3. Se non è né un cliente noto né un fornitore per un task attivo
                                    console.log(`Proxy: Number ${senderIdE164} not recognized as a client or a provider for an active task.`);
                                    const reply = "Ciao! Il tuo numero non è attualmente riconosciuto o associato a una richiesta attiva nel nostro sistema. Se sei un ospite, assicurati che il tuo numero WhatsApp sia registrato correttamente. Se sei un fornitore, attendi una nostra comunicazione. Per assistenza, contatta l'amministratore o l'host.";
                                    await sendWhatsAppMessageInternal(senderIdE164, { type: "text", body: reply });
                                    await saveChatInteraction({ userId: senderIdE164, hostId: null, propertyId: null, channel: "whatsapp", userMessage: messageText, aiResponse: reply, toolCallPublished: null, promptSent: null, wasBlocked: true, blockReason: "UNRECOGNIZED_SENDER", processingError: null });
                                }
                            }
                        }
                        catch (error) {
                            console.error(`Proxy: Error processing WhatsApp message from ${senderIdE164}:`, error.message, error.stack);
                            const reply = "Si è verificato un problema tecnico durante l'elaborazione del tuo messaggio. Riprova più tardi o contatta il supporto se il problema persiste.";
                            await sendWhatsAppMessageInternal(senderIdE164, { type: "text", body: reply });
                            // Log con userIdForLog che potrebbe essere UID o numero WA
                            await saveChatInteraction({ userId: userIdForLog, hostId, propertyId, channel: "whatsapp", userMessage: messageText, aiResponse: reply, toolCallPublished: null, promptSent: null, wasBlocked: true, blockReason: "WHATSAPP_PROCESSING_ERROR", processingError: error.message });
                        }
                    }
                    else {
                        console.log(`Proxy: Received WhatsApp message from ${senderIdRaw} which is not type 'text' or has no body. Type: ${messageData.type}. Ignored.`);
                    }
                }
            }
        }
    }
    else {
        console.warn('Proxy: POST /whatsapp - Unrecognized payload structure or not a WhatsApp Business Account notification.');
    }
});
app.post('/system/send-whatsapp', checkSystemAuth, async (req, res) => {
    const { to, text, templateName, templateLanguageCode, templateParams, hostId, propertyId, relatedTaskId } = req.body;
    // 'to' deve essere presente in entrambi i casi (testo o template)
    if (!to) {
        res.status(400).send({ error: 'Bad Request: Missing "to" parameter.' });
        return;
    }
    const recipientE164 = to.startsWith('+') ? to : `+${to}`; // Assicura il '+'
    let messageConfig;
    let logIdentifier;
    let userMessageForLog;
    if (templateName && Array.isArray(templateParams)) {
        // Invio di un messaggio template
        logIdentifier = `template '${templateName}' to ${recipientE164}`;
        // Per il log, mostriamo il nome del template e alcuni parametri
        userMessageForLog = `[Template: ${templateName}] Params: ${JSON.stringify(templateParams.slice(0, 3))}...`;
        const components = [{
                type: "body",
                // Assicura che ogni parametro sia una stringa; i valori null/undefined diventano stringhe vuote
                parameters: templateParams.map(param => ({ type: "text", text: String(param === null || param === undefined ? "" : param) }))
            }];
        // Qui potresti aggiungere logica per componenti 'header' o 'button' se i tuoi template li usano.
        // Esempio: se hai un ID di immagine pre-caricato per l'header:
        // if (req.body.templateHeaderImageId) {
        //   components.unshift({ type: "header", parameters: [{ type: "image", image: { id: req.body.templateHeaderImageId } }] });
        // }
        messageConfig = {
            type: "template",
            name: templateName,
            languageCode: templateLanguageCode || "it", // Default a 'it' se non fornito
            components: components
        };
    }
    else if (text) {
        // Invio di un messaggio di testo semplice
        logIdentifier = `text message to ${recipientE164}: "${text.substring(0, 30)}..."`;
        userMessageForLog = text;
        messageConfig = { type: "text", body: text };
    }
    else {
        // Parametri non validi
        res.status(400).send({ error: 'Bad Request: Missing "text" for text message, or ("templateName" and "templateParams") for template message.' });
        return;
    }
    console.log(`Proxy: Request /system/send-whatsapp - Sending ${logIdentifier}`);
    try {
        const sendResult = await sendWhatsAppMessageInternal(recipientE164, messageConfig);
        if (sendResult && sendResult.messages?.[0]?.id) {
            // Salva l'interazione nel log di chat
            await saveChatInteraction({
                userId: `system_to:${recipientE164}`, // Identificativo per messaggi inviati dal sistema
                hostId, // opzionale, per contesto
                propertyId, // opzionale, per contesto
                channel: "system",
                userMessage: userMessageForLog, // Contiene il testo o i dettagli del template
                aiResponse: null, // Non è una risposta AI in questo caso
                toolCallPublished: null,
                promptSent: null,
                wasBlocked: false,
                blockReason: null,
                processingError: null,
                relatedTaskId // Se il messaggio è relativo a un task specifico
            });
            res.status(200).send({ success: true, messageId: sendResult.messages[0].id, message: "Messaggio WhatsApp inviato con successo." });
            return;
        }
        else {
            // Errore riportato dall'API di Meta o fallimento interno in sendWhatsAppMessageInternal
            const metaError = sendResult?.error?.message || "Invio WhatsApp fallito (risposta API Meta o errore interno proxy).";
            const metaDetails = sendResult?.error?.error_data?.details || sendResult?.error; // Dettagli aggiuntivi se presenti
            console.error(`Proxy: Failed to send WhatsApp via /system/send-whatsapp to ${recipientE164}. Meta/Proxy response:`, JSON.stringify(sendResult, null, 2));
            res.status(500).send({ success: false, error: metaError, details: metaDetails });
            return;
        }
    }
    catch (error) {
        console.error(`Proxy: Uncaught API Error in /system/send-whatsapp for ${recipientE164}:`, error.message, error.stack);
        res.status(500).send({ success: false, error: `Errore imprevisto durante l'invio del messaggio WhatsApp: ${error.message}` });
        return;
    }
});
// Endpoint di Health Check
app.get('/_health', (req, res) => {
    res.status(200).send('OK');
});
// ... (tutto il codice precedente, inclusa la funzione sendGmailReplyForBooking)
// --- INIZIO BLOCCO AVVIO SERVER (Modifica 12 - Revisione Finale) ---
// Avvio Server Express
if (process.env.NODE_ENV !== 'test') { // Non avviare il server durante i test
    app.listen(PORT, async () => {
        console.log(`gemini-proxy-service listening on port ${PORT}`);
        console.log(`Pub/Sub Topic for concierge actions: ${CONCIERGE_ACTIONS_TOPIC_NAME}`);
        console.log(`Pub/Sub Topic for Gmail notifications will be: ${GMAIL_NOTIFICATIONS_PUB_SUB_TOPIC_NAME}`);
        if (YOUR_PHONE_NUMBER_ID === '656411320878547' && !process.env.YOUR_PHONE_NUMBER_ID) {
            console.warn("Proxy CRITICAL WARNING: YOUR_PHONE_NUMBER_ID is using a hardcoded fallback. Set via environment variable for production!");
        }
        // Verifica esplicita di BASE_URL in ambiente di produzione
        if (process.env.NODE_ENV === 'production' && !process.env.BASE_URL) {
            console.error("Proxy CRITICAL STARTUP ERROR: BASE_URL environment variable is NOT SET for production. OAuth2 redirects WILL FAIL. Please set it to your Cloud Run service's public URL (e.g., https://your-service-name.run.app).");
            // Potresti voler far fallire l'avvio qui:
            // process.exit(1);
        }
        else if (process.env.BASE_URL) {
            console.log(`Proxy: Using BASE_URL: ${process.env.BASE_URL}`);
        }
        else if (process.env.NODE_ENV !== 'production') {
            console.log(`Proxy: BASE_URL not set, will use dynamically determined URL for local development (e.g., http://localhost:${PORT}).`);
        }
        try {
            console.log("Proxy: Attempting to pre-load critical API keys, OAuth credentials, and encryption key at startup...");
            // 1. Inizializza SendGrid (gestisce ENV var o recupero da Secret Manager)
            await ensureSendGridInitialized();
            if (!sendgridApiKeyLoaded) {
                console.warn("Proxy: WARNING - SendGrid API Key was NOT successfully loaded during startup. Email functionality (non-Booking.com) will be impaired.");
            }
            else {
                console.log("Proxy: SendGrid API Key initialized successfully.");
            }
            // 2. Carica chiave Gemini (la mette in cache se non già presente)
            await getSecret(GEMINI_SECRET_ID);
            console.log("Proxy: Gemini API Key loaded/checked.");
            // 3. Pre-carica la chiave per checkSystemAuth (autenticazione tra servizi)
            if (!EXPECTED_WORKFLOW_SYSTEM_KEY) {
                EXPECTED_WORKFLOW_SYSTEM_KEY = await getSecret(WORKFLOW_SERVICE_API_KEY_SECRET_ID);
                console.log("Proxy: Workflow service API key for system authentication loaded successfully during startup.");
            }
            else {
                console.log("Proxy: Workflow service API key for system authentication was already available.");
            }
            // 4. Carica credenziali OAuth di Google
            GOOGLE_OAUTH_CLIENT_ID = await getSecret(GOOGLE_OAUTH_CLIENT_ID_SECRET_ID);
            GOOGLE_OAUTH_CLIENT_SECRET = await getSecret(GOOGLE_OAUTH_CLIENT_SECRET_SECRET_ID);
            if (!GOOGLE_OAUTH_CLIENT_ID || !GOOGLE_OAUTH_CLIENT_SECRET) {
                console.error("Proxy: CRITICAL STARTUP ERROR - Google OAuth Client ID or Client Secret could not be loaded from Secret Manager. Gmail integration WILL FAIL.");
                // Considera di far fallire l'avvio: throw new Error("Failed to load Google OAuth credentials.");
            }
            else {
                console.log("Proxy: Google OAuth Client ID and Client Secret loaded successfully.");
            }
            // 5. Carica e valida la chiave di crittografia dei token host
            await ensureTokenEncryptionKey();
            // ensureTokenEncryptionKey logga già il successo o l'errore al suo interno.
            console.log("Proxy: All critical configurations attempted. Service should be ready if no CRITICAL errors were logged above.");
        }
        catch (error) {
            console.error("Proxy: !!! CRITICAL STARTUP ERROR !!! Could not load one or more critical configurations (API keys, OAuth creds, or encryption key). Service functionality WILL BE SEVERELY IMPAIRED or NON-FUNCTIONAL.", error.message, error.stack);
            // In un ambiente di produzione, è fortemente consigliato far fallire l'avvio del server qui:
            // process.exit(1); 
        }
    });
}
process.on('uncaughtException', (err, origin) => { console.error(`[GEMINI-PROXY] UNCAUGHT EXCEPTION! Origin: ${origin}`, err); });
process.on('unhandledRejection', (reason, promise) => { console.error('[GEMINI-PROXY] UNHANDLED REJECTION!', reason, promise); });
// --- FINE BLOCCO AVVIO SERVER (Modifica 12 - Revisione Finale) ---
//# sourceMappingURL=server.js.map