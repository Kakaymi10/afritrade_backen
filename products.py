from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from uuid import uuid4
import firebase_admin
from firebase_admin import firestore, storage

# Firebase Firestore and Storage
db = firestore.client()
bucket = storage.bucket()

router = APIRouter()

# Pydantic model for product details
class Product(BaseModel):
    product_name: str
    location: str
    supplier_name: str
    description: str
    image_url: str = None

# Add a new product
@router.post("/add/")
async def add_product(product_name: str = Form(...), location: str = Form(...), supplier_name: str = Form(...), description: str = Form(...), image: UploadFile = File(...)):
    try:
        product_id = str(uuid4())
        blob = bucket.blob(f'products/{product_id}/{image.filename}')
        blob.upload_from_file(image.file, content_type=image.content_type)
        image_url = blob.public_url

        product_ref = db.collection("products").document(product_id)
        product_ref.set({
            "product_name": product_name,
            "location": location,
            "supplier_name": supplier_name,
            "description": description,
            "image_url": image_url
        })

        return {"message": "Product added successfully", "product_id": product_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Edit an existing product
@router.put("/edit/{product_id}")
async def edit_product(product_id: str, product: Product):
    try:
        product_ref = db.collection("products").document(product_id)
        if not product_ref.get().exists:
            raise HTTPException(status_code=404, detail="Product not found")

        product_ref.update(product.dict(exclude_unset=True))
        return {"message": "Product updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Delete a product
@router.delete("/delete/{product_id}")
async def delete_product(product_id: str):
    try:
        product_ref = db.collection("products").document(product_id)
        if not product_ref.get().exists:
            raise HTTPException(status_code=404, detail="Product not found")

        product_ref.delete()
        blobs = bucket.list_blobs(prefix=f'products/{product_id}/')
        for blob in blobs:
            blob.delete()

        return {"message": "Product deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get a product by ID
@router.get("/{product_id}")
async def get_product(product_id: str):
    try:
        product_ref = db.collection("products").document(product_id)
        product = product_ref.get()
        if not product.exists:
            raise HTTPException(status_code=404, detail="Product not found")
        return product.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# List all products
@router.get("/")
async def list_products():
    try:
        products_ref = db.collection("products").stream()
        products = [product.to_dict() for product in products_ref]
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
