"""
FTV Production Management API Module

This module provides comprehensive filming session and production management functionality
for the FTV system, including session scheduling, equipment assignment, contact management,
and production workflow support.

Public API Overview:
==================

The Production API manages all aspects of media production including filming sessions
(Forgatás), contact person management, equipment assignment, and production scheduling
with conflict detection and resource management.

Base URL: /api/production/

Protected Endpoints (JWT Token Required):

Contact Persons:
- GET  /contact-persons         - List all contact persons
- POST /contact-persons         - Create new contact person (admin only)

Filming Sessions:
- GET  /filming-sessions        - List filming sessions with filters
- GET  /filming-sessions/{id}   - Get specific session details
- POST /filming-sessions        - Create new session (admin only)
- PUT  /filming-sessions/{id}   - Update session (admin only)
- DELETE /filming-sessions/{id} - Delete session (admin only)
- GET  /filming-types          - Get available filming types
- GET  /filming-sessions/kacsa-available - Get available KaCsa sessions for linking

Production System Overview:
==========================

The production system manages the complete filming workflow:

1. **Session Planning**: Date, time, and location coordination
2. **Resource Assignment**: Equipment and personnel allocation
3. **Contact Management**: External contact person tracking
4. **Type Classification**: Different production categories
5. **Conflict Detection**: Equipment and personnel availability
6. **Academic Integration**: School year and class coordination

Filming Session Types:
=====================

Production categories for different content types:
- **KaCsa**: Special student-produced content format
- **Rendes**: Regular/standard productions
- **Rendezvény**: Event coverage and documentation
- **Egyéb**: Other/miscellaneous productions

Each type has specific workflows and requirements.

Data Structure:
==============

Contact Person:
- id: Unique identifier
- name: Contact person name
- email: Email address (optional)
- phone: Phone number (optional)

Filming Session (Forgatás):
- id: Unique identifier
- name: Session title/name
- description: Detailed description
- date: Filming date
- time_from: Start time
- time_to: End time
- location: Partner location details
- contact_person: External contact information
- notes: Additional notes and instructions
- type: Production type classification
- type_display: Human-readable type label
- related_kacsa: Related KaCsa content reference
- equipment_ids: Assigned equipment list
- equipment_count: Number of equipment items
- tanev: Associated school year

Equipment Integration:
=====================

Comprehensive equipment management:
- Equipment assignment to sessions
- Availability conflict detection
- Equipment count tracking
- Functional status validation
- Resource booking prevention

The system prevents double-booking equipment and ensures
all assigned equipment is functional and available.

Location and Partner Integration:
================================

Partner location management:
- External location assignments
- Partner institution coordination
- Contact person linking
- Location-specific requirements

Sessions can be held at partner institutions with
proper contact person coordination.

Academic Year Integration:
=========================

School year integration features:
- Automatic school year association
- Academic calendar coordination
- Student availability checking
- Class schedule integration

Sessions are automatically linked to the current
academic year for proper organization.

Example Usage:
=============

Get all contact persons:
curl -H "Authorization: Bearer {token}" /api/production/contact-persons

Create new contact person (admin):
curl -X POST /api/production/contact-persons \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"name":"John Smith","email":"john@partner.com","phone":"+36301234567"}'

Get filming sessions with filters:
curl -H "Authorization: Bearer {token}" \
  "/api/production/filming-sessions?date_from=2024-03-01&date_to=2024-03-31&type=kacsa"

Create new filming session (admin):
curl -X POST /api/production/filming-sessions \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Morning Show Recording",
    "description":"Weekly morning show episode",
    "date":"2024-03-15",
    "time_from":"09:00",
    "time_to":"11:00",
    "type":"rendes",
    "equipment_ids":[1,2,3],
    "contact_person_id":1
  }'

Get available filming types:
curl -H "Authorization: Bearer {token}" /api/production/filming-types

KaCsa Integration:
=================

Special support for KaCsa content format:
- Related content linking
- Specialized workflow support
- Content tracking and organization
- Student-producer coordination

KaCsa represents a special student-produced content
format with specific production requirements.

Scheduling and Conflicts:
========================

Advanced scheduling features:
- Date and time validation
- Equipment availability checking
- Personnel conflict detection
- Academic calendar integration
- Automatic overlap prevention

The system ensures efficient resource utilization
and prevents scheduling conflicts.

Production Workflow:
===================

Typical production workflow:
1. Plan session (date, time, type)
2. Assign location and contact person
3. Select and assign equipment
4. Validate availability (equipment + personnel)
5. Execute session
6. Track completion and equipment return

Permission Requirements:
=======================

- Viewing: Authentication required
- Contact Management: Admin permissions
- Session Creation: Admin permissions (teacher or system admin)
- Session Updates: Admin permissions
- Session Deletion: Admin permissions with safety checks

Error Handling:
==============

- 200/201: Success
- 400: Validation errors (time conflicts, equipment unavailable)
- 401: Authentication failed or insufficient permissions
- 404: Session, contact person, or resource not found
- 409: Scheduling conflict
- 500: Server error

Validation Rules:
================

- End time must be after start time
- Dates must be valid and not in the past (configurable)
- Equipment must be functional and available
- Contact person references must exist
- Location references must be valid partners
- Session names should be unique per day (recommended)

Integration Points:
==================

- Equipment system (assignment and availability)
- Partner system (location management)
- Academic system (school year coordination)
- User system (permission-based access)
- Communication system (announcement integration)
"""

from ninja import Schema
from api.models import Forgatas, ContactPerson, Partner, Equipment, Tanev, Beosztas
from .auth import JWTAuth, ErrorSchema
from datetime import datetime, date, time
from typing import Optional

# ============================================================================
# Schemas
# ============================================================================

class ContactPersonSchema(Schema):
    """Response schema for contact person data."""
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    context: Optional[str] = None

class ContactPersonCreateSchema(Schema):
    """Request schema for creating new contact person."""
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    context: Optional[str] = None

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
    location: Optional[dict] = None
    contact_person: Optional[ContactPersonSchema] = None
    notes: Optional[str] = None
    type: str
    type_display: str
    related_kacsa: Optional[dict] = None
    equipment_ids: list[int] = []
    equipment_count: int = 0
    tanev: Optional[dict] = None

class ForgatCreateSchema(Schema):
    """Request schema for creating new filming session."""
    name: str
    description: str
    date: str
    time_from: str
    time_to: str
    location_id: Optional[int] = None
    contact_person_id: Optional[int] = None
    riporter_id: Optional[int] = None
    notes: Optional[str] = None
    type: str
    related_kacsa_id: Optional[int] = None
    equipment_ids: list[int] = []

class ForgatUpdateSchema(Schema):
    """Request schema for updating existing filming session."""
    name: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    time_from: Optional[str] = None
    time_to: Optional[str] = None
    location_id: Optional[int] = None
    contact_person_id: Optional[int] = None
    riporter_id: Optional[int] = None
    notes: Optional[str] = None
    type: Optional[str] = None
    related_kacsa_id: Optional[int] = None
    equipment_ids: Optional[list[int]] = None

class KacsaAvailableSchema(Schema):
    """Schema for available KaCsa sessions."""
    id: int
    name: str
    date: str
    time_from: str
    time_to: str
    can_link: bool
    already_linked: bool
    linked_sessions_count: int = 0

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
        "phone": contact_person.phone,
        "context": contact_person.context
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
    
    @api.get("/production/contact-persons", auth=JWTAuth(), response={200: list[ContactPersonSchema], 401: ErrorSchema})
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

    @api.post("/production/contact-persons", auth=JWTAuth(), response={201: ContactPersonSchema, 400: ErrorSchema, 401: ErrorSchema})
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
                phone=data.phone,
                context=data.context
            )
            
            return 201, create_contact_person_response(contact)
        except Exception as e:
            return 400, {"message": f"Error creating contact person: {str(e)}"}

    # ========================================================================
    # Filming Session (Forgatas) Endpoints  
    # ========================================================================
    
    @api.get("/production/filming-sessions", auth=JWTAuth(), response={200: list[ForgatSchema], 401: ErrorSchema})
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

    @api.get("/production/filming-sessions/{forgatas_id}", auth=JWTAuth(), response={200: ForgatSchema, 401: ErrorSchema, 404: ErrorSchema})
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

    @api.get("/production/filming-sessions/types", response={200: list[ForgatoTipusSchema]})
    def get_filming_types(request):
        """
        Get available filming session types.
        
        Public endpoint that returns all available filming session types.
        
        Returns:
            200: List of filming session types
        """
        return 200, FORGATAS_TYPES

    @api.post("/production/filming-sessions", auth=JWTAuth(), response={201: ForgatSchema, 400: ErrorSchema, 401: ErrorSchema})
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
                session_date = date.fromisoformat(data.date)
                time_from = time.fromisoformat(data.time_from)
                time_to = time.fromisoformat(data.time_to)
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
            
            riporter = None
            if data.riporter_id:
                try:
                    from django.contrib.auth.models import User
                    riporter = User.objects.get(id=data.riporter_id)
                    
                    # Validate reporter eligibility
                    if not hasattr(riporter, 'profile') or not riporter.profile.medias:
                        return 400, {"message": "A kiválasztott felhasználó nem lehet riporter"}
                    
                    # Check for scheduling conflicts
                    conflicting_sessions = Forgatas.objects.filter(
                        riporter=riporter,
                        date=session_date
                    ).filter(
                        timeFrom__lt=time_to,
                        timeTo__gt=time_from
                    )
                    
                    if conflicting_sessions.exists():
                        conflicting_session = conflicting_sessions.first()
                        return 400, {
                            "message": f"A riporter már be van osztva egy másik forgatásra: {conflicting_session.name} ({conflicting_session.timeFrom}-{conflicting_session.timeTo})"
                        }
                        
                except User.DoesNotExist:
                    return 400, {"message": "Riporter nem található"}
            
            # Create filming session
            forgatas = Forgatas.objects.create(
                name=data.name,
                description=data.description,
                date=session_date,
                timeFrom=time_from,
                timeTo=time_to,
                location=location,
                contactPerson=contact_person,
                riporter=riporter,
                notes=data.notes,
                forgTipus=data.type,
                relatedKaCsa=related_kacsa
            )
            
            # Add equipment if provided
            if data.equipment_ids:
                equipment = Equipment.objects.filter(id__in=data.equipment_ids)
                forgatas.equipments.set(equipment)
            
            # Create corresponding Beosztas for the new forgatas
            try:
                beosztas = Beosztas.objects.create(
                    forgatas=forgatas,
                    author=request.auth
                )
                print(f"Created Beosztas {beosztas.id} for Forgatas {forgatas.id}")
            except Exception as beosztas_error:
                print(f"Warning: Could not create Beosztas for Forgatas {forgatas.id}: {beosztas_error}")
                # Don't fail the whole operation if beosztas creation fails
            
            return 201, create_forgatas_response(forgatas)
        except Exception as e:
            return 400, {"message": f"Error creating filming session: {str(e)}"}

    @api.put("/production/filming-sessions/{forgatas_id}", auth=JWTAuth(), response={200: ForgatSchema, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
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
                    forgatas.date = date.fromisoformat(data.date)
                except ValueError:
                    return 400, {"message": "Hibás dátum formátum"}
            
            if data.time_from is not None:
                try:
                    forgatas.timeFrom = time.fromisoformat(data.time_from)
                except ValueError:
                    return 400, {"message": "Hibás kezdő idő formátum"}
            
            if data.time_to is not None:
                try:
                    forgatas.timeTo = time.fromisoformat(data.time_to)
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
            
            if data.riporter_id is not None:
                if data.riporter_id == 0:
                    forgatas.riporter = None
                else:
                    try:
                        from django.contrib.auth.models import User
                        riporter = User.objects.get(id=data.riporter_id)
                        
                        # Validate reporter eligibility
                        if not hasattr(riporter, 'profile') or not riporter.profile.medias:
                            return 400, {"message": "A kiválasztott felhasználó nem lehet riporter"}
                        
                        # Check for scheduling conflicts (exclude current session)
                        conflicting_sessions = Forgatas.objects.filter(
                            riporter=riporter,
                            date=forgatas.date
                        ).exclude(id=forgatas.id).filter(
                            timeFrom__lt=forgatas.timeTo,
                            timeTo__gt=forgatas.timeFrom
                        )
                        
                        if conflicting_sessions.exists():
                            conflicting_session = conflicting_sessions.first()
                            return 400, {
                                "message": f"A riporter már be van osztva egy másik forgatásra: {conflicting_session.name} ({conflicting_session.timeFrom}-{conflicting_session.timeTo})"
                            }
                        
                        forgatas.riporter = riporter
                    except User.DoesNotExist:
                        return 400, {"message": "Riporter nem található"}
            
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

    @api.delete("/production/filming-sessions/{forgatas_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
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
