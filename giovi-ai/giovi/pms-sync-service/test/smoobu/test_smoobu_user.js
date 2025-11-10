// Script per testare API Smoobu e recuperare user ID
const SMOOBU_API_KEY = 'kzenAwU8arzdZ52ctlSziUOHzFHdrFbfQv3zp41KaE '; // Sostituisci con la tua API key

async function getSmoobuUserInfo() {
    try {
        const response = await fetch('https://login.smoobu.com/api/me', {
            method: 'GET',
            headers: {
                'Api-Key': SMOOBU_API_KEY,
                'Cache-Control': 'no-cache'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const userData = await response.json();
        console.log('🔍 User Data from Smoobu:');
        console.log(JSON.stringify(userData, null, 2));
        
        if (userData.id) {
            console.log(`\n✅ Il tuo smoobuUserId è: ${userData.id}`);
            console.log('\n📝 Aggiungi questo campo al documento dell\'host in Firebase:');
            console.log(`{
  "smoobuUserId": ${userData.id},
  "role": "host",
  // altri campi esistenti...
}`);
        }
        
        return userData;
    } catch (error) {
        console.error('❌ Errore nel recuperare info utente Smoobu:', error.message);
    }
}

async function getSmoobuApartments() {
    try {
        const response = await fetch('https://login.smoobu.com/api/apartments', {
            method: 'GET',
            headers: {
                'Api-Key': SMOOBU_API_KEY,
                'Cache-Control': 'no-cache'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const apartmentsData = await response.json();
        console.log('\n🏠 Apartments from Smoobu:');
        console.log(JSON.stringify(apartmentsData, null, 2));
        
        return apartmentsData;
    } catch (error) {
        console.error('❌ Errore nel recuperare appartamenti Smoobu:', error.message);
    }
}

// Esegui il test
async function runTest() {
    console.log('🚀 Testing Smoobu API connection...\n');
    
    await getSmoobuUserInfo();
    await getSmoobuApartments();
}

runTest(); 