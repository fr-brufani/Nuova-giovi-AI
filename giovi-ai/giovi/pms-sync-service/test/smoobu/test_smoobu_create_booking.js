// Script per creare prenotazioni di test via API Smoobu
const fetch = require('node-fetch');

const SMOOBU_API_KEY = 'LA_TUA_API_KEY_QUI'; // Sostituisci con la tua API key
const APARTMENT_ID = 1; // ID dell'appartamento (ottienilo dal test_smoobu_user.js)

// Payload per creare una prenotazione di test
const testBookingData = {
    arrivalDate: '2024-03-20',
    departureDate: '2024-03-23',
    channelId: 13, // Direct booking
    apartmentId: APARTMENT_ID,
    arrivalTime: '15:00',
    departureTime: '11:00',
    firstName: 'Giuseppe',
    lastName: 'Verdi',
    email: 'giuseppe.verdi@test.it',
    phone: '+39 338 9876543',
    notice: 'Prenotazione test creata via API per testare webhook',
    adults: 2,
    children: 0,
    price: 380.00,
    priceStatus: 0, // 0 = non pagato, 1 = pagato
    prepayment: 100.00,
    prepaymentStatus: 1, // prepagato
    deposit: 50.00,
    depositStatus: 0, // deposito non pagato
    language: 'it'
};

async function createTestBooking() {
    try {
        console.log('🚀 Creazione prenotazione di test via API Smoobu...\n');
        console.log('📋 Dati prenotazione:');
        console.log(JSON.stringify(testBookingData, null, 2));

        const response = await fetch('https://login.smoobu.com/api/reservations', {
            method: 'POST',
            headers: {
                'Api-Key': SMOOBU_API_KEY,
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            },
            body: JSON.stringify(testBookingData)
        });

        console.log(`\n📥 Response Status: ${response.status} ${response.statusText}`);
        
        if (response.ok) {
            const result = await response.json();
            console.log('📄 Response:', JSON.stringify(result, null, 2));
            
            if (result.id) {
                console.log(`\n✅ Prenotazione creata con successo!`);
                console.log(`📝 ID Prenotazione Smoobu: ${result.id}`);
                console.log('\n🔔 Ora dovresti vedere:');
                console.log('1. Un webhook "newReservation" arrivare al tuo pms-sync-service');
                console.log('2. Nei log del server il processing della prenotazione');
                console.log('3. Nel database Firebase:');
                console.log(`   - Cliente: giuseppe.verdi@test.it`);
                console.log(`   - Prenotazione: smoobu_${result.id}`);
                console.log(`   - Proprietà aggiornata/creata`);
                
                return result.id;
            }
        } else {
            const error = await response.text();
            console.error('❌ Errore nella creazione:', error);
        }
    } catch (error) {
        console.error('❌ Errore nella richiesta:', error.message);
    }
}

async function getBookingDetails(bookingId) {
    try {
        console.log(`\n🔍 Recupero dettagli prenotazione ${bookingId}...`);
        
        const response = await fetch(`https://login.smoobu.com/api/reservations/${bookingId}`, {
            method: 'GET',
            headers: {
                'Api-Key': SMOOBU_API_KEY,
                'Cache-Control': 'no-cache'
            }
        });

        if (response.ok) {
            const booking = await response.json();
            console.log('📋 Dettagli prenotazione:');
            console.log(JSON.stringify(booking, null, 2));
            return booking;
        } else {
            console.error('❌ Errore nel recuperare dettagli prenotazione');
        }
    } catch (error) {
        console.error('❌ Errore nella richiesta:', error.message);
    }
}

async function updateTestBooking(bookingId) {
    try {
        console.log(`\n🔄 Aggiornamento prenotazione ${bookingId}...`);
        
        const updateData = {
            adults: 3, // Cambio da 2 a 3 adulti
            price: 420.00, // Aggiorno il prezzo
            notice: 'Prenotazione aggiornata via API - test webhook updateReservation'
        };

        console.log('📝 Dati aggiornamento:', JSON.stringify(updateData, null, 2));

        const response = await fetch(`https://login.smoobu.com/api/reservations/${bookingId}`, {
            method: 'PUT',
            headers: {
                'Api-Key': SMOOBU_API_KEY,
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            },
            body: JSON.stringify(updateData)
        });

        console.log(`📥 Response Status: ${response.status} ${response.statusText}`);
        
        if (response.ok) {
            const result = await response.json();
            console.log('📄 Response:', JSON.stringify(result, null, 2));
            console.log('✅ Prenotazione aggiornata! Dovresti vedere un webhook "updateReservation"');
            return true;
        } else {
            const error = await response.text();
            console.error('❌ Errore nell\'aggiornamento:', error);
        }
    } catch (error) {
        console.error('❌ Errore nella richiesta:', error.message);
    }
    return false;
}

async function cancelTestBooking(bookingId) {
    try {
        console.log(`\n❌ Cancellazione prenotazione ${bookingId}...`);
        
        const response = await fetch(`https://login.smoobu.com/api/reservations/${bookingId}`, {
            method: 'DELETE',
            headers: {
                'Api-Key': SMOOBU_API_KEY,
                'Cache-Control': 'no-cache'
            }
        });

        console.log(`📥 Response Status: ${response.status} ${response.statusText}`);
        
        if (response.ok) {
            const result = await response.json();
            console.log('📄 Response:', JSON.stringify(result, null, 2));
            console.log('✅ Prenotazione cancellata! Dovresti vedere un webhook "cancelReservation"');
            return true;
        } else {
            const error = await response.text();
            console.error('❌ Errore nella cancellazione:', error);
        }
    } catch (error) {
        console.error('❌ Errore nella richiesta:', error.message);
    }
    return false;
}

async function runCompleteTest() {
    console.log('🎯 TESTING COMPLETO INTEGRAZIONE SMOOBU');
    console.log('=====================================\n');
    console.log('⚠️  PREREQUISITI:');
    console.log('1. Sostituisci SMOOBU_API_KEY con la tua API key');
    console.log('2. Sostituisci APARTMENT_ID con un ID valido dal tuo account');
    console.log('3. Assicurati che il pms-sync-service sia in esecuzione');
    console.log('4. Configura il webhook URL nelle impostazioni Smoobu\n');

    // Step 1: Crea prenotazione
    const bookingId = await createTestBooking();
    if (!bookingId) {
        console.log('❌ Test fallito: impossibile creare prenotazione');
        return;
    }

    // Aspetta un po' per dare tempo al webhook
    console.log('\n⏳ Attendendo 3 secondi per il webhook...');
    await new Promise(resolve => setTimeout(resolve, 3000));

    // Step 2: Recupera dettagli
    await getBookingDetails(bookingId);

    // Aspetta un po'
    console.log('\n⏳ Attendendo 3 secondi...');
    await new Promise(resolve => setTimeout(resolve, 3000));

    // Step 3: Aggiorna prenotazione
    const updated = await updateTestBooking(bookingId);
    if (updated) {
        console.log('\n⏳ Attendendo 3 secondi per il webhook update...');
        await new Promise(resolve => setTimeout(resolve, 3000));
    }

    // Step 4: Cancella prenotazione
    const cancelled = await cancelTestBooking(bookingId);
    if (cancelled) {
        console.log('\n⏳ Attendendo 3 secondi per il webhook cancel...');
        await new Promise(resolve => setTimeout(resolve, 3000));
    }

    console.log('\n🎉 TEST COMPLETATO!');
    console.log('\n🔍 Controlla ora:');
    console.log('1. I log del pms-sync-service per vedere i webhook ricevuti');
    console.log('2. Il database Firebase per vedere i dati sincronizzati');
    console.log('3. Se tutti i webhook sono stati processati correttamente');
}

// Permetti di eseguire singole funzioni o test completo
if (process.argv.includes('--create-only')) {
    createTestBooking();
} else if (process.argv.includes('--complete')) {
    runCompleteTest();
} else {
    console.log('📋 Opzioni disponibili:');
    console.log('node test_smoobu_create_booking.js --create-only  # Crea solo una prenotazione');
    console.log('node test_smoobu_create_booking.js --complete     # Test completo (crea, aggiorna, cancella)');
} 