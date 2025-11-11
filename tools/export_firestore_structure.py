import json
import os
import sys
from pathlib import Path

from google.cloud import firestore


def get_structure(collection_ref):
    structure = {}
    docs = collection_ref.stream()
    for doc in docs:
        subcollections = doc.reference.collections()
        structure[doc.id] = {
            "fields": sorted(doc.to_dict().keys()),
            "subcollections": {},
        }
        for sub in subcollections:
            structure[doc.id]["subcollections"][sub.id] = get_structure(sub)
    return structure


def main(output_path):
    client = firestore.Client()
    result = {}
    for collection in client.collections():
        result[collection.id] = get_structure(collection)

    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"✅ Struttura esportata in {output_path}")


if __name__ == "__main__":
    if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        print("❌ Variabile GOOGLE_APPLICATION_CREDENTIALS non impostata.", file=sys.stderr)
        sys.exit(1)

    output_file = Path(__file__).resolve().parent.parent / "firestore_structure.json"
    main(output_file)

