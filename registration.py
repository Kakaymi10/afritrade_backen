from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

app = FastAPI()

# Define registration models for Client, Supplier, and Transporter
class ClientRegistration(BaseModel):
    name: str
    email: EmailStr
    location: str
    business_type: str  # SME, exporter, manufacturer
    trade_focus: str  # Products they deal in

class SupplierRegistration(BaseModel):
    name: str
    email: EmailStr
    company_name: str
    location: str
    product_categories: list[str]  # List of categories like electronics, textiles
    capacity: int  # Max orders supplier can handle

class TransporterRegistration(BaseModel):
    name: str
    email: EmailStr
    location: str
    transport_modes: list[str]  # Modes like road, air, sea
    regions_covered: list[str]  # List of regions covered

# Register Client route
@app.post("/register/client/")
async def register_client(client: ClientRegistration):
    try:
        client_ref = db.collection("clients").document(client.email)
        client_ref.set(client.dict())
        return {"message": "Client registration successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Register Supplier route
@app.post("/register/supplier/")
async def register_supplier(supplier: SupplierRegistration):
    try:
        supplier_ref = db.collection("suppliers").document(supplier.email)
        supplier_ref.set(supplier.dict())
        return {"message": "Supplier registration successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Register Transporter route
@app.post("/register/transporter/")
async def register_transporter(transporter: TransporterRegistration):
    try:
        transporter_ref = db.collection("transporters").document(transporter.email)
        transporter_ref.set(transporter.dict())
        return {"message": "Transporter registration successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/")
def read_root():
    return {"message": "AfriTrade API is running!"}
