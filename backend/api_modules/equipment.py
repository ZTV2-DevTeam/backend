"""
FTV Equipment Management API Module

This module provides comprehensive equipment and equipment type management functionality
for the FTV system, including inventory tracking, availability checking, and maintenance status.

Public API Overview:
==================

The Equipment API manages the school's media equipment inventory, providing endpoints
for equipment types, individual equipment items, and availability tracking for filming sessions.

Base URL: /api/

Protected Endpoints (JWT Token Required):

Equipment Types:
- GET  /equipment-types         - List all equipment types with counts
- POST /equipment-types         - Create new equipment type (admin only)

Equipment Items:
- GET  /equipment              - List all equipment (with optional filters)
- GET  /equipment/{id}         - Get specific equipment details
- POST /equipment              - Create new equipment item (admin only)
- PUT  /equipment/{id}         - Update equipment item (admin only)
- DELETE /equipment/{id}       - Delete equipment item (admin only)
- GET  /equipment/{id}/availability - Check equipment availability

Equipment Type System:
=====================

Equipment types categorize different kinds of media equipment:
- Cameras, Audio equipment, Lighting, etc.
- Optional emoji icons for visual identification
- Automatic equipment count tracking per type
- Used for filtering and organization

Equipment Management:
====================

Individual equipment items track:
- Unique nicknames for easy identification
- Brand and model information
- Serial numbers for asset tracking
- Functional status for maintenance management
- Optional notes for additional information
- Equipment type classification

Data Structure:
==============

Equipment Type (EquipmentTipus):
- id: Unique identifier
- name: Type name (e.g., "Kamera", "Mikrofon")
- emoji: Optional visual icon
- equipment_count: Number of items of this type

Equipment Item:
- id: Unique identifier
- nickname: User-friendly name (required)
- brand: Manufacturer name (optional)
- model: Equipment model (optional)
- serial_number: Asset tracking number (optional)
- equipment_type: Associated type classification
- functional: Working status flag
- notes: Additional information (optional)
- display_name: Auto-generated display name

Availability System:
===================

Equipment availability checking considers:
- Functional status (broken equipment unavailable)
- Current filming session assignments
- Date/time range conflicts
- Maintenance periods (if implemented)

The system integrates with filming sessions to prevent double-booking
and ensure equipment is available when needed.

Example Usage:
=============

Get all equipment types:
curl -H "Authorization: Bearer {token}" /api/equipment-types

Create new equipment type (admin):
curl -X POST /api/equipment-types \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"name":"Kamera","emoji":"📹"}'

Get all functional equipment:
curl -H "Authorization: Bearer {token}" "/api/equipment?functional_only=true"

Create new equipment (admin):
curl -X POST /api/equipment \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"nickname":"Main Camera","brand":"Canon","model":"XA40","equipment_type_id":1,"functional":true}'

Check equipment availability:
curl -H "Authorization: Bearer {token}" \
  "/api/equipment/1/availability?start_datetime=2024-03-15T14:00:00Z&end_datetime=2024-03-15T16:00:00Z"

Maintenance and Status Tracking:
===============================

Equipment functional status:
- functional: true = Equipment is working and available
- functional: false = Equipment is broken or under maintenance
- Broken equipment is automatically excluded from availability
- Status updates require admin permissions

Serial Number Management:
========================

Serial numbers support asset tracking:
- Optional field for institutional inventory
- Helps with warranty and maintenance tracking
- Useful for insurance and audit purposes
- Can be used for equipment identification

Integration Points:
==================

The equipment system integrates with:
- Filming session management (equipment assignment)
- User permissions (admin access control)
- Availability checking for scheduling
- Inventory tracking and reporting

Permission Requirements:
=======================

- Viewing: Authentication required
- Creating: Admin permissions (teacher or system admin)
- Updating: Admin permissions
- Deleting: Admin permissions (with usage checking)
- Availability: Authentication required

Error Handling:
==============

- 200/201: Success
- 400: Validation errors (duplicate names, invalid references, equipment in use)
- 401: Authentication failed or insufficient permissions
- 404: Equipment or equipment type not found
- 500: Server error

Validation Rules:
================

Equipment Types:
- Names must be unique across the system
- Emoji field accepts single emoji characters
- Deletion prevented if equipment items exist

Equipment Items:
- Nicknames must be unique for easy identification
- Serial numbers should be unique if provided
- Equipment type references must exist
- Functional status affects availability calculations
"""

from ninja import Schema
from api.models import Equipment, EquipmentTipus
from .auth import JWTAuth, ErrorSchema
from datetime import datetime
from typing import Optional

# ============================================================================
# Schemas
# ============================================================================

class EquipmentTipusSchema(Schema):
    """Response schema for equipment type data."""
    id: int
    name: str
    emoji: Optional[str] = None
    equipment_count: int = 0

class EquipmentTipusCreateSchema(Schema):
    """Request schema for creating new equipment type."""
    name: str
    emoji: Optional[str] = None

class EquipmentSchema(Schema):
    """Response schema for equipment data."""
    id: int
    nickname: str
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    equipment_type: Optional[EquipmentTipusSchema] = None
    functional: bool
    notes: Optional[str] = None
    display_name: str

class EquipmentCreateSchema(Schema):
    """Request schema for creating new equipment."""
    nickname: str
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    equipment_type_id: Optional[int] = None
    functional: bool = True
    notes: Optional[str] = None

class EquipmentUpdateSchema(Schema):
    """Request schema for updating existing equipment."""
    nickname: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    equipment_type_id: Optional[int] = None
    functional: Optional[bool] = None
    notes: Optional[str] = None

class EquipmentAvailabilitySchema(Schema):
    """Response schema for equipment availability."""
    equipment_id: int
    available: bool
    conflicts: list[dict] = []

class EquipmentScheduleSchema(Schema):
    """Response schema for equipment schedule."""
    equipment_id: int
    equipment_name: str
    schedule: list[dict] = []

class EquipmentUsageSchema(Schema):
    """Response schema for equipment usage statistics."""
    equipment_id: int
    equipment_name: str
    total_bookings: int
    upcoming_bookings: int
    usage_hours: float
    most_recent_use: Optional[str] = None
    next_booking: Optional[dict] = None

# ============================================================================
# Utility Functions
# ============================================================================

def create_equipment_tipus_response(equipment_tipus: EquipmentTipus) -> dict:
    """
    Create standardized equipment type response dictionary.
    
    Args:
        equipment_tipus: EquipmentTipus model instance
        
    Returns:
        Dictionary with equipment type information
    """
    return {
        "id": equipment_tipus.id,
        "name": equipment_tipus.name,
        "emoji": equipment_tipus.emoji,
        "equipment_count": equipment_tipus.equipments.count()
    }

def create_equipment_response(equipment: Equipment) -> dict:
    """
    Create standardized equipment response dictionary.
    
    Args:
        equipment: Equipment model instance
        
    Returns:
        Dictionary with equipment information
    """
    return {
        "id": equipment.id,
        "nickname": equipment.nickname,
        "brand": equipment.brand,
        "model": equipment.model,
        "serial_number": equipment.serialNumber,
        "equipment_type": create_equipment_tipus_response(equipment.equipmentType) if equipment.equipmentType else None,
        "functional": equipment.functional,
        "notes": equipment.notes,
        "display_name": str(equipment)
    }

def check_admin_permissions(user) -> tuple[bool, str]:
    """
    Check if user has admin permissions for equipment management.
    
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

def register_equipment_endpoints(api):
    """Register all equipment-related endpoints with the API router."""
    
    # ========================================================================
    # Equipment Type Endpoints
    # ========================================================================
    
    @api.get("/equipment-types", auth=JWTAuth(), response={200: list[EquipmentTipusSchema], 401: ErrorSchema})
    def get_equipment_types(request):
        """
        Get all equipment types.
        
        Requires authentication. Returns all equipment types with their
        basic information and equipment counts.
        
        Returns:
            200: List of all equipment types
            401: Authentication failed
        """
        try:
            equipment_types = EquipmentTipus.objects.prefetch_related('equipments').all()
            
            response = []
            for equipment_type in equipment_types:
                response.append(create_equipment_tipus_response(equipment_type))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching equipment types: {str(e)}"}

    @api.post("/equipment-types", auth=JWTAuth(), response={201: EquipmentTipusSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_equipment_type(request, data: EquipmentTipusCreateSchema):
        """
        Create new equipment type.
        
        Requires admin permissions. Creates a new equipment type.
        
        Args:
            data: Equipment type creation data
            
        Returns:
            201: Equipment type created successfully
            400: Invalid data or duplicate name
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            equipment_type = EquipmentTipus.objects.create(
                name=data.name,
                emoji=data.emoji
            )
            
            return 201, create_equipment_tipus_response(equipment_type)
        except Exception as e:
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                return 400, {"message": "Ezzel a névvel már létezik eszköz típus"}
            return 400, {"message": f"Error creating equipment type: {str(e)}"}

    @api.delete("/equipment-types/{type_id}", auth=JWTAuth(), response={200: dict, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
    def delete_equipment_type(request, type_id: int):
        """
        Delete equipment type.
        
        Requires admin permissions. Permanently removes equipment type from database.
        Note: This will fail if equipment items are still using this type.
        
        Args:
            type_id: Unique equipment type identifier
            
        Returns:
            200: Equipment type deleted successfully
            400: Equipment type has associated equipment items
            404: Equipment type not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            equipment_type = EquipmentTipus.objects.get(id=type_id)
            
            # Check if there are any equipment items using this type
            equipment_count = equipment_type.equipments.count()
            if equipment_count > 0:
                return 400, {"message": f"Nem törölhető az eszköz típus, mert {equipment_count} eszköz használja"}
            
            type_name = equipment_type.name
            equipment_type.delete()
            
            return 200, {"message": f"Eszköz típus '{type_name}' sikeresen törölve"}
        except EquipmentTipus.DoesNotExist:
            return 404, {"message": "Eszköz típus nem található"}
        except Exception as e:
            return 400, {"message": f"Error deleting equipment type: {str(e)}"}

    # ========================================================================
    # Equipment Endpoints
    # ========================================================================
    
    @api.get("/equipment", auth=JWTAuth(), response={200: list[EquipmentSchema], 401: ErrorSchema})
    def get_equipment(request, functional_only: bool = None):
        """
        Get all equipment.
        
        Requires authentication. Returns all equipment with their
        detailed information including type and functionality status.
        
        Args:
            functional_only: Optional filter for functional equipment only
            
        Returns:
            200: List of all equipment
            401: Authentication failed
        """
        try:
            equipment = Equipment.objects.select_related('equipmentType').all()
            
            if functional_only is not None:
                equipment = equipment.filter(functional=functional_only)
            
            response = []
            for equip in equipment:
                response.append(create_equipment_response(equip))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching equipment: {str(e)}"}

    @api.get("/equipment/{equipment_id}", auth=JWTAuth(), response={200: EquipmentSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_equipment_details(request, equipment_id: int):
        """
        Get single equipment by ID.
        
        Requires authentication. Returns detailed information about specific equipment.
        
        Args:
            equipment_id: Unique equipment identifier
            
        Returns:
            200: Equipment details
            404: Equipment not found
            401: Authentication failed
        """
        try:
            equipment = Equipment.objects.select_related('equipmentType').get(id=equipment_id)
            return 200, create_equipment_response(equipment)
        except Equipment.DoesNotExist:
            return 404, {"message": "Eszköz nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching equipment: {str(e)}"}

    @api.get("/equipment/by-type/{type_id}", auth=JWTAuth(), response={200: list[EquipmentSchema], 401: ErrorSchema, 404: ErrorSchema})
    def get_equipment_by_type(request, type_id: int, functional_only: bool = None):
        """
        Get equipment by type.
        
        Requires authentication. Returns all equipment of a specific type.
        
        Args:
            type_id: Equipment type identifier
            functional_only: Optional filter for functional equipment only
            
        Returns:
            200: List of equipment of specified type
            404: Equipment type not found
            401: Authentication failed
        """
        try:
            # Verify equipment type exists
            equipment_type = EquipmentTipus.objects.get(id=type_id)
            
            equipment = Equipment.objects.select_related('equipmentType').filter(
                equipmentType=equipment_type
            )
            
            if functional_only is not None:
                equipment = equipment.filter(functional=functional_only)
            
            response = []
            for equip in equipment:
                response.append(create_equipment_response(equip))
            
            return 200, response
        except EquipmentTipus.DoesNotExist:
            return 404, {"message": "Eszköz típus nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching equipment by type: {str(e)}"}

    @api.post("/equipment", auth=JWTAuth(), response={201: EquipmentSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_equipment(request, data: EquipmentCreateSchema):
        """
        Create new equipment.
        
        Requires admin permissions. Creates new equipment with specified parameters.
        
        Args:
            data: Equipment creation data
            
        Returns:
            201: Equipment created successfully
            400: Invalid data or duplicate nickname/serial
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Get equipment type if provided
            equipment_type = None
            if data.equipment_type_id:
                try:
                    equipment_type = EquipmentTipus.objects.get(id=data.equipment_type_id)
                except EquipmentTipus.DoesNotExist:
                    return 400, {"message": "Eszköz típus nem található"}
            
            equipment = Equipment.objects.create(
                nickname=data.nickname,
                brand=data.brand,
                model=data.model,
                serialNumber=data.serial_number,
                equipmentType=equipment_type,
                functional=data.functional,
                notes=data.notes
            )
            
            return 201, create_equipment_response(equipment)
        except Exception as e:
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                if "nickname" in str(e):
                    return 400, {"message": "Ezzel a becenévvel már létezik eszköz"}
                elif "serial" in str(e):
                    return 400, {"message": "Ezzel a sorozatszámmal már létezik eszköz"}
                return 400, {"message": "Egyedi mező duplikáció"}
            return 400, {"message": f"Error creating equipment: {str(e)}"}

    @api.put("/equipment/{equipment_id}", auth=JWTAuth(), response={200: EquipmentSchema, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
    def update_equipment(request, equipment_id: int, data: EquipmentUpdateSchema):
        """
        Update existing equipment.
        
        Requires admin permissions. Updates equipment information with provided data.
        Only non-None fields are updated.
        
        Args:
            equipment_id: Unique equipment identifier
            data: Equipment update data
            
        Returns:
            200: Equipment updated successfully
            404: Equipment not found
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            equipment = Equipment.objects.get(id=equipment_id)
            
            # Update fields only if they are provided (not None)
            if data.nickname is not None:
                equipment.nickname = data.nickname
            if data.brand is not None:
                equipment.brand = data.brand
            if data.model is not None:
                equipment.model = data.model
            if data.serial_number is not None:
                equipment.serialNumber = data.serial_number
            if data.functional is not None:
                equipment.functional = data.functional
            if data.notes is not None:
                equipment.notes = data.notes
            if data.equipment_type_id is not None:
                try:
                    equipment_type = EquipmentTipus.objects.get(id=data.equipment_type_id)
                    equipment.equipmentType = equipment_type
                except EquipmentTipus.DoesNotExist:
                    return 400, {"message": "Eszköz típus nem található"}
            
            equipment.save()
            
            return 200, create_equipment_response(equipment)
        except Equipment.DoesNotExist:
            return 404, {"message": "Eszköz nem található"}
        except Exception as e:
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                if "nickname" in str(e):
                    return 400, {"message": "Ezzel a becenévvel már létezik eszköz"}
                elif "serial" in str(e):
                    return 400, {"message": "Ezzel a sorozatszámmal már létezik eszköz"}
            return 400, {"message": f"Error updating equipment: {str(e)}"}

    @api.delete("/equipment/{equipment_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
    def delete_equipment(request, equipment_id: int):
        """
        Delete equipment.
        
        Requires admin permissions. Permanently removes equipment from database.
        Note: This may fail if equipment is referenced by filming sessions.
        
        Args:
            equipment_id: Unique equipment identifier
            
        Returns:
            200: Equipment deleted successfully
            404: Equipment not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            equipment = Equipment.objects.get(id=equipment_id)
            equipment_name = equipment.nickname
            equipment.delete()
            
            return 200, {"message": f"Eszköz '{equipment_name}' sikeresen törölve"}
        except Equipment.DoesNotExist:
            return 404, {"message": "Eszköz nem található"}
        except Exception as e:
            return 400, {"message": f"Error deleting equipment: {str(e)}"}

    @api.get("/equipment/{equipment_id}/availability", auth=JWTAuth(), response={200: EquipmentAvailabilitySchema, 401: ErrorSchema, 404: ErrorSchema})
    def check_equipment_availability(request, equipment_id: int, start_date: str, start_time: str, end_date: str = None, end_time: str = None):
        """
        Check equipment availability during specific time period.
        
        Requires authentication. Checks if equipment is available during the
        specified time range, considering filming sessions.
        
        Args:
            equipment_id: Unique equipment identifier
            start_date: Start date (YYYY-MM-DD format)
            start_time: Start time (HH:MM format)
            end_date: End date (YYYY-MM-DD format, defaults to start_date)
            end_time: End time (HH:MM format, defaults to start_time + 1 hour)
            
        Returns:
            200: Availability status with conflict details
            404: Equipment not found
            401: Authentication failed
            400: Invalid date/time format
        """
        try:
            equipment = Equipment.objects.get(id=equipment_id)
            
            # Parse dates and times
            try:
                from datetime import datetime, date, time
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                start_time_obj = datetime.strptime(start_time, '%H:%M').time()
                
                if end_date:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                else:
                    end_date_obj = start_date_obj
                    
                if end_time:
                    end_time_obj = datetime.strptime(end_time, '%H:%M').time()
                else:
                    # Default to 1 hour later
                    from datetime import timedelta
                    start_datetime = datetime.combine(start_date_obj, start_time_obj)
                    end_datetime = start_datetime + timedelta(hours=1)
                    end_time_obj = end_datetime.time()
                    
            except ValueError as e:
                return 400, {"message": f"Hibás dátum/idő formátum: {str(e)}"}
            
            # Check availability
            is_available = equipment.is_available_for(start_date_obj, start_time_obj, end_date_obj, end_time_obj)
            
            # Get conflicts if not available
            conflicts = []
            if not is_available or not equipment.functional:
                if not equipment.functional:
                    conflicts.append({
                        "type": "non_functional",
                        "reason": "Az eszköz nem működőképes",
                        "notes": equipment.notes
                    })
                    
                # Get overlapping bookings
                overlapping_bookings = equipment.get_bookings_for_period(start_date_obj, end_date_obj)
                for booking in overlapping_bookings:
                    # Check for actual time overlap
                    booking_conflicts = False
                    if booking.date == start_date_obj == end_date_obj:
                        if booking.timeFrom < end_time_obj and booking.timeTo > start_time_obj:
                            booking_conflicts = True
                    elif booking.date == start_date_obj:
                        if booking.timeTo > start_time_obj:
                            booking_conflicts = True
                    elif booking.date == end_date_obj:
                        if booking.timeFrom < end_time_obj:
                            booking_conflicts = True
                    elif start_date_obj < booking.date < end_date_obj:
                        booking_conflicts = True
                        
                    if booking_conflicts:
                        conflicts.append({
                            "type": "filming_session",
                            "forgatas_id": booking.id,
                            "forgatas_name": booking.name,
                            "date": booking.date.isoformat(),
                            "time_from": booking.timeFrom.isoformat(),
                            "time_to": booking.timeTo.isoformat(),
                            "location": booking.location.name if booking.location else None,
                            "type_display": dict(booking.tipusok).get(booking.forgTipus, booking.forgTipus)
                        })
            
            return 200, {
                "equipment_id": equipment_id,
                "available": is_available and equipment.functional,
                "conflicts": conflicts
            }
            
        except Equipment.DoesNotExist:
            return 404, {"message": "Eszköz nem található"}
        except Exception as e:
            return 401, {"message": f"Error checking equipment availability: {str(e)}"}

    @api.get("/equipment/{equipment_id}/schedule", auth=JWTAuth(), response={200: EquipmentScheduleSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_equipment_schedule(request, equipment_id: int, start_date: str, end_date: str = None):
        """
        Get equipment booking schedule for a date range.
        
        Requires authentication. Returns detailed schedule showing when equipment
        is booked and for which filming sessions.
        
        Args:
            equipment_id: Unique equipment identifier
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format, defaults to start_date)
            
        Returns:
            200: Equipment schedule with booking details
            404: Equipment not found
            401: Authentication failed
            400: Invalid date format
        """
        try:
            equipment = Equipment.objects.get(id=equipment_id)
            
            # Parse dates
            try:
                from datetime import datetime
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                if end_date:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                else:
                    end_date_obj = start_date_obj
            except ValueError as e:
                return 400, {"message": f"Hibás dátum formátum: {str(e)}"}
            
            # Get schedule
            schedule = equipment.get_availability_schedule(start_date_obj, end_date_obj)
            
            return 200, {
                "equipment_id": equipment_id,
                "equipment_name": equipment.nickname,
                "schedule": schedule
            }
            
        except Equipment.DoesNotExist:
            return 404, {"message": "Eszköz nem található"}
        except Exception as e:
            return 401, {"message": f"Error getting equipment schedule: {str(e)}"}

    @api.get("/equipment/{equipment_id}/usage", auth=JWTAuth(), response={200: EquipmentUsageSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_equipment_usage(request, equipment_id: int, days_back: int = 30):
        """
        Get equipment usage statistics.
        
        Requires authentication. Returns usage statistics including total bookings,
        usage hours, and recent activity.
        
        Args:
            equipment_id: Unique equipment identifier
            days_back: Number of days to look back for statistics (default 30)
            
        Returns:
            200: Equipment usage statistics
            404: Equipment not found
            401: Authentication failed
        """
        try:
            equipment = Equipment.objects.get(id=equipment_id)
            
            from datetime import date, timedelta
            from django.utils import timezone
            
            # Calculate date range
            today = date.today()
            start_date = today - timedelta(days=days_back)
            
            # Get bookings in the period
            bookings = equipment.get_bookings_for_period(start_date, today)
            
            # Calculate statistics
            total_bookings = bookings.count()
            upcoming_bookings = equipment.forgatasok.filter(date__gt=today).count()
            
            # Calculate usage hours
            usage_hours = 0.0
            most_recent_use = None
            
            for booking in bookings:
                # Calculate duration in hours
                from datetime import datetime, timedelta
                start_datetime = datetime.combine(booking.date, booking.timeFrom)
                end_datetime = datetime.combine(booking.date, booking.timeTo)
                duration = end_datetime - start_datetime
                usage_hours += duration.total_seconds() / 3600
                
                # Track most recent use
                if most_recent_use is None or booking.date > most_recent_use:
                    most_recent_use = booking.date
            
            # Get next booking
            next_booking_obj = equipment.forgatasok.filter(date__gt=today).order_by('date', 'timeFrom').first()
            next_booking = None
            if next_booking_obj:
                next_booking = {
                    "forgatas_id": next_booking_obj.id,
                    "forgatas_name": next_booking_obj.name,
                    "date": next_booking_obj.date.isoformat(),
                    "time_from": next_booking_obj.timeFrom.isoformat(),
                    "time_to": next_booking_obj.timeTo.isoformat(),
                    "location": next_booking_obj.location.name if next_booking_obj.location else None
                }
            
            return 200, {
                "equipment_id": equipment_id,
                "equipment_name": equipment.nickname,
                "total_bookings": total_bookings,
                "upcoming_bookings": upcoming_bookings,
                "usage_hours": round(usage_hours, 2),
                "most_recent_use": most_recent_use.isoformat() if most_recent_use else None,
                "next_booking": next_booking
            }
            
        except Equipment.DoesNotExist:
            return 404, {"message": "Eszköz nem található"}
        except Exception as e:
            return 401, {"message": f"Error getting equipment usage: {str(e)}"}

    @api.get("/equipment/availability-overview", auth=JWTAuth(), response={200: list[dict], 401: ErrorSchema})
    def get_equipment_availability_overview(request, date: str, type_id: int = None):
        """
        Get availability overview for all equipment on a specific date.
        
        Requires authentication. Returns availability status for all equipment,
        optionally filtered by equipment type.
        
        Args:
            date: Date to check (YYYY-MM-DD format)
            type_id: Optional equipment type filter
            
        Returns:
            200: List of equipment with availability status
            401: Authentication failed
            400: Invalid date format
        """
        try:
            # Parse date
            try:
                from datetime import datetime
                check_date = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError as e:
                return 400, {"message": f"Hibás dátum formátum: {str(e)}"}
            
            # Get equipment
            equipment_qs = Equipment.objects.select_related('equipmentType')
            if type_id:
                equipment_qs = equipment_qs.filter(equipmentType_id=type_id)
            
            equipment_list = equipment_qs.all()
            
            # Check availability for each equipment
            overview = []
            for equip in equipment_list:
                # Get bookings for this date
                bookings_today = equip.forgatasok.filter(date=check_date).order_by('timeFrom')
                
                booking_details = []
                for booking in bookings_today:
                    booking_details.append({
                        "forgatas_id": booking.id,
                        "forgatas_name": booking.name,
                        "time_from": booking.timeFrom.isoformat(),
                        "time_to": booking.timeTo.isoformat(),
                        "type": booking.forgTipus,
                        "location": booking.location.name if booking.location else None
                    })
                
                overview.append({
                    "equipment_id": equip.id,
                    "equipment_name": equip.nickname,
                    "equipment_type": equip.equipmentType.name if equip.equipmentType else None,
                    "functional": equip.functional,
                    "available_periods": bookings_today.count() == 0,  # Simplified - fully free day
                    "bookings": booking_details,
                    "booking_count": bookings_today.count()
                })
            
            return 200, overview
            
        except Exception as e:
            return 401, {"message": f"Error getting equipment availability overview: {str(e)}"}
