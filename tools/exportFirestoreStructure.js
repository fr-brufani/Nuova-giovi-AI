const admin = require("firebase-admin");
const fs = require("fs");
const path = require("path");

admin.initializeApp({
  credential: admin.credential.applicationDefault(),
});

const db = admin.firestore();

async function getStructure(collectionRef) {
  const snapshot = await collectionRef.get();
  const structure = {};

  for (const doc of snapshot.docs) {
    const subcollections = await doc.ref.listCollections();
    structure[doc.id] = {
      fields: Object.keys(doc.data()),
      subcollections: {},
    };
    for (const sub of subcollections) {
      structure[doc.id].subcollections[sub.id] = await getStructure(sub);
    }
  }

  return structure;
}

async function main() {
  const collections = await db.listCollections();
  const result = {};

  for (const col of collections) {
    result[col.id] = await getStructure(col);
  }

  const outputPath = path.resolve(__dirname, "../firestore_structure.json");
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
  console.log(`✅ Struttura esportata in ${outputPath}`);
}

main().catch((error) => {
  console.error("❌ Errore durante l'esportazione della struttura Firestore:", error);
  process.exit(1);
});

