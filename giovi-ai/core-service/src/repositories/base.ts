import type { CollectionReference, DocumentReference, FirestoreDataConverter } from "firebase-admin/firestore";

import type { Firestore } from "@config/firebase";

export class FirestoreRepository {
  constructor(protected readonly db: Firestore) {}

  protected collection(path: string): FirebaseFirestore.CollectionReference<FirebaseFirestore.DocumentData>;
  protected collection<T>(
    path: string,
    converter: FirestoreDataConverter<T>,
  ): CollectionReference<T>;
  protected collection<T>(path: string, converter?: FirestoreDataConverter<T>) {
    const col = this.db.collection(path);
    return converter ? col.withConverter(converter) : col;
  }

  protected doc(path: string): FirebaseFirestore.DocumentReference<FirebaseFirestore.DocumentData>;
  protected doc<T>(path: string, converter: FirestoreDataConverter<T>): DocumentReference<T>;
  protected doc<T>(path: string, converter?: FirestoreDataConverter<T>) {
    const document = this.db.doc(path);
    return converter ? document.withConverter(converter) : document;
  }
}

