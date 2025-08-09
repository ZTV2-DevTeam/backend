"""
Partner management API endpoints.
Handles CRUD operations for partners and partner types.
"""

from ninja import Schema
from api.models import Partner, PartnerTipus
from .auth import JWTAuth, ErrorSchema

# ============================================================================
# Schemas
# ============================================================================

class PartnerSchema(Schema):
    """Response schema for partner data."""
    id: int
    name: str
    address: str = ""
    institution: str = None
    imageURL: str = None

class PartnerCreateSchema(Schema):
    """Request schema for creating new partner."""
    name: str
    address: str = ""
    institution: str = None
    imageURL: str = None

class PartnerUpdateSchema(Schema):
    """Request schema for updating existing partner."""
    name: str = None
    address: str = None
    institution: str = None
    imageURL: str = None

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
