const functions = require("firebase-functions");
const admin = require("firebase-admin");
const { Storage } = require('@google-cloud/storage');

admin.initializeApp();
const storage = new Storage();

// ----- CONFIGURAZIONE (Legge da Firebase Functions Config) -----
const functionsConfig = functions.config();

// Leggi i valori dalla configurazione, fornendo dei default se non trovati
// o loggando errori se sono assolutamente necessari.
const GCS_BUCKET_NAME = functionsConfig.gcs?.bucket_name; // L'operatore ?. evita errori se 'gcs' non esiste
const GCS_FOLDER_PATH = functionsConfig.gcs?.folder_path || 'properties_export';
const GCP_REGION = functionsConfig.gcp?.region || 'europe-west1';

// Controllo critico per il nome del bucket
if (!GCS_BUCKET_NAME) {
    functions.logger.error("ERRORE CRITICO: La variabile di configurazione 'gcs.bucket_name' non è definita! Esegui 'firebase functions:config:set gcs.bucket_name=NOME_BUCKET'");
}
// Log di avviso se gli altri usano i default (opzionale, ma utile per il debug)
if (!functionsConfig.gcs?.folder_path) {
    functions.logger.warn(`ATTENZIONE: 'gcs.folder_path' non definito in config, uso default: '${GCS_FOLDER_PATH}'`);
}
if (!functionsConfig.gcp?.region) {
    functions.logger.warn(`ATTENZIONE: 'gcp.region' non definito in config, uso default: '${GCP_REGION}'`);
}

// Funzione per formattare i dati della proprietà in testo semplice
function formatPropertyDataAsText(propertyId, hostId, data) {
    let textContent = `Document ID (Property ID): ${propertyId}\n`;
    textContent += `Host ID: ${hostId}\n`;

    if (data.name) textContent += `Nome Alloggio: ${data.name}\n`;
    if (data.address) textContent += `Indirizzo: ${data.address}\n`;
    if (data.accessCode) textContent += `Codice Accesso: ${data.accessCode}\n`;
    if (data.accessInstructions) textContent += `Istruzioni Accesso: ${data.accessInstructions}\n`;
    if (data.luggageDropOffInstructions) textContent += `Istruzioni Deposito Bagagli: ${data.luggageDropOffInstructions}\n`;
    
    textContent += `Permesso Early Check-in: ${data.allowEarlyCheckin ? 'Sì' : (data.allowEarlyCheckin === false ? 'No' : 'Non specificato')}\n`;
    textContent += `Permesso Late Check-out: ${data.allowLateCheckout ? 'Sì' : (data.allowLateCheckout === false ? 'No' : 'Non specificato')}\n`;
    textContent += `Orario Check-in: ${data.checkInTime || 'Non specificato'}\n`;
    textContent += `Orario Check-out: ${data.checkOutTime || 'Non specificato'}\n`;
    
    textContent += `Parcheggio Disponibile: ${data.parkingAvailable ? 'Sì' : (data.parkingAvailable === false ? 'No' : 'Non specificato')}\n`;
    if (data.parkingAvailable) {
        if (data.parkingCost) textContent += `Costo Parcheggio: ${data.parkingCost}\n`;
        if (data.parkingDistance) textContent += `Distanza Parcheggio: ${data.parkingDistance}\n`;
    }

    if (data.propertyType) textContent += `Tipo Proprietà: ${data.propertyType}\n`;
    if (typeof data.rooms === 'number') textContent += `Numero Stanze: ${data.rooms}\n`;
    if (typeof data.bathrooms === 'number') textContent += `Numero Bagni: ${data.bathrooms}\n`;

    data.items?.forEach(item => {
        textContent += `Oggetto presente: ${item.name || 'N/D'}. Posizione: ${item.location || 'N/D'}.\n`;
    });
    data.instructions?.forEach(instr => {
        textContent += `Istruzioni per l'utilizzo di '${instr.item || 'N/D'}': ${instr.instruction || 'N/D'}.\n`;
    });
    data.areaServices?.forEach(service => {
        textContent += `Servizio nelle vicinanze (${service.type || 'N/D'}): ${service.name || 'N/D'}. Dettagli: ${service.notes || 'N/D'}.\n`;
    });
    data.contacts?.forEach(contact => {
        textContent += `Contatto di riferimento (${contact.type || 'N/D'}): ${contact.name || 'N/D'}. Telefono: ${contact.phone || 'N/D'}. Note: ${contact.description || 'N/D'}.\n`;
    });
    
    return textContent;
}

exports.exportPropertyToGCS = functions
    .region(GCP_REGION) // Usa la variabile letta dalla config o il default
    .firestore
    .document('users/{hostId}/properties/{propertyId}')
    .onWrite(async (change, context) => {
        const { hostId, propertyId } = context.params;

        if (!GCS_BUCKET_NAME) {
            functions.logger.error("Nome del bucket GCS non configurato (letto da functions.config). Impossibile procedere con l'export.");
            return null;
        }
        const safeFolderPath = GCS_FOLDER_PATH.replace(/\/$/, '');

        if (!change.after.exists) {
            const filePath = `${safeFolderPath}/${propertyId}.txt`;
            functions.logger.info(`[${propertyId}] Proprietà cancellata. Tento di cancellare ${filePath} da GCS.`);
            try {
                await storage.bucket(GCS_BUCKET_NAME).file(filePath).delete();
                functions.logger.info(`[${propertyId}] File ${filePath} cancellato da GCS.`);
            } catch (error) {
                if (error.code === 404) {
                    functions.logger.info(`[${propertyId}] File ${filePath} non trovato in GCS, nessuna azione.`);
                } else {
                    functions.logger.error(`[${propertyId}] Errore cancellazione file ${filePath} da GCS:`, error);
                }
            }
            return null;
        }

        const propertyData = change.after.data();
        if (!propertyData) {
            functions.logger.warn(`[${propertyId}] Nessun dato per la proprietà.`);
            return null;
        }

        functions.logger.info(`[${propertyId}] Proprietà creata/aggiornata. Esporto in GCS...`);
        const fileContent = formatPropertyDataAsText(propertyId, hostId, propertyData);
        
        if (!fileContent || fileContent.trim() === "") {
            functions.logger.warn(`[${propertyId}] Contenuto file vuoto, non scrivo in GCS.`);
            return null;
        }

        const filePath = `${safeFolderPath}/${propertyId}.txt`;
        const file = storage.bucket(GCS_BUCKET_NAME).file(filePath);

        try {
            await file.save(fileContent, { contentType: 'text/plain; charset=utf-8' });
            functions.logger.info(`[${propertyId}] Dati esportati in gs://${GCS_BUCKET_NAME}/${filePath}`);
        } catch (error) {
            functions.logger.error(`[${propertyId}] Errore salvataggio file in GCS (gs://${GCS_BUCKET_NAME}/${filePath}):`, error);
        }
        return null;
    });

// ----- NUOVA FUNZIONE HTTP PER ESPORTARE TUTTE LE PROPRIETÀ -----
exports.exportAllPropertiesToGCS = functions
    .region(GCP_REGION)
    .https
    .onRequest(async (req, res) => {
        functions.logger.info("=== INIZIO EXPORT COMPLETO DI TUTTE LE PROPRIETÀ ===");

        if (!GCS_BUCKET_NAME) {
            const errorMsg = "Nome del bucket GCS non configurato. Impossibile procedere.";
            functions.logger.error(errorMsg);
            return res.status(500).json({ error: errorMsg });
        }

        const safeFolderPath = GCS_FOLDER_PATH.replace(/\/$/, '');
        let totalProperties = 0;
        let exportedProperties = 0;
        let errors = [];

        try {
            // Ottieni tutti gli host
            const usersSnapshot = await admin.firestore().collection('users').get();
            
            for (const userDoc of usersSnapshot.docs) {
                const hostId = userDoc.id;
                const userData = userDoc.data();
                
                // Salta se non è un host o non ha proprietà
                if (userData.role !== 'host') {
                    continue;
                }

                functions.logger.info(`Processando host: ${hostId}`);

                // Ottieni tutte le proprietà di questo host
                const propertiesSnapshot = await admin.firestore()
                    .collection('users')
                    .doc(hostId)
                    .collection('properties')
                    .get();

                for (const propertyDoc of propertiesSnapshot.docs) {
                    totalProperties++;
                    const propertyId = propertyDoc.id;
                    const propertyData = propertyDoc.data();

                    try {
                        functions.logger.info(`[${propertyId}] Esportando proprietà per host ${hostId}...`);
                        
                        const fileContent = formatPropertyDataAsText(propertyId, hostId, propertyData);
                        
                        if (!fileContent || fileContent.trim() === "") {
                            functions.logger.warn(`[${propertyId}] Contenuto vuoto, salto.`);
                            continue;
                        }

                        const filePath = `${safeFolderPath}/${propertyId}.txt`;
                        const file = storage.bucket(GCS_BUCKET_NAME).file(filePath);

                        await file.save(fileContent, { contentType: 'text/plain; charset=utf-8' });
                        exportedProperties++;
                        
                        functions.logger.info(`[${propertyId}] ✅ Esportata in gs://${GCS_BUCKET_NAME}/${filePath}`);
                        
                    } catch (error) {
                        const errorMsg = `Errore esportazione proprietà ${propertyId}: ${error.message}`;
                        functions.logger.error(errorMsg);
                        errors.push(errorMsg);
                    }
                }
            }

            const result = {
                success: true,
                totalProperties,
                exportedProperties,
                errors: errors.length > 0 ? errors : null,
                bucketInfo: {
                    bucket: GCS_BUCKET_NAME,
                    folder: safeFolderPath
                }
            };

            functions.logger.info(`=== EXPORT COMPLETATO: ${exportedProperties}/${totalProperties} proprietà esportate ===`);
            res.status(200).json(result);

        } catch (error) {
            const errorMsg = `Errore durante l'export completo: ${error.message}`;
            functions.logger.error(errorMsg);
            res.status(500).json({ 
                success: false, 
                error: errorMsg,
                totalProperties,
                exportedProperties,
                errors
            });
        }
    });