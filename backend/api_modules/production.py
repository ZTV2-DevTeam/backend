"""
Production management API endpoints.
Handles filming sessions (Forgatas), contact persons, and production-related functionality.
"""

from ninja import Schema
from api.models import Forgatas, ContactPerson, Partner, Equipment, Tanev
from .auth import JWTAuth, ErrorSchema
from datetime import datetime, date, time

# ============================================================================
# Schemas
# ============================================================================

class ContactPersonSchema(Schema):
    """Response schema for contact person data."""
    id: int
    name: str
    email: str = None
    phone: str = None

class ContactPersonCreateSchema(Schema):
    """Request schema for creating new contact person."""
    name: str
    email: str = None
    phone: str = None

class ForgatoTipusSchema(Schema):
    """Schema for filming types."""
    value: str
    label: str

class ForgatSchema(Schema):
    """Response schema for filming session data."""
    id: int
    name: str
    description: str
    date: str
    time_from: str
    time_to: str
    location: dict = None
    contact_person: ContactPersonSchema = None
    notes: str = None
    type: str
    type_display: str
    related_kacsa: dict = None
    equipment_ids: list[int] = []
    equipment_count: int = 0
    tanev: dict = None

class ForgatCreateSchema(Schema):
    """Request schema for creating new filming session."""
    name: str
    description: str
    date: str
    time_from: str
    time_to: str
    location_id: int = None
    contact_person_id: int = None
    notes: str = None
    type: str
    related_kacsa_id: int = None
    equipment_ids: list[int] = []

class ForgatUpdateSchema(Schema):
    """Request schema for updating existing filming session."""
    name: str = None
    description: str = None
    date: str = None
    time_from: str = None
    time_to: str = None
    location_id: int = None
    contact_person_id: int = None
    notes: str = None
    type: str = None
    related_kacsa_id: int = None
    equipment_ids: list[int] = None

# ============================================================================
# Constants
# ============================================================================

FORGATAS_TYPES = [
    {"value": "kacsa", "label": "KaCsa"},
    {"value": "rendes", "label": "Rendes"},
    {"value": "rendezveny", "label": "Rendezvény"},
    {"value": "egyeb", "label": "Egyéb"}
]

# ============================================================================
# Utility Functions
# ============================================================================

def create_contact_person_response(contact_person: ContactPerson) -> dict:
    """
    Create standardized contact person response dictionary.
    
    Args:
        contact_person: ContactPerson model instance
        
    Returns:
        Dictionary with contact person information
    """
    return {
        "id": contact_person.id,
        "name": contact_person.name,
        "email": contact_person.email,
        "phone": contact_person.phone
    }

def create_forgatas_response(forgatas: Forgatas) -> dict:
    """
    Create standardized filming session response dictionary.
    
    Args:
        forgatas: Forgatas model instance
        
    Returns:
        Dictionary with filming session information
    """
    # Get type display name
    type_display = "Ismeretlen"
    for tipus in FORGATAS_TYPES:
        if tipus["value"] == forgatas.forgTipus:
            type_display = tipus["label"]
            break
    
    return {
        "id": forgatas.id,
        "name": forgatas.name,
        "description": forgatas.description,
        "date": forgatas.date.isoformat(),
        "time_from": forgatas.timeFrom.isoformat(),
        "time_to": forgatas.timeTo.isoformat(),
        "location": {
            "id": forgatas.location.id,
            "name": forgatas.location.name,
            "address": forgatas.location.address
        } if forgatas.location else None,
        "contact_person": create_contact_person_response(forgatas.contactPerson) if forgatas.contactPerson else None,
        "notes": forgatas.notes,
        "type": forgatas.forgTipus,
        "type_display": type_display,
        "related_kacsa": {
            "id": forgatas.relatedKaCsa.id,
            "name": forgatas.relatedKaCsa.name,
            "date": forgatas.relatedKaCsa.date.isoformat()
        } if forgatas.relatedKaCsa else None,
        "equipment_ids": list(forgatas.equipments.values_list('id', flat=True)),
        "equipment_count": forgatas.equipments.count(),
        "tanev": {
            "id": forgatas.tanev.id,
            "display_name": str(forgatas.tanev),
            "is_active": Tanev.get_active() and Tanev.get_active().id == forgatas.tanev.id
        } if forgatas.tanev else None
    }

def check_admin_or_teacher_permissions(user) -> tuple[bool, str]:
    """
    Check if user has admin or teacher permissions for filming session management.
    
    Args:
        user: Django User object
        
    Returns:
        Tuple of (has_permission, error_message)
    """
    try:
        from api.models import Profile
        profile = Profile.objects.get(user=user)
        if not (profile.has_admin_permission('any')):
            return False, "Adminisztrátor vagy tanár jogosultság szükséges"
        return True, ""
    except Profile.DoesNotExist:
        return False, "Felhasználói profil nem található"

def check_admin_permissions(user) -> tuple[bool, str]:
    """
    Check if user has admin permissions for contact person management.
    
    Args:
        user: Django User object
        
    Returns:
        Tuple of (has_permission, error_message)
    """
    try:
        from api.models import Profile
        profile = Profile.objects.get(user=user)
        if not profile.has_admin_permission('any'):
            return False, "Adminisztrátor jogosultság szükséges"
        return True, ""
    except Profile.DoesNotExist:
        return False, "Felhasználói profil nem található"

# ============================================================================
# API Endpoints
# ============================================================================

def register_production_endpoints(api):
    """Register all production-related endpoints with the API router."""
    
    # ========================================================================
    # Contact Person Endpoints
    # ========================================================================
    
    @api.get("/contact-persons", auth=JWTAuth(), response={200: list[ContactPersonSchema], 401: ErrorSchema})
    def get_contact_persons(request):
        """
        Get all contact persons.
        
        Requires authentication. Returns all contact persons with their information.
        
        Returns:
            200: List of all contact persons
            401: Authentication failed
        """
        try:
            contacts = ContactPerson.objects.all()
            
            response = []
            for contact in contacts:
                response.append(create_contact_person_response(contact))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching contact persons: {str(e)}"}

    @api.post("/contact-persons", auth=JWTAuth(), response={201: ContactPersonSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_contact_person(request, data: ContactPersonCreateSchema):
        """
        Create new contact person.
        
        Requires admin permissions. Creates a new contact person.
        
        Args:
            data: Contact person creation data
            
        Returns:
            201: Contact person created successfully
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            contact = ContactPerson.objects.create(
                name=data.name,
                email=data.email,
                phone=data.phone
            )
            
            return 201, create_contact_person_response(contact)
        except Exception as e:
            return 400, {"message": f"Error creating contact person: {str(e)}"}

    # ========================================================================
    # Filming Session (Forgatas) Endpoints  
    # ========================================================================
    
    @api.get("/filming-sessions", auth=JWTAuth(), response={200: list[ForgatSchema], 401: ErrorSchema})
    def get_filming_sessions(request, start_date: str = None, end_date: str = None, type: str = None):
        """
        Get filming sessions with optional filtering.
        
        Requires authentication. Returns filming sessions, optionally filtered
        by date range and/or type.
        
        Args:
            start_date: Optional start date filter (ISO format)
            end_date: Optional end date filter (ISO format)
            type: Optional type filter (kacsa, rendes, rendezveny, egyeb)
            
        Returns:
            200: List of filming sessions
            401: Authentication failed
        """
        try:
            sessions = Forgatas.objects.select_related(
                'location', 'contactPerson', 'relatedKaCsa', 'tanev'
            ).prefetch_related('equipments').all()
            
            if start_date:
                sessions = sessions.filter(date__gte=start_date)
            if end_date:
                sessions = sessions.filter(date__lte=end_date)
            if type:
                sessions = sessions.filter(forgTipus=type)
            
            response = []
            for session in sessions:
                response.append(create_forgatas_response(session))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching filming sessions: {str(e)}"}

    @api.get("/filming-sessions/{forgatas_id}", auth=JWTAuth(), response={200: ForgatSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_filming_session(request, forgatas_id: int):
        """
        Get single filming session by ID.
        
        Requires authentication. Returns detailed information about a specific filming session.
        
        Args:
            forgatas_id: Unique filming session identifier
            
        Returns:
            200: Filming session details
            404: Filming session not found
            401: Authentication failed
        """
        try:
            session = Forgatas.objects.select_related(
                'location', 'contactPerson', 'relatedKaCsa', 'tanev'
            ).prefetch_related('equipments').get(id=forgatas_id)
            
            return 200, create_forgatas_response(session)
        except Forgatas.DoesNotExist:
            return 404, {"message": "Forgatás nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching filming session: {str(e)}"}

    @api.get("/filming-sessions/types", response={200: list[ForgatoTipusSchema]})
    def get_filming_types(request):
        """
        Get available filming session types.
        
        Public endpoint that returns all available filming session types.
        
        Returns:
            200: List of filming session types
        """
        return 200, FORGATAS_TYPES

    @api.post("/filming-sessions", auth=JWTAuth(), response={201: ForgatSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_filming_session(request, data: ForgatCreateSchema):
        """
        Create new filming session.
        
        Requires admin/teacher permissions. Creates a new filming session.
        
        Args:
            data: Filming session creation data
            
        Returns:
            201: Filming session created successfully
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check if user has appropriate permissions
            has_permission, error_message = check_admin_or_teacher_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Validate type
            valid_types = [t["value"] for t in FORGATAS_TYPES]
            if data.type not in valid_types:
                return 400, {"message": "Érvénytelen forgatás típus"}
            
            # Parse date and times
            try:
                session_date = datetime.fromisoformat(data.date).date()
                time_from = datetime.fromisoformat(data.time_from).time()
                time_to = datetime.fromisoformat(data.time_to).time()
            except ValueError:
                return 400, {"message": "Hibás dátum vagy idő formátum"}
            
            if time_from >= time_to:
                return 400, {"message": "A befejezés idejének a kezdés ideje után kell lennie"}
            
            # Get related objects
            location = None
            if data.location_id:
                try:
                    location = Partner.objects.get(id=data.location_id)
                except Partner.DoesNotExist:
                    return 400, {"message": "Helyszín nem található"}
            
            contact_person = None
            if data.contact_person_id:
                try:
                    contact_person = ContactPerson.objects.get(id=data.contact_person_id)
                except ContactPerson.DoesNotExist:
                    return 400, {"message": "Kapcsolattartó nem található"}
            
            related_kacsa = None
            if data.related_kacsa_id:
                try:
                    related_kacsa = Forgatas.objects.get(id=data.related_kacsa_id, forgTipus='kacsa')
                except Forgatas.DoesNotExist:
                    return 400, {"message": "Kapcsolódó KaCsa forgatás nem található"}
            
            # Create filming session
            forgatas = Forgatas.objects.create(
                name=data.name,
                description=data.description,
                date=session_date,
                timeFrom=time_from,
                timeTo=time_to,
                location=location,
                contactPerson=contact_person,
                notes=data.notes,
                forgTipus=data.type,
                relatedKaCsa=related_kacsa
            )
            
            # Add equipment if provided
            if data.equipment_ids:
                equipment = Equipment.objects.filter(id__in=data.equipment_ids)
                forgatas.equipments.set(equipment)
            
            return 201, create_forgatas_response(forgatas)
        except Exception as e:
            return 400, {"message": f"Error creating filming session: {str(e)}"}

    @api.put("/filming-sessions/{forgatas_id}", auth=JWTAuth(), response={200: ForgatSchema, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
    def update_filming_session(request, forgatas_id: int, data: ForgatUpdateSchema):
        """
        Update existing filming session.
        
        Requires admin/teacher permissions. Updates filming session with provided data.
        Only non-None fields are updated.
        
        Args:
            forgatas_id: Unique filming session identifier
            data: Filming session update data
            
        Returns:
            200: Filming session updated successfully
            404: Filming session not found
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check if user has appropriate permissions
            has_permission, error_message = check_admin_or_teacher_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            forgatas = Forgatas.objects.get(id=forgatas_id)
            
            # Update basic fields
            if data.name is not None:
                forgatas.name = data.name
            if data.description is not None:
                forgatas.description = data.description
            if data.notes is not None:
                forgatas.notes = data.notes
            
            # Update date and times
            if data.date is not None:
                try:
                    forgatas.date = datetime.fromisoformat(data.date).date()
                except ValueError:
                    return 400, {"message": "Hibás dátum formátum"}
            
            if data.time_from is not None:
                try:
                    forgatas.timeFrom = datetime.fromisoformat(data.time_from).time()
                except ValueError:
                    return 400, {"message": "Hibás kezdő idő formátum"}
            
            if data.time_to is not None:
                try:
                    forgatas.timeTo = datetime.fromisoformat(data.time_to).time()
                except ValueError:
                    return 400, {"message": "Hibás befejező idő formátum"}
            
            # Validate time range
            if forgatas.timeFrom >= forgatas.timeTo:
                return 400, {"message": "A befejezés idejének a kezdés ideje után kell lennie"}
            
            # Update type
            if data.type is not None:
                valid_types = [t["value"] for t in FORGATAS_TYPES]
                if data.type not in valid_types:
                    return 400, {"message": "Érvénytelen forgatás típus"}
                forgatas.forgTipus = data.type
            
            # Update related objects
            if data.location_id is not None:
                if data.location_id == 0:
                    forgatas.location = None
                else:
                    try:
                        location = Partner.objects.get(id=data.location_id)
                        forgatas.location = location
                    except Partner.DoesNotExist:
                        return 400, {"message": "Helyszín nem található"}
            
            if data.contact_person_id is not None:
                if data.contact_person_id == 0:
                    forgatas.contactPerson = None
                else:
                    try:
                        contact_person = ContactPerson.objects.get(id=data.contact_person_id)
                        forgatas.contactPerson = contact_person
                    except ContactPerson.DoesNotExist:
                        return 400, {"message": "Kapcsolattartó nem található"}
            
            if data.related_kacsa_id is not None:
                if data.related_kacsa_id == 0:
                    forgatas.relatedKaCsa = None
                else:
                    try:
                        related_kacsa = Forgatas.objects.get(id=data.related_kacsa_id, forgTipus='kacsa')
                        forgatas.relatedKaCsa = related_kacsa
                    except Forgatas.DoesNotExist:
                        return 400, {"message": "Kapcsolódó KaCsa forgatás nem található"}
            
            forgatas.save()
            
            # Update equipment if provided
            if data.equipment_ids is not None:
                equipment = Equipment.objects.filter(id__in=data.equipment_ids)
                forgatas.equipments.set(equipment)
            
            return 200, create_forgatas_response(forgatas)
        except Forgatas.DoesNotExist:
            return 404, {"message": "Forgatás nem található"}
        except Exception as e:
            return 400, {"message": f"Error updating filming session: {str(e)}"}

    @api.delete("/filming-sessions/{forgatas_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
    def delete_filming_session(request, forgatas_id: int):
        """
        Delete filming session.
        
        Requires admin permissions. Permanently removes filming session from database.
        
        Args:
            forgatas_id: Unique filming session identifier
            
        Returns:
            200: Filming session deleted successfully
            404: Filming session not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions (more strict for deletion)
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            forgatas = Forgatas.objects.get(id=forgatas_id)
            forgatas_name = forgatas.name
            forgatas.delete()
            
            return 200, {"message": f"Forgatás '{forgatas_name}' sikeresen törölve"}
        except Forgatas.DoesNotExist:
            return 404, {"message": "Forgatás nem található"}
        except Exception as e:
            return 400, {"message": f"Error deleting filming session: {str(e)}"}
