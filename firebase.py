# firebase.py
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase once
def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)

# Firestore client
db = firestore.client()
