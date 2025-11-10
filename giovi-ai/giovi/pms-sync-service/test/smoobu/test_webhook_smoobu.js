// Script per testare il webhook endpoint Smoobu
const fetch = require('node-fetch'); // Aggiungi questo import
const PMS_SYNC_SERVICE_URL = 'http://localhost:8080'; // URL del tuo pms-sync-service
const SMOOBU_USER_ID = 1306068; // Il tuo smoobuUserId che hai recuperato dal script precedente

// Payload di test per nuovo webhook di prenotazione
const newReservationPayload = {
    action: 'newReservation',
    user: SMOOBU_USER_ID,
    data: {
        id: 12345,
        'reference-id': 'TEST_BOOKING_001',
        type: 'reservation',
        arrival: '2024-03-15',
        departure: '2024-03-18',
        'created-at': '2024-01-15 10:30',
        'modifiedAt': '2024-01-15 10:30',
        apartment: {
            id: 101,
            name: 'Appartamento Test Roma'
        },
        channel: {
            id: 13,
            name: 'Direct booking'
        },
        'guest-name': 'Mario Rossi',
        firstname: 'Mario',
        lastname: 'Rossi',
        email: 'mario.rossi@test.com',
        phone: '+39 333 1234567',
        adults: 2,
        children: 1,
        'check-in': '15:00',
        'check-out': '11:00',
        notice: 'Test booking via webhook',
        price: 450.00,
        'price-paid': 'No',
        prepayment: 150.00,
        'prepayment-paid': 'Yes',
        deposit: 100.00,
        'deposit-paid': 'No',
        language: 'it',
        'guest-app-url': 'https://guest.smoobu.com/?t=test123&b=12345',
        'is-blocked-booking': false,
        guestId: 9876
    }
};

// Payload di test per aggiornamento prenotazione
const updateReservationPayload = {
    action: 'updateReservation',
    user: SMOOBU_USER_ID,
    data: {
        ...newReservationPayload.data,
        id: 12345,
        'reference-id': 'TEST_BOOKING_001_UPD',
        type: 'modification of booking',
        adults: 3, // Modificato da 2 a 3
        price: 550.00, // Prezzo aggiornato
        'modifiedAt': '2024-01-15 14:45'
    }
};

// Payload di test per cancellazione prenotazione
const cancelReservationPayload = {
    action: 'cancelReservation',
    user: SMOOBU_USER_ID,
    data: {
        ...newReservationPayload.data,
        id: 12345,
        type: 'cancellation'
    }
};

async function testWebhook(payload, testName) {
    try {
        console.log(`\n🔄 Testing ${testName}...`);
        console.log('📤 Payload:', JSON.stringify(payload, null, 2));
        
        const response = await fetch(`${PMS_SYNC_SERVICE_URL}/webhook/smoobu`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });

        console.log(`📥 Response Status: ${response.status} ${response.statusText}`);
        
        const responseData = await response.text();
        console.log('📄 Response Body:', responseData);
        
        if (response.ok) {
            console.log(`✅ ${testName} - SUCCESS`);
        } else {
            console.log(`❌ ${testName} - FAILED`);
        }
        
        return response.ok;
    } catch (error) {
        console.error(`❌ ${testName} - ERROR:`, error.message);
        return false;
    }
}

async function runWebhookTests() {
    console.log('🚀 Starting Smoobu Webhook Tests...');
    console.log(`🎯 Target URL: ${PMS_SYNC_SERVICE_URL}/webhook/smoobu`);
    console.log(`👤 Smoobu User ID: ${SMOOBU_USER_ID}`);
    console.log('\n⚠️  ASSICURATI CHE:');
    console.log('   1. Il pms-sync-service sia in esecuzione (npm start nella cartella pms-sync-service)');
    console.log(`   2. L'host abbia smoobuUserId: ${SMOOBU_USER_ID} nel documento Firebase`);
    console.log('   3. Firebase sia configurato correttamente\n');
    
    // Test 1: Nuova prenotazione
    const test1 = await testWebhook(newReservationPayload, 'NEW RESERVATION');
    
    // Aspetta un po' prima del prossimo test
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Test 2: Aggiornamento prenotazione  
    const test2 = await testWebhook(updateReservationPayload, 'UPDATE RESERVATION');
    
    // Aspetta un po' prima del prossimo test
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Test 3: Cancellazione prenotazione
    const test3 = await testWebhook(cancelReservationPayload, 'CANCEL RESERVATION');
    
    console.log('\n📊 RISULTATI TEST:');
    console.log(`   Nuova prenotazione: ${test1 ? '✅ OK' : '❌ FAILED'}`);
    console.log(`   Aggiornamento: ${test2 ? '✅ OK' : '❌ FAILED'}`);
    console.log(`   Cancellazione: ${test3 ? '✅ OK' : '❌ FAILED'}`);
    
    if (test1 && test2 && test3) {
        console.log('\n🎉 TUTTI I TEST SONO PASSATI! L\'integrazione Smoobu funziona correttamente.');
        console.log('\n🔍 Controlla il database Firebase per vedere:');
        console.log('   - Nuovo cliente: mario.rossi@test.com');
        console.log('   - Nuova proprietà: Appartamento Test Roma');
        console.log('   - Prenotazione: smoobu_12345');
    } else {
        console.log('\n⚠️  Alcuni test sono falliti. Controlla i log del server.');
    }
}

// Esegui i test
runWebhookTests(); 