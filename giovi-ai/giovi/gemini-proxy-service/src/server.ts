// gemini-proxy-service - Proxy per Gemini API con WhatsApp e Gmail
// NOTA: Questo è un file temporaneo di fallback che usa il JS pre-compilato

console.log('Starting Gemini Proxy Service...');

// Re-export dal modulo JS compilato esistente
try {
    require('../lib/server.js');
} catch (error) {
    console.error('Failed to load pre-compiled JS server:', error);
    process.exit(1);
}    