// Test script per gli endpoint di configurazione Smoobu
const fetch = require('node-fetch');

const PMS_SYNC_SERVICE_URL = 'http://localhost:8080';
const SMOOBU_API_KEY = 'LA_TUA_API_KEY_QUI'; // Sostituisci con la tua API key vera
const AUTH_TOKEN = 'IL_TUO_JWT_TOKEN'; // Token Firebase dell'host

async function testConfigEndpoints() {
    console.log('🚀 Testando Endpoint di Configurazione Smoobu...\n');

    // Test 1: Test connessione senza salvare
    console.log('🔧 Test 1: Test connessione API Key...');
    try {
        const response = await fetch(`${PMS_SYNC_SERVICE_URL}/config/smoobu/test`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${AUTH_TOKEN}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                smoobuApiKey: SMOOBU_API_KEY
            })
        });

        const result = await response.json();
        if (response.ok) {
            console.log('✅ Test connessione riuscito!');
            console.log(`   Account: ${result.account.name} (${result.account.email})`);
            console.log(`   Proprietà trovate: ${result.properties.count}`);
            console.log('   Proprietà:', result.properties.list.map(p => p.name).join(', '));
        } else {
            console.log('❌ Test connessione fallito:', result.error);
        }
    } catch (error) {
        console.log('❌ Errore durante test:', error.message);
    }

    console.log('\n' + '='.repeat(50) + '\n');

    // Test 2: Configurazione completa
    console.log('🔧 Test 2: Configurazione completa con sincronizzazione...');
    try {
        const response = await fetch(`${PMS_SYNC_SERVICE_URL}/config/smoobu`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${AUTH_TOKEN}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                smoobuApiKey: SMOOBU_API_KEY,
                testConnection: true,
                syncProperties: true
            })
        });

        const result = await response.json();
        if (response.ok) {
            console.log('✅ Configurazione completata!');
            console.log(`   Account Smoobu: ${result.smoobuAccount.name}`);
            console.log(`   User ID: ${result.smoobuAccount.userId}`);
            console.log(`   Proprietà sincronizzate: ${result.propertiesSync.synced}/${result.propertiesSync.total}`);
            console.log(`   Webhook URL: ${result.webhookUrl}`);
            console.log('\n📋 COPIA QUESTO URL IN SMOOBU:');
            console.log(`   ${result.webhookUrl}`);
        } else {
            console.log('❌ Configurazione fallita:', result.error);
        }
    } catch (error) {
        console.log('❌ Errore durante configurazione:', error.message);
    }

    console.log('\n' + '='.repeat(50) + '\n');

    // Test 3: Stato integrazione
    console.log('🔧 Test 3: Controllo stato integrazione...');
    try {
        const response = await fetch(`${PMS_SYNC_SERVICE_URL}/config/smoobu/status`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${AUTH_TOKEN}`
            }
        });

        const result = await response.json();
        if (response.ok) {
            console.log('✅ Stato recuperato!');
            console.log(`   Configurata: ${result.configured ? 'SÌ' : 'NO'}`);
            if (result.configured) {
                console.log(`   User Smoobu: ${result.smoobuUserName} (ID: ${result.smoobuUserId})`);
                console.log(`   Configurata il: ${new Date(result.configuredAt.seconds * 1000).toLocaleString()}`);
                if (result.syncStats) {
                    console.log(`   Ultima sync: ${new Date(result.syncStats.lastSyncAt.seconds * 1000).toLocaleString()}`);
                    console.log(`   Proprietà: ${result.syncStats.propertiesSynced}/${result.syncStats.propertiesCount}`);
                }
            }
        } else {
            console.log('❌ Errore recuperando stato:', result.error);
        }
    } catch (error) {
        console.log('❌ Errore durante controllo stato:', error.message);
    }

    console.log('\n' + '='.repeat(50) + '\n');

    // Test 4: Sincronizzazione manuale proprietà
    console.log('🔧 Test 4: Sincronizzazione manuale proprietà...');
    try {
        const response = await fetch(`${PMS_SYNC_SERVICE_URL}/config/smoobu/sync-properties`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${AUTH_TOKEN}`,
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();
        if (response.ok) {
            console.log('✅ Sincronizzazione completata!');
            console.log(`   Proprietà totali: ${result.total}`);
            console.log(`   Proprietà sincronizzate: ${result.synced}`);
            console.log(`   Errori: ${result.errors}`);
        } else {
            console.log('❌ Sincronizzazione fallita:', result.error);
        }
    } catch (error) {
        console.log('❌ Errore durante sincronizzazione:', error.message);
    }

    console.log('\n🎉 Test completati!\n');
    console.log('📝 ISTRUZIONI FINALI:');
    console.log('1. Copia l\'URL webhook mostrato sopra');
    console.log('2. Vai nelle impostazioni Smoobu > Developer > Webhooks');
    console.log('3. Incolla l\'URL e abilita i webhook per: newReservation, updateReservation, cancelReservation');
    console.log('4. Testa creando/modificando una prenotazione in Smoobu');
}

// Esegui i test solo se questo file viene eseguito direttamente
if (require.main === module) {
    testConfigEndpoints().catch(console.error);
}

module.exports = { testConfigEndpoints }; 