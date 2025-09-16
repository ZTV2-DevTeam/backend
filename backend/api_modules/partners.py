"""
FTV Partners API Module

This module provides comprehensive partner management functionality for the FTV system,
including CRUD operations for partners and automatic institution type management.

Public API Overview:
==================

The Partners API enables management of external partners and their institutional affiliations.
All endpoints return JSON responses with consistent schemas.

Base URL: /api/partners/

Public Endpoints (No Authentication Required):
- GET  /partners                 - List all partners
- GET  /partners/{id}           - Get specific partner details
- GET  /partners/types          - List all partner types (for dropdowns)

Protected Endpoints (JWT Token Required):
- POST /partners                - Create new partner
- PUT  /partners/{id}          - Update partner information  
- DELETE /partners/{id}        - Delete partner

Partner Data Structure:
======================

Each partner contains:
- id: Unique identifier
- name: Partner organization name
- address: Physical address (optional)
- institution: Institution type name (auto-created if new)
- imageURL: Partner logo/image URL (optional)

Institution Management:
======================

The system automatically manages institution types:
- When creating/updating partners with institution names
- New institution types are automatically created
- Institution names are normalized and deduplicated
- Empty strings are treated as null institutions

Example Usage:
=============

Get all partners:
curl /api/partners

Get all partner types (for dropdowns):
curl /api/partners/types

Create new partner:
curl -X POST /api/partners \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"name":"ABC Corp","address":"123 Main St","institution":"Technology"}'

Update partner:
curl -X PUT /api/partners/1 \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"name":"ABC Corporation","imageURL":"https://example.com/logo.png"}'

Error Handling:
==============

- 200/201: Success
- 400: Validation errors (duplicate names, invalid data)
- 401: Authentication required
- 404: Partner not found
- 500: Server error

Validation Rules:
================

- Partner names must be unique across the system
- Institution names are automatically normalized
- All string fields accept empty strings (converted to appropriate nulls)
- Image URLs should be valid HTTP/HTTPS URLs
"""

from ninja import Schema
from api.models import Partner, PartnerTipus
from .auth import JWTAuth, ErrorSchema
from typing import Optional

# ============================================================================
# Schemas
# ============================================================================

class PartnerTipusSchema(Schema):
    """Response schema for partner type data."""
    id: int
    name: str

class PartnerSchema(Schema):
    """Response schema for partner data."""
    id: int
    name: str
    address: str = ""
    institution: Optional[str] = None
    imageURL: Optional[str] = None

class PartnerCreateSchema(Schema):
    """Request schema for creating new partner."""
    name: str
    address: str = ""
    institution: Optional[str] = None
    imageURL: Optional[str] = None

class PartnerUpdateSchema(Schema):
    """Request schema for updating existing partner."""
    name: Optional[str] = None
    address: Optional[str] = None
    institution: Optional[str] = None
    imageURL: Optional[str] = None

# ============================================================================
# Utility Functions
# ============================================================================

def create_partner_response(partner: Partner) -> dict:
    """
    Create standardized partner response dictionary.
    
    Args:
        partner: Partner model instance
        
    Returns:
        Dictionary with partner information
    """
    return {
        "id": partner.id,
        "name": partner.name,
        "address": partner.address or "",
        "institution": partner.institution.name if partner.institution else None,
        "imageURL": partner.imgUrl
    }

def handle_institution_assignment(institution_name: str = None) -> PartnerTipus:
    """
    Handle partner institution assignment.
    
    Creates new institution type if it doesn't exist.
    
    Args:
        institution_name: Name of the institution
        
    Returns:
        PartnerTipus instance or None
    """
    if institution_name:
        if institution_name == "":
            return None
        institution_obj, created = PartnerTipus.objects.get_or_create(name=institution_name)
        return institution_obj
    return None

# ============================================================================
# API Endpoints
# ============================================================================

def register_partner_endpoints(api):
    """Register all partner-related endpoints with the API router."""
    
    @api.get("/partners/types", response={200: list[PartnerTipusSchema], 401: ErrorSchema})
    def get_partner_types(request):
        """
        Get all partner types.
        
        Public endpoint that returns all partner types for dropdown usage.
        Used by frontend to populate partner type selection dropdowns.
        
        Returns:
            200: List of all partner types
            401: Error occurred
        """
        try:
            partner_types = PartnerTipus.objects.all().order_by('name')
            
            response = []
            for partner_type in partner_types:
                response.append({
                    "id": partner_type.id,
                    "name": partner_type.name
                })
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching partner types: {str(e)}"}
    
    @api.get("/partners", response={200: list[PartnerSchema], 401: ErrorSchema})
    def get_partners(request):
        """
        Get all partners.
        
        Public endpoint that returns all partners with their institution information.
        
        Returns:
            200: List of all partners
            401: Error occurred
        """
        try:
            partners = Partner.objects.select_related('institution').all()
            
            response = []
            for partner in partners:
                response.append(create_partner_response(partner))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching partners: {str(e)}"}

    @api.get("/partners/{partner_id}", response={200: PartnerSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_partner(request, partner_id: int):
        """
        Get single partner by ID.
        
        Public endpoint that returns detailed information about a specific partner.
        
        Args:
            partner_id: Unique partner identifier
            
        Returns:
            200: Partner details
            404: Partner not found
            401: Error occurred
        """
        try:
            partner = Partner.objects.select_related('institution').get(id=partner_id)
            return 200, create_partner_response(partner)
        except Partner.DoesNotExist:
            return 404, {"message": "Partner not found"}
        except Exception as e:
            return 401, {"message": f"Error fetching partner: {str(e)}"}

    @api.post("/partners", auth=JWTAuth(), response={201: PartnerSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_partner(request, data: PartnerCreateSchema):
        """
        Create new partner.
        
        Requires authentication. Creates a new partner with optional institution assignment.
        
        Args:
            data: Partner creation data
            
        Returns:
            201: Partner created successfully
            400: Invalid data or duplicate name
            401: Authentication failed
        """
        try:
            # Handle institution lookup if provided
            institution_obj = handle_institution_assignment(data.institution)
            
            partner = Partner.objects.create(
                name=data.name,
                address=data.address or "",
                institution=institution_obj,
                imgUrl=data.imageURL
            )
            
            return 201, create_partner_response(partner)
        except Exception as e:
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                return 400, {"message": "Partner with this name already exists"}
            return 400, {"message": f"Error creating partner: {str(e)}"}

    @api.put("/partners/{partner_id}", auth=JWTAuth(), response={200: PartnerSchema, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
    def update_partner(request, partner_id: int, data: PartnerUpdateSchema):
        """
        Update existing partner.
        
        Requires authentication. Updates partner information with provided data.
        Only non-None fields are updated.
        
        Args:
            partner_id: Unique partner identifier
            data: Partner update data
            
        Returns:
            200: Partner updated successfully
            404: Partner not found
            400: Invalid data or duplicate name
            401: Authentication failed
        """
        try:
            partner = Partner.objects.get(id=partner_id)
            
            # Update fields only if they are provided (not None)
            if data.name is not None:
                partner.name = data.name
            if data.address is not None:
                partner.address = data.address
            if data.imageURL is not None:
                partner.imgUrl = data.imageURL
            if data.institution is not None:
                partner.institution = handle_institution_assignment(data.institution)
            
            partner.save()
            
            return 200, create_partner_response(partner)
        except Partner.DoesNotExist:
            return 404, {"message": "Partner not found"}
        except Exception as e:
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                return 400, {"message": "Partner with this name already exists"}
            return 400, {"message": f"Error updating partner: {str(e)}"}

    @api.delete("/partners/{partner_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
    def delete_partner(request, partner_id: int):
        """
        Delete partner.
        
        Requires authentication. Permanently removes partner from database.
        
        Args:
            partner_id: Unique partner identifier
            
        Returns:
            200: Partner deleted successfully
            404: Partner not found
            401: Authentication failed
        """
        try:
            partner = Partner.objects.get(id=partner_id)
            partner_name = partner.name
            partner.delete()
            
            return 200, {"message": f"Partner '{partner_name}' deleted successfully"}
        except Partner.DoesNotExist:
            return 404, {"message": "Partner not found"}
        except Exception as e:
            return 400, {"message": f"Error deleting partner: {str(e)}"}
