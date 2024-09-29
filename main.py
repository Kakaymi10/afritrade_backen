from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
import firebase_admin
from firebase_admin import credentials, firestore
import bcrypt
import shutil
import os
import uuid  # For generating unique user IDs

# Firebase Initialization
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

app = FastAPI()

# Add CORS middleware to allow requests from localhost:3000 (your React app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Directory to save uploaded images
UPLOAD_DIRECTORY = "./uploads"

# Create the upload directory if it doesn't exist
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

@app.post("/upload-image")
async def upload_image(image: UploadFile = File(...)):
    # Create a unique filename
    file_location = os.path.join(UPLOAD_DIRECTORY, image.filename)

    # Save the uploaded image
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # Construct the image URL
    image_url = f"http://localhost:8000/uploads/{image.filename}"
    return JSONResponse(content={"image_url": image_url})

# Serve the uploaded files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIRECTORY), name="uploads")

# Define Product Model
class Product(BaseModel):
    product_name: str
    location: str
    supplier_name: str
    product_details: str
    image_url: str  # Assuming you store image URLs for products
    user_id: str  # ID of the user who added the product

# Define Registration Models with password
class ClientRegistration(BaseModel):
    name: str
    email: EmailStr
    location: str
    business_type: str  # SME, exporter, manufacturer
    trade_focus: str  # Products they deal in
    password: str  # Added password field

class SupplierRegistration(BaseModel):
    name: str
    email: EmailStr
    company_name: str
    location: str
    product_categories: list[str]  # List of categories like electronics, textiles
    capacity: int  # Max orders supplier can handle
    password: str  # Added password field

class TransporterRegistration(BaseModel):
    name: str
    email: EmailStr
    location: str
    transport_modes: list[str]  # Modes like road, air, sea
    regions_covered: list[str]  # List of regions covered
    password: str  # Added password field

# Define Login Model
class LoginData(BaseModel):
    email: EmailStr
    password: str

# Helper function to hash passwords
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

# Helper function to verify password
def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

# Registration routes with unique ID and hashed passwords
@app.post("/register/client/")
async def register_client(client: ClientRegistration):
    try:
        client_ref = db.collection("clients").document(client.email)
        hashed_password = hash_password(client.password)
        client_data = client.dict()
        client_data['password'] = hashed_password
        
        # Generate a unique ID for the client
        client_id = str(uuid.uuid4())
        client_data['client_id'] = client_id
        
        client_ref.set(client_data)
        return {"message": "Client registration successful", "client_id": client_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/register/supplier/")
async def register_supplier(supplier: SupplierRegistration):
    try:
        supplier_ref = db.collection("suppliers").document(supplier.email)
        hashed_password = hash_password(supplier.password)
        supplier_data = supplier.dict()
        supplier_data['password'] = hashed_password
        
        # Generate a unique ID for the supplier
        supplier_id = str(uuid.uuid4())
        supplier_data['supplier_id'] = supplier_id
        
        supplier_ref.set(supplier_data)
        return {"message": "Supplier registration successful", "supplier_id": supplier_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/register/transporter/")
async def register_transporter(transporter: TransporterRegistration):
    try:
        transporter_ref = db.collection("transporters").document(transporter.email)
        hashed_password = hash_password(transporter.password)
        transporter_data = transporter.dict()
        transporter_data['password'] = hashed_password
        
        # Generate a unique ID for the transporter
        transporter_id = str(uuid.uuid4())
        transporter_data['transporter_id'] = transporter_id
        
        transporter_ref.set(transporter_data)
        return {"message": "Transporter registration successful", "transporter_id": transporter_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Login route to verify email and password and return the role
@app.post("/login/")
async def login(login_data: LoginData):
    try:
        # Check in all collections (clients, suppliers, transporters)
        user_roles = {
            "clients": "client",
            "suppliers": "supplier",
            "transporters": "transporter"
        }

        for collection, role in user_roles.items():
            user_ref = db.collection(collection).document(login_data.email)
            user_data = user_ref.get()
            if user_data.exists:
                user = user_data.to_dict()
                if verify_password(login_data.password, user["password"]):
                    return {"message": "Login successful", "role": role}

        raise HTTPException(status_code=401, detail="Invalid email or password")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get user by ID route
@app.get("/user/{user_id}")
async def get_user_by_id(user_id: str):
    try:
        # Check in all collections (clients, suppliers, transporters)
        user_roles = {
            "clients": "client_id",
            "suppliers": "supplier_id",
            "transporters": "transporter_id"
        }

        for collection, id_field in user_roles.items():
            users_ref = db.collection(collection).where(id_field, "==", user_id)
            users = users_ref.stream()
            user_list = [user.to_dict() for user in users]
            if user_list:
                return user_list[0]  # Assuming IDs are unique, return the first match

        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get products by user ID route
@app.get("/products")
async def get_products_by_user_id(user_id: str):
    try:
        # Fetch products where user_id matches the provided user ID
        products_ref = db.collection("products").where("user_id", "==", user_id)
        products = products_ref.stream()
        user_products = [product.to_dict() for product in products]

        if user_products:
            return user_products
        else:
            raise HTTPException(status_code=404, detail="No products found for this user ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# CRUD operations for Products
@app.post("/products/")
async def add_product(product: Product):
    try:
        product_ref = db.collection("products").document()
        product_ref.set(product.dict())
        return {"message": "Product added successfully", "product_id": product_ref.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/")
async def get_all_products():
    try:
        products_ref = db.collection("products")
        products = products_ref.stream()
        all_products = [product.to_dict() for product in products]
        return all_products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/{product_id}")
async def get_product(product_id: str):
    try:
        product_ref = db.collection("products").document(product_id)
        product_data = product_ref.get()
        if product_data.exists:
            return product_data.to_dict()
        else:
            raise HTTPException(status_code=404, detail="Product not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Update a product by user_id and product_name
@app.put("/products/")
async def update_product(user_id: str, product_name: str, product: Product):
    try:
        product_ref = db.collection("products").where("user_id", "==", user_id).where("product_name", "==", product_name)
        products = product_ref.stream()

        for product_doc in products:
            product_ref = db.collection("products").document(product_doc.id)
            product_ref.update(product.dict())
            return {"message": "Product updated successfully"}

        raise HTTPException(status_code=404, detail="Product not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/products/{product_id}")
async def delete_product(product_id: str):
    try:
        product_ref = db.collection("products").document(product_id)
        product_data = product_ref.get()
        if product_data.exists:
            product_ref.delete()
            return {"message": "Product deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Product not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== ORDERS =====

class Order(BaseModel):
    product_id: str
    product_name: str
    buyer_name: str
    buyer_id: str
    location: str
    status: str  # Example statuses: 'Pending', 'Shipped', 'Delivered'

@app.post("/orders/")
async def place_order(order: Order):
    try:
        order_ref = db.collection("orders").document()
        order_ref.set(order.dict())
        return {"message": "Order placed successfully", "order_id": order_ref.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    try:
        order_ref = db.collection("orders").document(order_id)
        order_data = order_ref.get()
        if order_data.exists:
            return order_data.to_dict()
        else:
            raise HTTPException(status_code=404, detail="Order not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/orders/")
async def get_orders_by_buyer_id(buyer_id: str):
    try:
        orders_ref = db.collection("orders").where("buyer_id", "==", buyer_id)
        orders = orders_ref.stream()
        buyer_orders = [order.to_dict() for order in orders]

        if buyer_orders:
            return buyer_orders
        else:
            raise HTTPException(status_code=404, detail="No orders found for this buyer ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/orders/{order_id}")
async def update_order_status(order_id: str, status: str):
    try:
        order_ref = db.collection("orders").document(order_id)
        order_data = order_ref.get()
        if order_data.exists:
            order_ref.update({"status": status})
            return {"message": "Order status updated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Order not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

 
# Health check
@app.get("/")
def health_check():
    return {"message": "AfriTrade API is running!"}
