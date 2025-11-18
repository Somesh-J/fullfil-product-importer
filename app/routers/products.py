# app/routers/products.py
# Product CRUD endpoints
# - GET /api/products: List products (paginated, filtered)
# - GET /api/products/{id}: Get single product
# - POST /api/products: Create product
# - PUT /api/products/{id}: Update product
# - DELETE /api/products/{id}: Delete product
# - DELETE /api/products/bulk: Bulk delete all products

import math
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select, or_, delete
from sqlalchemy.exc import IntegrityError

from app.db import AsyncSessionLocal
from app.models import Product
from app.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    DeleteResponse,
    BulkDeleteResponse,
)
from app.tasks import bulk_delete_task
from app.utils import publish_progress_async

router = APIRouter()


@router.get("/products", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sku: Optional[str] = Query(None, description="Filter by SKU (case-insensitive partial match)"),
    q: Optional[str] = Query(None, description="Search in name and description"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
):
    """
    List products with pagination and filtering
    
    - Supports pagination (default: page=1, page_size=20)
    - Filter by SKU (case-insensitive partial match)
    - Search by name/description (case-insensitive partial match)
    - Filter by active status
    """
    async with AsyncSessionLocal() as session:
        # Build query
        query = select(Product)
        
        # Apply filters
        if sku:
            sku_term = f"{sku.lower()}%"  # Starts with (prefix match)
            query = query.where(Product.sku_ci.like(sku_term))
        
        if q:
            search_term = f"%{q}%"  # Contains anywhere
            query = query.where(
                or_(
                    Product.name.ilike(search_term),
                    Product.description.ilike(search_term)
                )
            )
        
        if active is not None:
            query = query.where(Product.active == active)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        result = await session.execute(count_query)
        total = result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(Product.created_at.desc())
        query = query.limit(page_size).offset(offset)
        
        # Execute query
        result = await session.execute(query)
        products = result.scalars().all()
        
        # Calculate total pages
        pages = math.ceil(total / page_size) if total > 0 else 0
        
        return ProductListResponse(
            items=[ProductResponse.model_validate(p) for p in products],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int):
    """
    Get single product by ID
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {product_id} not found"
            )
        
        return ProductResponse.model_validate(product)


@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(product_data: ProductCreate):
    """
    Create a new product
    
    - SKU must be unique (case-insensitive)
    - Returns created product
    """
    async with AsyncSessionLocal() as session:
        try:
            # Create product with case-insensitive SKU
            product = Product(
                sku=product_data.sku,
                sku_ci=product_data.sku.lower(),
                name=product_data.name,
                description=product_data.description,
                price=product_data.price,
                active=product_data.active
            )
            
            session.add(product)
            await session.commit()
            await session.refresh(product)
            
            print(f"[Products] Created product: {product.id} (SKU: {product.sku})")
            
            return ProductResponse.model_validate(product)
            
        except IntegrityError as e:
            await session.rollback()
            
            # Check if it's a duplicate SKU error
            if 'sku_ci' in str(e.orig) or 'unique' in str(e.orig).lower():
                raise HTTPException(
                    status_code=409,
                    detail=f"Product with SKU '{product_data.sku}' already exists (case-insensitive)"
                )
            
            raise HTTPException(
                status_code=400,
                detail=f"Database error: {str(e.orig)}"
            )


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, product_data: ProductUpdate):
    """
    Update existing product
    
    - All fields are optional
    - SKU uniqueness is enforced (case-insensitive)
    """
    async with AsyncSessionLocal() as session:
        # Fetch product
        result = await session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {product_id} not found"
            )
        
        try:
            # Update fields if provided
            if product_data.sku is not None:
                product.sku = product_data.sku
                product.sku_ci = product_data.sku.lower()
            
            if product_data.name is not None:
                product.name = product_data.name
            
            if product_data.description is not None:
                product.description = product_data.description
            
            if product_data.price is not None:
                product.price = product_data.price
            
            if product_data.active is not None:
                product.active = product_data.active
            
            await session.commit()
            await session.refresh(product)
            
            print(f"[Products] Updated product: {product.id}")
            
            return ProductResponse.model_validate(product)
            
        except IntegrityError as e:
            await session.rollback()
            
            # Check if it's a duplicate SKU error
            if 'sku_ci' in str(e.orig) or 'unique' in str(e.orig).lower():
                raise HTTPException(
                    status_code=409,
                    detail=f"Product with SKU '{product_data.sku}' already exists (case-insensitive)"
                )
            
            raise HTTPException(
                status_code=400,
                detail=f"Database error: {str(e.orig)}"
            )


@router.delete("/products/{product_id}", response_model=DeleteResponse)
async def delete_product(product_id: int):
    """
    Delete a product by ID
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {product_id} not found"
            )
        
        await session.delete(product)
        await session.commit()
        
        print(f"[Products] Deleted product: {product_id}")
        
        return DeleteResponse(
            deleted=product_id,
            message=f"Product {product_id} deleted successfully"
        )


@router.post("/products/bulk-delete", response_model=BulkDeleteResponse, status_code=202)
async def bulk_delete_products():
    """
    Delete ALL products (triggers async Celery task)
    
    - Returns job ID for progress tracking
    - Actual deletion happens in background
    """
    # Generate job ID for tracking
    job_id = str(uuid.uuid4())
    
    # Publish initial message
    await publish_progress_async(job_id, {
        "status": "queued",
        "message": "Bulk delete queued"
    })
    
    # Trigger Celery task
    try:
        bulk_delete_task.delay(job_id)
        print(f"[Products] Triggered bulk delete task, job_id: {job_id}")
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start bulk delete task: {str(e)}"
        )
    
    return BulkDeleteResponse(
        job_id=job_id,
        message="Bulk delete started. Use /api/progress/{job_id} to track progress.",
        status="queued"
    )

