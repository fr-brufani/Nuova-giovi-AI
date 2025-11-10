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
// pms-sync-service/src/server.ts
const express_1 = __importDefault(require("express"));
const cors_1 = __importDefault(require("cors"));
const admin = __importStar(require("firebase-admin"));
const papaparse_1 = __importDefault(require("papaparse")); // Importa papaparse
// --- Inizializzazioni ---
admin.initializeApp();
const firestore = admin.firestore();
const FieldValue = admin.firestore.FieldValue; // Per timestamp
const app = (0, express_1.default)();
// --- Costanti e Configurazioni ---
const PORT = process.env.PORT || 8080;
// --- Middleware ---
app.use((0, cors_1.default)({ origin: true })); // Abilita CORS per le richieste dal frontend Flutter
app.use(express_1.default.json({ limit: '10mb' })); // Aumenta limite JSON per CSV grandi nel body
// Middleware per autenticazione Firebase ID Token
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
        // Aggiungi l'utente decodificato alla richiesta per usarlo dopo
        req.user = decodedToken;
        next();
    }
    catch (error) {
        console.error('Error verifying Firebase ID token:', error);
        res.status(403).send({ error: 'Forbidden: Invalid or expired token.' });
    }
};
// --- Helper Functions ---
/**
 * Normalizza un numero di telefono in formato E.164 (es. +39...).
 * Rimuove spazi, aggiunge '+' se mancano prefissi comuni.
 */
const normalizePhoneNumber = (prefix, number) => {
    if (!number || number.trim() === '') {
        return null; // Nessun numero fornito
    }
    let fullNumber = (prefix && prefix.trim() !== '' ? prefix.trim() : '') + number.trim();
    fullNumber = fullNumber.replace(/\s+/g, ''); // Rimuove tutti gli spazi
    if (fullNumber.startsWith('+')) {
        return fullNumber; // Già in formato corretto (presumibilmente)
    }
    // Heuristic: Se inizia con un prefisso comune senza +, aggiungilo
    if (fullNumber.startsWith('39') || fullNumber.startsWith('41') || fullNumber.startsWith('44')) { // Aggiungi altri prefissi se necessario
        return `+${fullNumber}`;
    }
    // Altrimenti, non possiamo essere sicuri, restituisci null o il numero così com'è?
    // Per ora restituiamo null se non siamo sicuri del formato internazionale
    console.warn(`Numero di telefono non normalizzato in formato E.164: ${fullNumber}`);
    return null; // O return fullNumber se vuoi salvarlo comunque
};
/**
 * Mappa lo stato della prenotazione dal CSV allo stato interno.
 */
const mapReservationStatus = (csvStatus) => {
    const status = csvStatus?.toLowerCase().trim() ?? '';
    if (status.includes('conferma'))
        return 'confirmed';
    if (status.includes('annulla') || status.includes('cancel'))
        return 'cancelled';
    if (status.includes('check-out') || status.includes('partit'))
        return 'completed';
    if (status.includes('check-in'))
        return 'active'; // Es. "Check-in Eseguito"
    if (status.includes('pending') || status.includes('attesa'))
        return 'pending';
    return 'unknown'; // Default se non mappato
};
/**
 * Converte una data YYYY-MM-DD in Timestamp Firestore (inizio del giorno UTC).
 */
const parseDateToTimestamp = (dateString) => {
    if (!dateString || !/^\d{4}-\d{2}-\d{2}$/.test(dateString.trim())) {
        return null; // Formato non valido
    }
    try {
        // Crea data UTC per evitare problemi di timezone locale del server
        const date = new Date(`${dateString.trim()}T00:00:00Z`);
        if (isNaN(date.getTime()))
            return null; // Data non valida
        return admin.firestore.Timestamp.fromDate(date);
    }
    catch (e) {
        console.error(`Errore parsing data ${dateString}:`, e);
        return null;
    }
};
// --- Endpoint Principale POST /import-pms-data ---
app.post('/import-pms-data', checkAuth, async (req, res) => {
    const hostId = req.user.uid; // UID dell'host autenticato
    const { csvData, importType } = req.body; // tipo: 'clients' o 'reservations'
    if (!csvData || typeof csvData !== 'string' || csvData.trim() === '') {
        return res.status(400).send({ error: 'Bad Request: Missing or empty csvData.' });
    }
    if (importType !== 'clients' && importType !== 'reservations') {
        return res.status(400).send({ error: 'Bad Request: Invalid importType. Must be "clients" or "reservations".' });
    }
    console.log(`[${hostId}] Ricevuta richiesta di import ${importType}. Dimensione dati: ${csvData.length} chars.`);
    try {
        // 1. Parsifica il CSV
        const parseResult = papaparse_1.default.parse(csvData.trim(), {
            header: true,
            delimiter: ";",
            skipEmptyLines: 'greedy', // Più robusto per righe vuote
            transformHeader: header => header.trim(),
            dynamicTyping: false,
        });
        // Filtra eventuali errori non critici
        const criticalErrors = parseResult.errors.filter(e => e.code !== 'TooFewFields' && e.code !== 'TooManyFields');
        if (criticalErrors.length > 0) {
            console.error(`[${hostId}] Errori critici parsing CSV:`, criticalErrors);
            return res.status(400).send({
                error: 'CSV Parsing Error (Critical).',
                details: criticalErrors.slice(0, 5)
            });
        }
        if (parseResult.errors.length > criticalErrors.length) {
            console.warn(`[${hostId}] Errori non critici parsing CSV (es. field count mismatch):`, parseResult.errors);
        }
        if (!parseResult.data || parseResult.data.length === 0) {
            return res.status(400).send({ error: 'No valid data found in CSV.' });
        }
        // Filtra righe potenzialmente vuote o invalide risultanti dal parsing
        const rows = parseResult.data.filter(row => Object.values(row).some(val => val !== null && val !== undefined && String(val).trim() !== ''));
        if (rows.length === 0) {
            return res.status(400).send({ error: 'No processable data rows found after filtering.' });
        }
        let processedCount = 0;
        let errorCount = 0;
        // 2. Esegui logica specifica per tipo
        if (importType === 'clients') {
            const result = await processClientImport(rows, hostId);
            processedCount = result.processed;
            errorCount = result.errors;
        }
        else if (importType === 'reservations') {
            const result = await processReservationImport(rows, hostId);
            processedCount = result.processed;
            errorCount = result.errors;
        }
        console.log(`[${hostId}] Import ${importType} completato. Processati: ${processedCount}, Errori: ${errorCount}.`);
        return res.status(200).send({
            message: `Import ${importType} completato.`,
            processed: processedCount,
            errors: errorCount
        });
    }
    catch (error) {
        console.error(`[${hostId}] Errore grave durante import ${importType}:`, error);
        return res.status(500).send({ error: 'Internal Server Error during import process.', details: error.message });
    }
});
/**
 * Processa l'importazione dei clienti.
 */
async function processClientImport(rows, hostId) {
    const batch = firestore.batch();
    let processed = 0;
    let errors = 0;
    const processedEmails = new Set(); // Per gestire duplicati nello stesso CSV
    for (const row of rows) {
        // Aggiungi controllo null/undefined più robusto
        const email = row['Email']?.trim();
        const firstName = row['Nome']?.trim();
        const lastName = row['Cognome']?.trim();
        // Validazione minima
        if (!email || email === '' || !email.includes('@') || (!firstName && !lastName)) {
            console.warn(`[${hostId}] Riga cliente CSV skippata (mancano dati essenziali):`, row);
            errors++;
            continue;
        }
        // Evita di processare lo stesso cliente più volte dallo stesso file
        if (processedEmails.has(email.toLowerCase())) {
            console.log(`[${hostId}] Duplicato email ${email} nel CSV clienti, skippato.`);
            continue;
        }
        try {
            const clientName = `${firstName || ''} ${lastName || ''}`.trim();
            const whatsAppNumber = normalizePhoneNumber(row['Prefisso Cellulare'], row['Cellulare']);
            // Cerca se esiste già un utente con questa email assegnato a questo host
            const usersRef = firestore.collection('users');
            const querySnapshot = await usersRef
                .where('email', '==', email)
                // .where('assignedHostId', '==', hostId) // Rimuoviamo questo per ora, aggiorniamo se esiste
                .where('role', '==', 'client') // Assicuriamoci sia un cliente
                .limit(1)
                .get();
            let userDocRef;
            const userData = {
                email: email,
                name: clientName,
                whatsappPhoneNumber: whatsAppNumber,
                role: 'client',
                assignedHostId: hostId, // Associa sempre a questo host
                // assignedPropertyId: null, // Non impostiamo/sovrascriviamo da qui
                lastUpdatedAt: FieldValue.serverTimestamp(),
                importedFrom: 'csv_scidoo' // Flag opzionale per tracciamento
            };
            if (querySnapshot.empty) {
                // Cliente non trovato -> Crea nuovo documento
                userDocRef = usersRef.doc(); // Genera nuovo ID
                batch.set(userDocRef, {
                    ...userData,
                    assignedPropertyId: null, // Imposta a null per i nuovi
                    createdAt: FieldValue.serverTimestamp()
                });
                console.log(`[${hostId}] Cliente da creare: ${email} (${clientName})`);
            }
            else {
                // Cliente trovato -> Aggiorna (merge)
                userDocRef = querySnapshot.docs[0].ref;
                batch.set(userDocRef, userData, { merge: true }); // Usa merge per non cancellare altri campi come assignedPropertyId se già presente
                console.log(`[${hostId}] Cliente da aggiornare: ${email} (${clientName})`);
            }
            processed++;
            processedEmails.add(email.toLowerCase());
        }
        catch (rowError) {
            console.error(`[${hostId}] Errore processando riga cliente CSV ${email}:`, rowError);
            errors++;
        }
    } // end for loop
    if (processed > 0) {
        try {
            await batch.commit();
            console.log(`[${hostId}] Batch clienti committato con successo (${processed} operazioni).`);
        }
        catch (commitError) {
            console.error(`[${hostId}] Errore commit batch clienti:`, commitError);
            // In caso di errore commit, consideriamo tutte le operazioni fallite
            return { processed: 0, errors: errors + processed };
        }
    }
    return { processed, errors };
}
/**
 * Processa l'importazione delle prenotazioni.
 * Garantisce che ogni prenotazione creata abbia un clientId valido.
 */
async function processReservationImport(rows, hostId) {
    const batch = firestore.batch();
    let processed = 0;
    let errors = 0;
    const clientCache = {};
    const propertyCache = {};
    // 1. Pre-fetch delle proprietà
    try {
        const propsSnapshot = await firestore.collection('users').doc(hostId).collection('properties').get();
        propsSnapshot.forEach(doc => {
            const propData = doc.data();
            if (propData.name) {
                propertyCache[propData.name.toLowerCase().trim()] = doc.id;
            }
        });
        console.log(`[${hostId}] Cache proprietà pre-caricata con ${Object.keys(propertyCache).length} elementi.`);
    }
    catch (e) {
        console.error(`[${hostId}] Impossibile pre-caricare cache proprietà:`, e);
    }
    for (const row of rows) {
        const propertyNameCsv = row['Alloggio']?.trim();
        const clientEmailCsv = row['Email']?.trim();
        const checkinDateStr = row['Checkin']?.trim();
        const checkoutDateStr = row['Checkout']?.trim();
        const clientNameCsv = row['Nome Cliente']?.trim();
        const statusCsv = row['Stato']?.trim();
        // Validazione minima riga prenotazione
        if (!propertyNameCsv || !checkinDateStr || !checkoutDateStr || !clientNameCsv || !statusCsv) {
            console.warn(`[${hostId}] Riga prenotazione CSV skippata (mancano dati essenziali):`, row);
            errors++;
            continue;
        }
        // ---- INIZIO LOGICA PER GARANTIRE clientId ----
        let clientId = null; // Inizializza a null
        let propertyId = null; // Inizializza a null
        try {
            // ---- Gestione Property ID (Lookup / Creazione) ----
            const lowerPropertyName = propertyNameCsv.toLowerCase();
            propertyId = propertyCache[lowerPropertyName] ?? null;
            if (propertyId === null) {
                const propsRef = firestore.collection('users').doc(hostId).collection('properties');
                const querySnapshot = await propsRef.where('name', '==', propertyNameCsv).limit(1).get();
                if (querySnapshot.empty) {
                    const newPropertyRef = propsRef.doc();
                    batch.set(newPropertyRef, {
                        name: propertyNameCsv, createdBy: 'csv_import', createdAt: FieldValue.serverTimestamp()
                    });
                    propertyId = newPropertyRef.id;
                    propertyCache[lowerPropertyName] = propertyId;
                    console.log(`[${hostId}] Proprietà "${propertyNameCsv}" da creare (ID: ${propertyId}).`);
                }
                else {
                    propertyId = querySnapshot.docs[0].id;
                    propertyCache[lowerPropertyName] = propertyId;
                }
            }
            if (!propertyId)
                throw new Error(`Impossibile determinare propertyId per "${propertyNameCsv}"`); // Errore se non si ottiene ID
            // ---- Gestione Client ID (Lookup / Creazione) ----
            if (clientEmailCsv && clientEmailCsv.includes('@')) {
                const lowerEmail = clientEmailCsv.toLowerCase();
                if (clientCache[lowerEmail] !== undefined) {
                    clientId = clientCache[lowerEmail];
                    if (clientId) { // Se trovato in cache (non null)
                        console.log(`[${hostId}] Cliente trovato in cache per prenotazione: ${clientEmailCsv} (ID: ${clientId})`);
                        // Assicura associazione host/proprietà anche se trovato in cache
                        const clientRef = firestore.collection('users').doc(clientId);
                        batch.set(clientRef, {
                            assignedHostId: hostId, assignedPropertyId: propertyId, lastUpdatedAt: FieldValue.serverTimestamp()
                        }, { merge: true });
                    }
                    else {
                        console.log(`[${hostId}] Cliente ${clientEmailCsv} già cercato e non trovato (cache).`);
                        // Non fare nulla, clientId rimane null e la prenotazione verrà skippata sotto
                    }
                }
                else {
                    // Non in cache -> Cerca cliente in Firestore
                    const usersRef = firestore.collection('users');
                    const clientQuery = await usersRef.where('email', '==', clientEmailCsv).where('role', '==', 'client').limit(1).get();
                    if (!clientQuery.empty) { // Cliente Esiste
                        clientId = clientQuery.docs[0].id;
                        clientCache[lowerEmail] = clientId;
                        batch.set(clientQuery.docs[0].ref, {
                            assignedHostId: hostId, assignedPropertyId: propertyId, lastUpdatedAt: FieldValue.serverTimestamp()
                        }, { merge: true });
                        console.log(`[${hostId}] Cliente trovato in DB per prenotazione: ${clientEmailCsv} (ID: ${clientId})`);
                    }
                    else { // Cliente NON Esiste -> Crealo
                        const newClientRef = usersRef.doc();
                        batch.set(newClientRef, {
                            email: clientEmailCsv, name: clientNameCsv, whatsappPhoneNumber: null, role: 'client',
                            assignedHostId: hostId, assignedPropertyId: propertyId,
                            createdAt: FieldValue.serverTimestamp(), importedFrom: 'csv_scidoo_reservation'
                        });
                        clientId = newClientRef.id; // Usa il nuovo ID
                        clientCache[lowerEmail] = clientId;
                        console.log(`[${hostId}] Cliente da creare per prenotazione: ${clientEmailCsv} (ID: ${clientId})`);
                    }
                }
            }
            else {
                // Email non valida o mancante
                console.warn(`[${hostId}] Email cliente mancante o non valida per prenotazione ${clientNameCsv}. Impossibile associare o creare cliente.`);
                // clientId rimane null
            }
            // ---- Controllo Finale e Creazione Prenotazione ----
            if (!clientId) { // Se NON siamo riusciti a ottenere/creare un clientId (es. email mancante)
                console.error(`[${hostId}] IMPOSSIBILE creare prenotazione per ${clientNameCsv} (${propertyNameCsv}) perché manca un clientId valido.`);
                errors++; // Incrementa errore
                continue; // Salta al prossimo ciclo del for
            }
            // Qui siamo sicuri che clientId NON è null
            const startDate = parseDateToTimestamp(checkinDateStr);
            const endDate = parseDateToTimestamp(checkoutDateStr);
            const status = mapReservationStatus(statusCsv);
            if (!startDate || !endDate) {
                console.warn(`[${hostId}] Date non valide per prenotazione ${clientNameCsv}, skip.`);
                errors++;
                continue;
            }
            // Crea il documento prenotazione (ID auto-generato)
            const reservationRef = firestore.collection('reservations').doc();
            batch.set(reservationRef, {
                hostId: hostId,
                propertyId: propertyId,
                propertyName: propertyNameCsv,
                clientId: clientId, // Ora siamo sicuri sia una stringa non nulla
                clientName: clientNameCsv,
                startDate: startDate,
                endDate: endDate,
                status: status,
                createdAt: FieldValue.serverTimestamp(),
                importedFrom: 'csv_scidoo'
            });
            processed++; // Incrementa solo se la prenotazione viene aggiunta al batch
        }
        catch (rowError) {
            console.error(`[${hostId}] Errore processando riga prenotazione CSV (Cliente: ${clientNameCsv}, Alloggio: ${propertyNameCsv}):`, rowError);
            errors++;
        }
    } // end for loop
    if (processed > 0) {
        try {
            console.log(`[${hostId}] Tentativo commit batch prenotazioni con ${processed} prenotazioni e potenziali creazioni/aggiornamenti clienti/proprietà.`);
            await batch.commit();
            console.log(`[${hostId}] Batch prenotazioni committato con successo.`);
        }
        catch (commitError) {
            console.error(`[${hostId}] Errore commit batch prenotazioni:`, commitError);
            console.error(`[${hostId}] Dettagli Errore Commit:`, JSON.stringify(commitError));
            return { processed: 0, errors: errors + processed };
        }
    }
    else {
        console.log(`[${hostId}] Nessuna prenotazione valida da processare nel batch.`);
    }
    return { processed, errors };
}
/**
 * Recupera l'hostId interno (Firebase UID) basato sullo smoobuUserId.
 * Assicurati di aver salvato 'smoobuUserId' nel documento dell'utente host
 * quando l'host collega il suo account Smoobu alla tua piattaforma.
 */
async function getHostIdFromSmoobuUserId(smoobuUserId) {
    console.log(`[SMOOBU_WEBHOOK] Ricerca hostId per smoobuUserId: ${smoobuUserId}`);
    try {
        const usersRef = firestore.collection('users');
        const querySnapshot = await usersRef
            .where('smoobuUserId', '==', smoobuUserId) // Assicurati che questo campo esista nel tuo DB
            .where('role', '==', 'host') // Filtra per ruolo host
            .limit(1)
            .get();
        if (querySnapshot.empty) {
            console.error(`[SMOOBU_WEBHOOK] Host NON TROVATO per smoobuUserId: ${smoobuUserId}. L'host deve collegare il suo account Smoobu.`);
            return null;
        }
        const hostId = querySnapshot.docs[0].id;
        console.log(`[SMOOBU_WEBHOOK] Trovato hostId: ${hostId} per smoobuUserId: ${smoobuUserId}`);
        return hostId;
    }
    catch (error) {
        console.error(`[SMOOBU_WEBHOOK] Errore Firebase durante ricerca host per smoobuUserId ${smoobuUserId}:`, error);
        return null;
    }
}
/**
 * Trova o crea un cliente in Firestore basandosi sui dati Smoobu.
 * Restituisce l'ID del cliente e il nome.
 */
async function findOrCreateClientForSmoobu(details) {
    const { hostId, smoobuGuestId, email, phone, source } = details;
    let { firstName, lastName, guestName } = details;
    // Logica per estrarre nome e cognome se non forniti separatamente
    if ((!firstName || !lastName) && guestName) {
        const nameParts = guestName.split(/\s+/); // Splitta per uno o più spazi
        firstName = nameParts.shift() || '';
        lastName = nameParts.join(' ') || '';
    }
    const finalClientName = `${firstName || ''} ${lastName || ''}`.trim() || guestName?.trim() || (email ? email.split('@')[0] : 'Ospite Sconosciuto');
    if (!email || !email.includes('@')) {
        console.warn(`[SMOOBU_WEBHOOK - ${hostId}] Email cliente non valida o mancante ('${email}') per ${finalClientName}. Non sarà possibile creare/associare un cliente univoco via email.`);
        // Potresti decidere di creare un cliente "placeholder" se l'email non c'è,
        // ma per ora restituiamo null per clientId se l'email non è valida.
        // Questo causerà il fallimento della creazione della prenotazione più avanti se clientId è obbligatorio.
        return { clientId: null, clientName: finalClientName };
    }
    const lowerEmail = email.toLowerCase();
    const usersRef = firestore.collection('users');
    try {
        const clientQuery = await usersRef
            .where('email', '==', lowerEmail)
            .where('role', '==', 'client')
            .limit(1)
            .get();
        const clientDataToStore = {
            email: lowerEmail,
            name: finalClientName,
            whatsappPhoneNumber: normalizePhoneNumber(undefined, phone), // Usa la tua helper esistente
            role: 'client',
            assignedHostId: hostId, // Assicura che sia (ri)associato a questo host
            lastUpdatedAt: FieldValue.serverTimestamp(),
            importedFrom: source,
        };
        if (smoobuGuestId)
            clientDataToStore.smoobuGuestId = smoobuGuestId; // Salva l'ID ospite di Smoobu
        let clientId;
        if (!clientQuery.empty) {
            const clientDoc = clientQuery.docs[0];
            clientId = clientDoc.id;
            await clientDoc.ref.set(clientDataToStore, { merge: true });
            console.log(`[SMOOBU_WEBHOOK - ${hostId}] Cliente '${lowerEmail}' aggiornato (ID: ${clientId})`);
        }
        else {
            const newClientRef = usersRef.doc();
            clientId = newClientRef.id;
            await newClientRef.set({
                ...clientDataToStore,
                // assignedPropertyId: null, // Un nuovo cliente non ha una proprietà assegnata di default
                createdAt: FieldValue.serverTimestamp(),
            });
            console.log(`[SMOOBU_WEBHOOK - ${hostId}] Cliente '${lowerEmail}' creato (ID: ${clientId})`);
        }
        return { clientId, clientName: finalClientName };
    }
    catch (error) {
        console.error(`[SMOOBU_WEBHOOK - ${hostId}] Errore durante findOrCreateClientForSmoobu per ${email}:`, error);
        return { clientId: null, clientName: finalClientName };
    }
}
/**
 * Trova o crea una proprietà in Firestore.
 * Restituisce l'ID della proprietà.
 */
async function findOrCreatePropertyForSmoobu(details) {
    const { hostId, propertyName, smoobuApartmentId, source } = details;
    if (!propertyName || propertyName.trim() === '') {
        console.warn(`[SMOOBU_WEBHOOK - ${hostId}] Nome proprietà mancante, impossibile trovare/creare.`);
        return { propertyId: null, propertyName: 'Proprietà Sconosciuta' };
    }
    const trimmedPropertyName = propertyName.trim();
    const propertiesRef = firestore.collection('users').doc(hostId).collection('properties');
    try {
        // Cerca per nome E smoobuApartmentId se disponibile, altrimenti solo per nome
        let propertyQuery;
        if (smoobuApartmentId) {
            propertyQuery = await propertiesRef
                .where('smoobuApartmentId', '==', smoobuApartmentId)
                .limit(1)
                .get();
        }
        if (!propertyQuery || propertyQuery.empty) { // Se non trovato per ID Smoobu o ID Smoobu non fornito, cerca per nome
            propertyQuery = await propertiesRef
                .where('name', '==', trimmedPropertyName)
                .limit(1)
                .get();
        }
        const propertyDataToStore = {
            name: trimmedPropertyName,
            lastUpdatedAt: FieldValue.serverTimestamp(),
            importedFrom: source, // o aggiorna a source
        };
        if (smoobuApartmentId)
            propertyDataToStore.smoobuApartmentId = smoobuApartmentId; // Salva l'ID appartamento di Smoobu
        let propertyId;
        if (!propertyQuery.empty) {
            const propDoc = propertyQuery.docs[0];
            propertyId = propDoc.id;
            await propDoc.ref.set(propertyDataToStore, { merge: true });
            console.log(`[SMOOBU_WEBHOOK - ${hostId}] Proprietà '${trimmedPropertyName}' aggiornata (ID: ${propertyId})`);
        }
        else {
            const newPropertyRef = propertiesRef.doc();
            propertyId = newPropertyRef.id;
            await newPropertyRef.set({
                ...propertyDataToStore,
                createdAt: FieldValue.serverTimestamp(),
                // Altri campi di default per una nuova proprietà se necessario
            });
            console.log(`[SMOOBU_WEBHOOK - ${hostId}] Proprietà '${trimmedPropertyName}' creata (ID: ${propertyId})`);
        }
        return { propertyId, propertyName: trimmedPropertyName };
    }
    catch (error) {
        console.error(`[SMOOBU_WEBHOOK - ${hostId}] Errore durante findOrCreatePropertyForSmoobu per ${trimmedPropertyName}:`, error);
        return { propertyId: null, propertyName: trimmedPropertyName };
    }
}
/**
 * Processa una singola azione di prenotazione da Smoobu (creazione, aggiornamento).
 */
async function processSmoobuReservationAction(hostId, smoobuReservationData, actionType // Per distinguere il logging o piccole variazioni logiche se necessario
) {
    console.log(`[SMOOBU_WEBHOOK - ${hostId}] Inizio processSmoobuReservationAction (${actionType}) per Smoobu ID: ${smoobuReservationData.id}`);
    // 1. Cliente
    const { clientId, clientName } = await findOrCreateClientForSmoobu({
        hostId,
        smoobuGuestId: smoobuReservationData.guestId,
        email: smoobuReservationData.email,
        firstName: smoobuReservationData.firstname,
        lastName: smoobuReservationData.lastname,
        guestName: smoobuReservationData['guest-name'],
        phone: smoobuReservationData.phone,
        source: 'smoobu_webhook',
    });
    if (!clientId) {
        console.error(`[SMOOBU_WEBHOOK - ${hostId}] IMPOSSIBILE processare prenotazione Smoobu ID ${smoobuReservationData.id} perché manca un clientId valido.`);
        // Potresti voler salvare un log di errore persistente qui
        return; // Interrompi se il cliente non può essere gestito
    }
    // 2. Proprietà
    const { propertyId, propertyName } = await findOrCreatePropertyForSmoobu({
        hostId,
        propertyName: smoobuReservationData.apartment?.name,
        smoobuApartmentId: smoobuReservationData.apartment?.id,
        source: 'smoobu_webhook',
    });
    if (!propertyId) {
        console.error(`[SMOOBU_WEBHOOK - ${hostId}] IMPOSSIBILE processare prenotazione Smoobu ID ${smoobuReservationData.id} perché manca un propertyId valido per '${smoobuReservationData.apartment?.name}'.`);
        return; // Interrompi se la proprietà non può essere gestita
    }
    // 3. Dati Prenotazione
    const startDate = parseDateToTimestamp(smoobuReservationData.arrival); // Usa la tua helper esistente
    const endDate = parseDateToTimestamp(smoobuReservationData.departure); // Usa la tua helper esistente
    if (!startDate || !endDate) {
        console.warn(`[SMOOBU_WEBHOOK - ${hostId}] Date non valide (Arrivo: ${smoobuReservationData.arrival}, Partenza: ${smoobuReservationData.departure}) per prenotazione Smoobu ID ${smoobuReservationData.id}. Skip.`);
        return;
    }
    // Lo stato per una nuova prenotazione o un aggiornamento (non cancellazione) è tipicamente 'confirmed'.
    // Se Smoobu inviasse uno stato più specifico nel payload `data` (oltre a `data.type`), andrebbe mappato qui.
    // Per ora, assumiamo 'confirmed' a meno che l'azione del webhook non sia 'cancelReservation'.
    const reservationStatus = 'confirmed'; // Modifica se Smoobu fornisce uno stato più specifico per le prenotazioni attive/modificate
    const reservationRef = firestore.collection('reservations').doc(`smoobu_${smoobuReservationData.id}`); // ID univoco basato sull'ID Smoobu
    const existingReservationDoc = await reservationRef.get();
    const firestoreReservationPayload = {
        hostId: hostId,
        propertyId: propertyId,
        propertyName: propertyName, // Nome della proprietà come gestito in Firestore
        clientId: clientId,
        clientName: clientName, // Nome del cliente come gestito in Firestore
        startDate: startDate,
        endDate: endDate,
        status: reservationStatus, // Per new/update, sarà 'confirmed'. Per cancel, gestito da altra funzione.
        adults: smoobuReservationData.adults ?? null,
        children: smoobuReservationData.children ?? null,
        notes: smoobuReservationData.notice ?? null,
        totalPrice: smoobuReservationData.price ?? null,
        language: smoobuReservationData.language ?? null,
        isBlockedBooking: smoobuReservationData['is-blocked-booking'] ?? false,
        // Dati specifici Smoobu e Canale
        smoobuReservationId: smoobuReservationData.id,
        numeroConfermaBooking: smoobuReservationData['reference-id'] || null, // CAMPO RICHIESTO!
        smoobuChannelId: smoobuReservationData.channel?.id ?? null,
        smoobuChannelName: smoobuReservationData.channel?.name ?? null,
        smoobuRawPayloadType: smoobuReservationData.type ?? null, // Tipo di payload Smoobu (es. "reservation")
        lastUpdatedAt: FieldValue.serverTimestamp(),
        importedFrom: 'smoobu_webhook', // Identificatore di origine
    };
    if (!existingReservationDoc.exists) {
        firestoreReservationPayload.createdAt = FieldValue.serverTimestamp();
        console.log(`[SMOOBU_WEBHOOK - ${hostId}] Prenotazione Smoobu ID ${smoobuReservationData.id} sarà CREATA.`);
    }
    else {
        console.log(`[SMOOBU_WEBHOOK - ${hostId}] Prenotazione Smoobu ID ${smoobuReservationData.id} sarà AGGIORNATA.`);
    }
    try {
        await reservationRef.set(firestoreReservationPayload, { merge: true }); // merge: true è importante per gli aggiornamenti
        console.log(`[SMOOBU_WEBHOOK - ${hostId}] Prenotazione Smoobu ID ${smoobuReservationData.id} salvata con successo in Firestore.`);
        // Aggiorna l'associazione cliente-proprietà (opzionale, ma può essere utile)
        // Se un cliente fa una prenotazione per una nuova proprietà, potresti volerlo riflettere
        const clientRef = firestore.collection('users').doc(clientId);
        await clientRef.set({
            assignedPropertyId: propertyId, // Aggiorna all'ultima proprietà prenotata
            lastUpdatedAt: FieldValue.serverTimestamp()
        }, { merge: true });
    }
    catch (error) {
        console.error(`[SMOOBU_WEBHOOK - ${hostId}] Errore durante il salvataggio della prenotazione Smoobu ID ${smoobuReservationData.id} in Firestore:`, error);
    }
}
/**
 * Processa l'eliminazione di una prenotazione da Smoobu.
 */
async function processDeleteSmoobuReservation(hostId, smoobuReservationData) {
    console.log(`[SMOOBU_WEBHOOK - ${hostId}] Inizio processDeleteSmoobuReservation per Smoobu ID: ${smoobuReservationData.id}`);
    const reservationRef = firestore.collection('reservations').doc(`smoobu_${smoobuReservationData.id}`);
    const doc = await reservationRef.get();
    if (!doc.exists) {
        console.warn(`[SMOOBU_WEBHOOK - ${hostId}] Tentativo di eliminare prenotazione Smoobu ID ${smoobuReservationData.id} che non esiste in Firestore. Nessuna azione necessaria.`);
        return; // Niente da eliminare
    }
    try {
        await reservationRef.delete();
        console.log(`[SMOOBU_WEBHOOK - ${hostId}] Prenotazione Smoobu ID ${smoobuReservationData.id} ELIMINATA da Firestore.`);
    }
    catch (error) {
        console.error(`[SMOOBU_WEBHOOK - ${hostId}] Errore durante l'eliminazione della prenotazione Smoobu ID ${smoobuReservationData.id}:`, error);
    }
}
/**
 * Processa la cancellazione di una prenotazione da Smoobu.
 */
async function processCancelSmoobuReservation(hostId, smoobuReservationData) {
    console.log(`[SMOOBU_WEBHOOK - ${hostId}] Inizio processCancelSmoobuReservation per Smoobu ID: ${smoobuReservationData.id}`);
    const reservationRef = firestore.collection('reservations').doc(`smoobu_${smoobuReservationData.id}`);
    const doc = await reservationRef.get();
    if (!doc.exists) {
        console.warn(`[SMOOBU_WEBHOOK - ${hostId}] Tentativo di cancellare prenotazione Smoobu ID ${smoobuReservationData.id} (che non esiste in Firestore). Si procede a crearla come cancellata.`);
        // Se la prenotazione non esiste, la creiamo come cancellata.
        // Questo gestisce il caso in cui il primo webhook ricevuto per una prenotazione sia una cancellazione.
        // Dobbiamo comunque ottenere clientId e propertyId.
        const { clientId, clientName } = await findOrCreateClientForSmoobu({
            hostId,
            smoobuGuestId: smoobuReservationData.guestId,
            email: smoobuReservationData.email,
            firstName: smoobuReservationData.firstname,
            lastName: smoobuReservationData.lastname,
            guestName: smoobuReservationData['guest-name'],
            phone: smoobuReservationData.phone,
            source: 'smoobu_webhook_cancelled_creation',
        });
        const { propertyId, propertyName } = await findOrCreatePropertyForSmoobu({
            hostId,
            propertyName: smoobuReservationData.apartment?.name,
            smoobuApartmentId: smoobuReservationData.apartment?.id,
            source: 'smoobu_webhook_cancelled_creation',
        });
        if (!clientId || !propertyId) {
            console.error(`[SMOOBU_WEBHOOK - ${hostId}] Impossibile creare prenotazione cancellata per Smoobu ID ${smoobuReservationData.id} per mancanza di client/property ID.`);
            return;
        }
        const startDate = parseDateToTimestamp(smoobuReservationData.arrival);
        const endDate = parseDateToTimestamp(smoobuReservationData.departure);
        if (!startDate || !endDate) {
            console.warn(`[SMOOBU_WEBHOOK - ${hostId}] Date non valide per creazione prenotazione cancellata Smoobu ID ${smoobuReservationData.id}. Skip.`);
            return;
        }
        const firestoreReservationPayload = {
            hostId: hostId,
            propertyId: propertyId,
            propertyName: propertyName,
            clientId: clientId,
            clientName: clientName,
            startDate: startDate,
            endDate: endDate,
            status: 'cancelled', // Imposta direttamente a cancellato
            adults: smoobuReservationData.adults ?? null,
            children: smoobuReservationData.children ?? null,
            notes: smoobuReservationData.notice ?? null,
            totalPrice: smoobuReservationData.price ?? null,
            language: smoobuReservationData.language ?? null,
            isBlockedBooking: smoobuReservationData['is-blocked-booking'] ?? false,
            smoobuReservationId: smoobuReservationData.id,
            numeroConfermaBooking: smoobuReservationData['reference-id'] || null,
            smoobuChannelId: smoobuReservationData.channel?.id ?? null,
            smoobuChannelName: smoobuReservationData.channel?.name ?? null,
            smoobuRawPayloadType: smoobuReservationData.type ?? null,
            lastUpdatedAt: FieldValue.serverTimestamp(),
            createdAt: FieldValue.serverTimestamp(), // È una nuova creazione nel nostro DB
            importedFrom: 'smoobu_webhook_cancelled_creation',
            cancellationDetails: `Cancellata via webhook Smoobu ${new Date().toISOString()}`,
        };
        try {
            await reservationRef.set(firestoreReservationPayload); // Non merge, è una creazione
            console.log(`[SMOOBU_WEBHOOK - ${hostId}] Prenotazione Smoobu ID ${smoobuReservationData.id} CREATA come CANCELLATA in Firestore.`);
        }
        catch (error) {
            console.error(`[SMOOBU_WEBHOOK - ${hostId}] Errore durante la creazione della prenotazione cancellata Smoobu ID ${smoobuReservationData.id}:`, error);
        }
    }
    else {
        // La prenotazione esiste, aggiorna lo stato a cancellato
        try {
            await reservationRef.update({
                status: 'cancelled',
                lastUpdatedAt: FieldValue.serverTimestamp(),
                cancellationDetails: `Cancellata via webhook Smoobu ${new Date().toISOString()}`, // Aggiungi dettagli sulla cancellazione
                // Potresti voler azzerare/aggiornare altri campi se necessario per una cancellazione
            });
            console.log(`[SMOOBU_WEBHOOK - ${hostId}] Prenotazione Smoobu ID ${smoobuReservationData.id} AGGIORNATA a CANCELLATA in Firestore.`);
        }
        catch (error) {
            console.error(`[SMOOBU_WEBHOOK - ${hostId}] Errore durante l'aggiornamento a cancellata della prenotazione Smoobu ID ${smoobuReservationData.id}:`, error);
        }
    }
}
// --- ENDPOINT PER WEBHOOK SMOOBU ---
// Questo endpoint DEVE essere pubblico o protetto da un meccanismo che Smoobu può usare (es. un token segreto nell'URL).
// La logica di `getHostIdFromSmoobuUserId` è la tua principale "autenticazione" interna.
// --- ENDPOINT PER WEBHOOK SMOOBU ---
app.post('/webhook/smoobu', express_1.default.json(), async (req, res) => {
    const smoobuPayload = req.body;
    const { action, user: smoobuUserId, data: reservationData } = smoobuPayload;
    // Validazione iniziale del payload
    if (!action || typeof smoobuUserId !== 'number' || !reservationData || typeof reservationData.id !== 'number') {
        console.error('[SMOOBU_WEBHOOK] Payload Invalido: mancano action, user, data o data.id.');
        res.status(400).send({ error: 'Invalid payload structure.' });
        return; // Termina qui se il payload base è invalido
    }
    console.log(`[SMOOBU_WEBHOOK] Ricevuta azione '${action}' per smoobuUser ${smoobuUserId}, prenotazione Smoobu ID ${reservationData.id}`);
    // Ottieni l'hostId interno
    const hostId = await getHostIdFromSmoobuUserId(smoobuUserId);
    if (!hostId) {
        // `getHostIdFromSmoobuUserId` logga già l'errore.
        res.status(404).send({ error: `Host configuration not found for Smoobu user ID ${smoobuUserId}. Please link your Smoobu account.` });
        return; // Termina qui se l'host non è trovato/configurato
    }
    // Blocco Try-Catch per la logica di processamento
    try {
        let responseSent = false; // Flag per tracciare se una risposta è già stata inviata
        switch (action.toLowerCase()) {
            case 'newreservation':
                await processSmoobuReservationAction(hostId, reservationData, 'new');
                // Se arriva qui, l'azione è stata processata (o ha lanciato un errore catturato sotto)
                break;
            case 'updatereservation':
                await processSmoobuReservationAction(hostId, reservationData, 'update');
                break;
            case 'cancelreservation':
                await processCancelSmoobuReservation(hostId, reservationData);
                break;
            case 'deletereservation':
                await processDeleteSmoobuReservation(hostId, reservationData);
                break;
            default:
                console.warn(`[SMOOBU_WEBHOOK - ${hostId}] Azione Smoobu non gestita: '${action}'`);
                res.status(200).send({ message: `Action '${action}' received but not actively handled.` });
                responseSent = true; // Indica che abbiamo inviato una risposta
                break;
        }
        // Se una risposta non è stata inviata specificamente da un case dello switch (es. per azioni non gestite o errori specifici)
        // invia la risposta di successo generica.
        if (!responseSent) {
            res.status(200).send({ message: `Webhook action '${action}' processed successfully.` });
        }
    }
    catch (error) {
        console.error(`[SMOOBU_WEBHOOK - ${hostId}] Errore critico durante il processamento del webhook (Azione: ${action}, Smoobu ID: ${reservationData.id}):`, error);
        // Assicurati di inviare una risposta di errore solo se non ne è già stata inviata una
        if (!res.headersSent) {
            res.status(500).send({ error: 'Internal server error while processing webhook.' });
        }
    }
    // Non è necessario un return esplicito qui alla fine della funzione handler di Express
    // se tutti i percorsi inviano una risposta o lanciano un errore che viene catturato e gestito con una risposta.
});
// #############################################################################
// #                    FINE BLOCCO INTEGRAZIONE SMOOBU WEBHOOK                  #
// #############################################################################
// #############################################################################
// #                   INIZIO BLOCCO INTEGRAZIONE SCIDOO API                    #
// #############################################################################
// Import per node-fetch (già installato)
const fetch = require('node-fetch');
// --- Servizio Scidoo ---
class ScidooService {
    constructor() {
        this.baseUrl = 'https://www.scidoo.com/api/v1';
    }
    /**
     * Test connessione con API Key e recupera info account
     */
    async testConnection(apiKey) {
        try {
            console.log('[SCIDOO_SERVICE] Test connessione...');
            const response = await fetch(`${this.baseUrl}/account/getInfo.php`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Api-Key': apiKey
                },
                body: JSON.stringify({})
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const accountInfo = await response.json();
            console.log(`[SCIDOO_SERVICE] Connessione riuscita. Account: ${accountInfo.name} (${accountInfo.email})`);
            console.log(`[SCIDOO_SERVICE] Proprietà trovate: ${accountInfo.properties?.length || 0}`);
            return accountInfo;
        }
        catch (error) {
            console.error('[SCIDOO_SERVICE] Errore test connessione:', error.message);
            if (error.message.includes('401') || error.message.includes('403')) {
                throw new Error('API Key Scidoo non valida o scaduta');
            }
            throw new Error(`Errore connessione Scidoo: ${error.message}`);
        }
    }
    /**
     * Recupera tutte le categorie di alloggio (room types)
     */
    async getRoomTypes(apiKey) {
        try {
            console.log('[SCIDOO_SERVICE] Recupero categorie alloggio...');
            const response = await fetch(`${this.baseUrl}/rooms/getRoomTypes.php`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Api-Key': apiKey
                },
                body: JSON.stringify({})
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const roomTypes = await response.json() || [];
            console.log(`[SCIDOO_SERVICE] Categorie alloggio recuperate: ${roomTypes.length}`);
            return roomTypes;
        }
        catch (error) {
            console.error('[SCIDOO_SERVICE] Errore recupero room types:', error.message);
            throw error;
        }
    }
    /**
     * Recupera prenotazioni - import iniziale o per periodo specifico
     */
    async getReservations(apiKey, params = {}) {
        try {
            console.log('[SCIDOO_SERVICE] Recupero prenotazioni...', params);
            const response = await fetch(`${this.baseUrl}/bookings/get.php`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Api-Key': apiKey
                },
                body: JSON.stringify(params)
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            const reservations = data.reservations || [];
            console.log(`[SCIDOO_SERVICE] Prenotazioni recuperate: ${reservations.length} (totali: ${data.count})`);
            return reservations;
        }
        catch (error) {
            console.error('[SCIDOO_SERVICE] Errore recupero prenotazioni:', error.message);
            throw error;
        }
    }
    /**
     * Recupera solo prenotazioni modificate dall'ultima sincronizzazione
     * Ottimizzazione per polling
     */
    async getModifiedReservations(apiKey) {
        return this.getReservations(apiKey, {
            last_modified: true
        });
    }
    /**
     * Recupera prenotazioni per range di date check-in
     */
    async getReservationsByCheckinRange(apiKey, fromDate, toDate) {
        return this.getReservations(apiKey, {
            checkin_from: fromDate,
            checkin_to: toDate
        });
    }
    /**
     * Utility: converte data in formato YYYY-MM-DD per API Scidoo
     */
    static formatDateForAPI(date) {
        return date.toISOString().split('T')[0];
    }
    /**
     * Utility: calcola data di N giorni fa per import iniziale
     */
    static getDateDaysAgo(days) {
        const date = new Date();
        date.setDate(date.getDate() - days);
        return ScidooService.formatDateForAPI(date);
    }
}
const scidooService = new ScidooService();
// --- Funzioni Helper Scidoo ---
/**
 * Mappa stato Scidoo → stato giovi_ai
 */
function mapScidooStatus(scidooStatus) {
    const statusMap = {
        'opzione': 'pending',
        'attesa_pagamento': 'awaiting_payment',
        'confermata_pagamento': 'confirmed',
        'confermata_carta': 'confirmed',
        'check_in': 'checked_in',
        'saldo': 'confirmed',
        'confermata_manuale': 'confirmed',
        'check_out': 'checked_out',
        'sospesa': 'pending',
        'annullata': 'cancelled',
        'eliminata': 'deleted'
    };
    return statusMap[scidooStatus] || 'unknown';
}
/**
 * Trova o crea un cliente in Firestore basandosi sui dati Scidoo.
 */
async function findOrCreateClientForScidoo(details) {
    const { hostId, scidooGuestId, email, phone, mobile, source } = details;
    let { firstName, lastName } = details;
    const finalClientName = `${firstName || ''} ${lastName || ''}`.trim() || (email ? email.split('@')[0] : 'Ospite Sconosciuto');
    if (!email || !email.includes('@')) {
        console.warn(`[SCIDOO_SERVICE - ${hostId}] Email cliente non valida o mancante ('${email}') per ${finalClientName}. Non sarà possibile creare/associare un cliente univoco via email.`);
        return { clientId: null, clientName: finalClientName };
    }
    const lowerEmail = email.toLowerCase();
    const usersRef = firestore.collection('users');
    try {
        const clientQuery = await usersRef
            .where('email', '==', lowerEmail)
            .where('role', '==', 'client')
            .limit(1)
            .get();
        const phoneNumber = mobile || phone;
        const clientDataToStore = {
            email: lowerEmail,
            name: finalClientName,
            whatsappPhoneNumber: normalizePhoneNumber(undefined, phoneNumber),
            role: 'client',
            assignedHostId: hostId,
            lastUpdatedAt: FieldValue.serverTimestamp(),
            importedFrom: source,
        };
        if (scidooGuestId)
            clientDataToStore.scidooGuestId = scidooGuestId;
        let clientId;
        if (!clientQuery.empty) {
            const clientDoc = clientQuery.docs[0];
            clientId = clientDoc.id;
            await clientDoc.ref.set(clientDataToStore, { merge: true });
            console.log(`[SCIDOO_SERVICE - ${hostId}] Cliente '${lowerEmail}' aggiornato (ID: ${clientId})`);
        }
        else {
            const newClientRef = usersRef.doc();
            clientId = newClientRef.id;
            await newClientRef.set({
                ...clientDataToStore,
                createdAt: FieldValue.serverTimestamp(),
            });
            console.log(`[SCIDOO_SERVICE - ${hostId}] Cliente '${lowerEmail}' creato (ID: ${clientId})`);
        }
        return { clientId, clientName: finalClientName };
    }
    catch (error) {
        console.error(`[SCIDOO_SERVICE - ${hostId}] Errore durante findOrCreateClientForScidoo per ${email}:`, error);
        return { clientId: null, clientName: finalClientName };
    }
}
/**
 * Trova o crea una proprietà in Firestore per Scidoo.
 */
async function findOrCreatePropertyForScidoo(details) {
    const { hostId, roomTypeName, scidooRoomTypeId, source } = details;
    if (!roomTypeName || roomTypeName.trim() === '') {
        console.warn(`[SCIDOO_SERVICE - ${hostId}] Nome room type mancante, impossibile trovare/creare proprietà.`);
        return { propertyId: null, propertyName: 'Proprietà Sconosciuta' };
    }
    const trimmedPropertyName = roomTypeName.trim();
    const propertiesRef = firestore.collection('users').doc(hostId).collection('properties');
    try {
        // Cerca per scidooRoomTypeId se disponibile, altrimenti per nome
        let propertyQuery;
        if (scidooRoomTypeId) {
            propertyQuery = await propertiesRef
                .where('scidooRoomTypeId', '==', scidooRoomTypeId)
                .limit(1)
                .get();
        }
        if (!propertyQuery || propertyQuery.empty) {
            propertyQuery = await propertiesRef
                .where('name', '==', trimmedPropertyName)
                .limit(1)
                .get();
        }
        const propertyDataToStore = {
            name: trimmedPropertyName,
            lastUpdatedAt: FieldValue.serverTimestamp(),
            importedFrom: source,
        };
        if (scidooRoomTypeId)
            propertyDataToStore.scidooRoomTypeId = scidooRoomTypeId;
        let propertyId;
        if (!propertyQuery.empty) {
            const propDoc = propertyQuery.docs[0];
            propertyId = propDoc.id;
            await propDoc.ref.set(propertyDataToStore, { merge: true });
            console.log(`[SCIDOO_SERVICE - ${hostId}] Proprietà '${trimmedPropertyName}' aggiornata (ID: ${propertyId})`);
        }
        else {
            const newPropertyRef = propertiesRef.doc();
            propertyId = newPropertyRef.id;
            await newPropertyRef.set({
                ...propertyDataToStore,
                createdAt: FieldValue.serverTimestamp(),
            });
            console.log(`[SCIDOO_SERVICE - ${hostId}] Proprietà '${trimmedPropertyName}' creata (ID: ${propertyId})`);
        }
        return { propertyId, propertyName: trimmedPropertyName };
    }
    catch (error) {
        console.error(`[SCIDOO_SERVICE - ${hostId}] Errore durante findOrCreatePropertyForScidoo per ${trimmedPropertyName}:`, error);
        return { propertyId: null, propertyName: trimmedPropertyName };
    }
}
/**
 * Processa una prenotazione Scidoo e la salva in Firestore
 */
async function processScidooReservation(hostId, scidooReservation) {
    console.log(`[SCIDOO_SERVICE - ${hostId}] Inizio processamento prenotazione Scidoo ID: ${scidooReservation.internal_id}`);
    // 1. Cliente
    const { clientId, clientName } = await findOrCreateClientForScidoo({
        hostId,
        scidooGuestId: scidooReservation.customer.guest_id,
        email: scidooReservation.customer.email,
        firstName: scidooReservation.customer.first_name,
        lastName: scidooReservation.customer.last_name,
        phone: scidooReservation.customer.phone,
        mobile: scidooReservation.customer.mobile,
        source: 'scidoo_api',
    });
    if (!clientId) {
        console.error(`[SCIDOO_SERVICE - ${hostId}] IMPOSSIBILE processare prenotazione Scidoo ID ${scidooReservation.internal_id} perché manca un clientId valido.`);
        return;
    }
    // 2. Proprietà (basata su room_type_id)
    const { propertyId, propertyName } = await findOrCreatePropertyForScidoo({
        hostId,
        roomTypeName: `Room Type ${scidooReservation.room_type_id}`, // Placeholder, potresti voler fare lookup da getRoomTypes
        scidooRoomTypeId: parseInt(scidooReservation.room_type_id),
        source: 'scidoo_api',
    });
    if (!propertyId) {
        console.error(`[SCIDOO_SERVICE - ${hostId}] IMPOSSIBILE processare prenotazione Scidoo ID ${scidooReservation.internal_id} perché manca un propertyId valido.`);
        return;
    }
    // 3. Dati Prenotazione
    const startDate = parseDateToTimestamp(scidooReservation.checkin_date);
    const endDate = parseDateToTimestamp(scidooReservation.checkout_date);
    if (!startDate || !endDate) {
        console.warn(`[SCIDOO_SERVICE - ${hostId}] Date non valide per prenotazione Scidoo ID ${scidooReservation.internal_id}. Skip.`);
        return;
    }
    const reservationStatus = mapScidooStatus(scidooReservation.status);
    const reservationRef = firestore.collection('reservations').doc(`scidoo_${scidooReservation.internal_id}`);
    const existingReservationDoc = await reservationRef.get();
    const firestoreReservationPayload = {
        hostId: hostId,
        propertyId: propertyId,
        propertyName: propertyName,
        clientId: clientId,
        clientName: clientName,
        startDate: startDate,
        endDate: endDate,
        status: reservationStatus,
        guests: scidooReservation.guest_count || null,
        totalPrice: scidooReservation.extra_price || null,
        // Dati specifici Scidoo
        scidooReservationId: scidooReservation.internal_id,
        scidooExternalId: scidooReservation.id,
        scidooRoomTypeId: scidooReservation.room_type_id,
        scidooOrigin: scidooReservation.origin_name || null,
        scidooStatus: scidooReservation.status,
        lastUpdatedAt: FieldValue.serverTimestamp(),
        importedFrom: 'scidoo_api',
    };
    if (!existingReservationDoc.exists) {
        firestoreReservationPayload.createdAt = FieldValue.serverTimestamp();
        console.log(`[SCIDOO_SERVICE - ${hostId}] Prenotazione Scidoo ID ${scidooReservation.internal_id} sarà CREATA.`);
    }
    else {
        console.log(`[SCIDOO_SERVICE - ${hostId}] Prenotazione Scidoo ID ${scidooReservation.internal_id} sarà AGGIORNATA.`);
    }
    try {
        await reservationRef.set(firestoreReservationPayload, { merge: true });
        console.log(`[SCIDOO_SERVICE - ${hostId}] Prenotazione Scidoo ID ${scidooReservation.internal_id} salvata con successo in Firestore.`);
        // Aggiorna associazione cliente-proprietà
        const clientRef = firestore.collection('users').doc(clientId);
        await clientRef.set({
            assignedPropertyId: propertyId,
            lastUpdatedAt: FieldValue.serverTimestamp()
        }, { merge: true });
    }
    catch (error) {
        console.error(`[SCIDOO_SERVICE - ${hostId}] Errore durante il salvataggio della prenotazione Scidoo ID ${scidooReservation.internal_id} in Firestore:`, error);
    }
}
// --- ENDPOINTS API SCIDOO ---
/**
 * POST /config/scidoo - Configurazione automatica Scidoo
 */
app.post('/config/scidoo', checkAuth, async (req, res) => {
    const hostId = req.user.uid;
    const { apiKey } = req.body;
    if (!apiKey || typeof apiKey !== 'string' || apiKey.trim() === '') {
        return res.status(400).send({ error: 'Bad Request: Missing or empty apiKey.' });
    }
    console.log(`[SCIDOO_CONFIG - ${hostId}] Avvio configurazione con API Key fornita.`);
    try {
        // 1. Test connessione
        const accountInfo = await scidooService.testConnection(apiKey.trim());
        // 2. Import room types (categorie alloggio)
        const roomTypes = await scidooService.getRoomTypes(apiKey.trim());
        // 3. Import prenotazioni recenti (ultimi 30 giorni)
        const fromDate = ScidooService.getDateDaysAgo(30);
        const toDate = ScidooService.formatDateForAPI(new Date());
        const recentReservations = await scidooService.getReservationsByCheckinRange(apiKey.trim(), fromDate, toDate);
        // 4. Salva configurazione nel profilo host
        const hostRef = firestore.collection('users').doc(hostId);
        await hostRef.set({
            scidooApiKey: apiKey.trim(),
            scidooAccountId: accountInfo.account_id,
            scidooAccountName: accountInfo.name,
            scidooAccountEmail: accountInfo.email,
            scidooConfiguredAt: FieldValue.serverTimestamp(),
            scidooSyncStats: {
                totalRoomTypes: roomTypes.length,
                totalRecentReservations: recentReservations.length,
                lastSyncAt: FieldValue.serverTimestamp()
            }
        }, { merge: true });
        // 5. Processa room types (crea proprietà)
        let roomTypesProcessed = 0;
        for (const roomType of roomTypes) {
            try {
                await findOrCreatePropertyForScidoo({
                    hostId,
                    roomTypeName: roomType.name,
                    scidooRoomTypeId: roomType.id,
                    source: 'scidoo_config'
                });
                roomTypesProcessed++;
            }
            catch (error) {
                console.error(`[SCIDOO_CONFIG - ${hostId}] Errore processando room type ${roomType.name}:`, error);
            }
        }
        // 6. Processa prenotazioni recenti
        let reservationsProcessed = 0;
        for (const reservation of recentReservations) {
            try {
                await processScidooReservation(hostId, reservation);
                reservationsProcessed++;
            }
            catch (error) {
                console.error(`[SCIDOO_CONFIG - ${hostId}] Errore processando prenotazione ${reservation.internal_id}:`, error);
            }
        }
        console.log(`[SCIDOO_CONFIG - ${hostId}] Configurazione completata. Room types: ${roomTypesProcessed}, Prenotazioni: ${reservationsProcessed}`);
        return res.status(200).send({
            configured: true,
            message: 'Configurazione Scidoo completata con successo',
            account: {
                userId: accountInfo.account_id,
                name: accountInfo.name,
                email: accountInfo.email
            },
            propertiesSync: {
                total: roomTypes.length,
                synced: roomTypesProcessed,
                errors: roomTypes.length - roomTypesProcessed
            },
            imported: {
                roomTypes: roomTypesProcessed,
                recentReservations: reservationsProcessed
            }
        });
    }
    catch (error) {
        console.error(`[SCIDOO_CONFIG - ${hostId}] Errore durante configurazione:`, error);
        return res.status(500).send({
            error: 'Errore durante configurazione Scidoo',
            details: error.message
        });
    }
});
/**
 * POST /config/scidoo/test - Test connessione Scidoo senza salvare
 */
app.post('/config/scidoo/test', checkAuth, async (req, res) => {
    const hostId = req.user.uid;
    const { scidooApiKey } = req.body;
    if (!scidooApiKey || typeof scidooApiKey !== 'string' || scidooApiKey.trim() === '') {
        return res.status(400).send({ error: 'Bad Request: Missing or empty scidooApiKey.' });
    }
    console.log(`[SCIDOO_TEST - ${hostId}] Test connessione senza salvare.`);
    try {
        // 1. Test connessione
        const accountInfo = await scidooService.testConnection(scidooApiKey.trim());
        // 2. Test room types
        const roomTypes = await scidooService.getRoomTypes(scidooApiKey.trim());
        return res.status(200).send({
            success: true,
            message: 'Test connessione Scidoo riuscito',
            account: {
                userId: accountInfo.account_id,
                name: accountInfo.name,
                email: accountInfo.email
            },
            properties: {
                count: roomTypes.length,
                list: roomTypes.slice(0, 10).map(rt => ({
                    id: rt.id.toString(),
                    name: rt.name
                }))
            }
        });
    }
    catch (error) {
        console.error(`[SCIDOO_TEST - ${hostId}] Errore durante test:`, error);
        return res.status(500).send({
            success: false,
            message: 'Test connessione Scidoo fallito',
            error: error.message
        });
    }
});
/**
 * GET /config/scidoo/status - Stato configurazione Scidoo
 */
app.get('/config/scidoo/status', checkAuth, async (req, res) => {
    const hostId = req.user.uid;
    try {
        const hostDoc = await firestore.collection('users').doc(hostId).get();
        const hostData = hostDoc.data();
        if (!hostData || !hostData.scidooApiKey) {
            return res.status(404).send({
                configured: false,
                message: 'Scidoo non configurato per questo host'
            });
        }
        return res.status(200).send({
            configured: true,
            configuredAt: hostData.scidooConfiguredAt || null,
            scidooUserId: hostData.scidooAccountId,
            scidooUserName: hostData.scidooAccountName,
            scidooUserEmail: hostData.scidooAccountEmail,
            syncStats: {
                lastSyncAt: hostData.scidooSyncStats?.lastSyncAt || null,
                propertiesCount: hostData.scidooSyncStats?.totalRoomTypes || 0,
                propertiesSynced: hostData.scidooSyncStats?.totalRoomTypes || 0,
                syncErrors: 0
            }
        });
    }
    catch (error) {
        console.error(`[SCIDOO_STATUS - ${hostId}] Errore:`, error);
        return res.status(500).send({ error: 'Errore recupero stato Scidoo' });
    }
});
/**
 * POST /config/scidoo/sync-properties - Sincronizzazione proprietà
 */
app.post('/config/scidoo/sync-properties', checkAuth, async (req, res) => {
    const hostId = req.user.uid;
    try {
        const hostDoc = await firestore.collection('users').doc(hostId).get();
        const hostData = hostDoc.data();
        if (!hostData || !hostData.scidooApiKey) {
            return res.status(404).send({
                error: 'Scidoo non configurato per questo host'
            });
        }
        // Sincronizza room types (proprietà)
        const roomTypes = await scidooService.getRoomTypes(hostData.scidooApiKey);
        let processed = 0;
        for (const roomType of roomTypes) {
            try {
                await findOrCreatePropertyForScidoo({
                    hostId,
                    roomTypeName: roomType.name,
                    scidooRoomTypeId: roomType.id,
                    source: 'scidoo_sync_properties'
                });
                processed++;
            }
            catch (error) {
                console.error(`[SCIDOO_SYNC_PROPS - ${hostId}] Errore processando room type ${roomType.name}:`, error);
            }
        }
        // Aggiorna stats
        await firestore.collection('users').doc(hostId).set({
            'scidooSyncStats.totalRoomTypes': roomTypes.length,
            'scidooSyncStats.lastSyncAt': FieldValue.serverTimestamp(),
        }, { merge: true });
        return res.status(200).send({
            total: roomTypes.length,
            synced: processed,
            errors: roomTypes.length - processed
        });
    }
    catch (error) {
        console.error(`[SCIDOO_SYNC_PROPS - ${hostId}] Errore durante sincronizzazione proprietà:`, error);
        return res.status(500).send({
            error: 'Errore durante sincronizzazione proprietà Scidoo',
            details: error.message
        });
    }
});
/**
 * POST /config/scidoo/sync-now - Sincronizzazione manuale immediata
 */
app.post('/config/scidoo/sync-now', checkAuth, async (req, res) => {
    const hostId = req.user.uid;
    try {
        const hostDoc = await firestore.collection('users').doc(hostId).get();
        const hostData = hostDoc.data();
        if (!hostData || !hostData.scidooApiKey) {
            return res.status(404).send({
                error: 'Scidoo non configurato per questo host'
            });
        }
        // Sincronizza prenotazioni modificate
        const modifiedReservations = await scidooService.getModifiedReservations(hostData.scidooApiKey);
        let processed = 0;
        for (const reservation of modifiedReservations) {
            try {
                await processScidooReservation(hostId, reservation);
                processed++;
            }
            catch (error) {
                console.error(`[SCIDOO_SYNC - ${hostId}] Errore processando prenotazione ${reservation.internal_id}:`, error);
            }
        }
        // Aggiorna timestamp ultima sincronizzazione
        await firestore.collection('users').doc(hostId).set({
            'scidooSyncStats.lastSyncAt': FieldValue.serverTimestamp(),
            'scidooSyncStats.lastManualSyncAt': FieldValue.serverTimestamp(),
            'scidooSyncStats.lastSyncReservations': processed
        }, { merge: true });
        return res.status(200).send({
            message: 'Sincronizzazione Scidoo completata',
            processed: processed,
            found: modifiedReservations.length
        });
    }
    catch (error) {
        console.error(`[SCIDOO_SYNC - ${hostId}] Errore durante sincronizzazione:`, error);
        return res.status(500).send({
            error: 'Errore durante sincronizzazione Scidoo',
            details: error.message
        });
    }
});
// #############################################################################
// #                     FINE BLOCCO INTEGRAZIONE SCIDOO API                    #
// #############################################################################
// --- Avvio Server Express ---
app.listen(PORT, () => {
    console.log(`pms-sync-service listening on port ${PORT}`);
});
// --- Gestione Errori Globali (opzionale ma consigliato) ---
process.on('uncaughtException', (err, origin) => { console.error(`[FATAL] UNCAUGHT EXCEPTION! Origin: ${origin}`, err); });
process.on('unhandledRejection', (reason, promise) => { console.error('[FATAL] UNHANDLED REJECTION!', reason); });
//# sourceMappingURL=server.js.map