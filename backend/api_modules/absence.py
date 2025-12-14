"""
Absence management API endpoints.
Handles absences (Tavollet) and availability tracking.
"""

from ninja import Schema
from django.contrib.auth.models import User
from api.models import Tavollet, TavolletTipus
from .auth import JWTAuth, ErrorSchema
from datetime import datetime, date
from typing import Optional

# ============================================================================
# Utility Functions for Timezone Handling
# ============================================================================

def convert_to_local_naive_datetime(dt):
    """
    Convert a timezone-aware datetime to Europe/Budapest local time and make it naive.
    This is needed because USE_TZ=False and SQLite doesn't support timezone-aware datetimes.
    
    Args:
        dt: datetime object (timezone-aware or naive)
        
    Returns:
        naive datetime in Europe/Budapest timezone
    """
    if dt is None:
        return None
    
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        # Convert timezone-aware datetime to Europe/Budapest, then make naive
        from zoneinfo import ZoneInfo
        budapest_tz = ZoneInfo('Europe/Budapest')
        return dt.astimezone(budapest_tz).replace(tzinfo=None)
    
    # Already naive - assume it's in local time
    return dt

# ============================================================================
# Schemas
# ============================================================================

class UserBasicSchema(Schema):
    """Basic user information schema."""
    id: int
    username: str
    first_name: str
    last_name: str
    full_name: str

class TavolletTipusSchema(Schema):
    """Response schema for absence type data."""
    id: int
    name: str
    explanation: Optional[str] = None
    ignored_counts_as: str
    ignored_counts_as_display: str
    usage_count: int

class TavolletTipusCreateSchema(Schema):
    """Request schema for creating new absence type."""
    name: str
    explanation: Optional[str] = None
    ignored_counts_as: str  # 'approved' or 'denied'

class TavolletTipusUpdateSchema(Schema):
    """Request schema for updating existing absence type."""
    name: Optional[str] = None
    explanation: Optional[str] = None
    ignored_counts_as: Optional[str] = None

class TavolletTipusBasicSchema(Schema):
    """Basic absence type schema for inclusion in other responses."""
    id: int
    name: str
    ignored_counts_as: str

class TavolletSchema(Schema):
    """Response schema for absence data."""
    id: int
    user: UserBasicSchema
    start_date: str  # ISO datetime string
    end_date: str    # ISO datetime string
    reason: Optional[str] = None
    denied: bool
    approved: bool
    duration_days: int
    status: str
    tipus: Optional[TavolletTipusBasicSchema] = None
    teacher_reason: Optional[str] = None

class TavolletCreateSchema(Schema):
    """Request schema for creating new absence."""
    user_id: Optional[int] = None  # Optional - if not provided, uses current user
    start_date: str    # ISO datetime string
    end_date: str      # ISO datetime string
    reason: Optional[str] = None
    tipus_id: Optional[int] = None  # Optional absence type

class TavolletUpdateSchema(Schema):
    """Request schema for updating absence."""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    reason: Optional[str] = None
    denied: Optional[bool] = None
    approved: Optional[bool] = None
    tipus_id: Optional[int] = None
    teacher_reason: Optional[str] = None

class TeacherReasonSchema(Schema):
    """Request schema for updating teacher reason."""
    teacher_reason: str

class TavolletBulkCreateSchema(Schema):
    """Request schema for bulk creating absences."""
    user_ids: list[int]  # List of user IDs to create absences for
    start_date: str    # ISO datetime string
    end_date: str      # ISO datetime string
    reason: Optional[str] = None
    tipus_id: Optional[int] = None
    """Request schema for creating multiple absences for multiple users (admin only)."""
    user_ids: list[int]  # List of user IDs to create absences for
    start_date: str      # ISO datetime string
    end_date: str        # ISO datetime string
    reason: Optional[str] = None
    tipus_id: Optional[int] = None  # Optional absence type

class TavolletBulkCreateResponseSchema(Schema):
    """Response schema for bulk absence creation."""
    created_count: int
    absences: list[TavolletSchema]
    errors: Optional[list[str]] = None

# ============================================================================
# Utility Functions
# ============================================================================

def create_user_basic_response(user: User) -> dict:
    """
    Create basic user information response.
    
    Args:
        user: Django User object
        
    Returns:
        Dictionary with basic user information (no sensitive data)
    """
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.get_full_name()
    }

def create_tavollet_tipus_response(tipus: TavolletTipus) -> dict:
    """
    Create standardized absence type response dictionary.
    
    Args:
        tipus: TavolletTipus model instance
        
    Returns:
        Dictionary with absence type information
    """
    usage_count = Tavollet.objects.filter(tipus=tipus).count()
    
    return {
        "id": tipus.id,
        "name": tipus.name,
        "explanation": tipus.explanation,
        "ignored_counts_as": tipus.ignored_counts_as,
        "ignored_counts_as_display": tipus.get_ignored_counts_as_display(),
        "usage_count": usage_count
    }

def create_tavollet_tipus_basic_response(tipus: TavolletTipus) -> dict:
    """
    Create basic absence type response for inclusion in other responses.
    
    Args:
        tipus: TavolletTipus model instance
        
    Returns:
        Dictionary with basic absence type information
    """
    return {
        "id": tipus.id,
        "name": tipus.name,
        "ignored_counts_as": tipus.ignored_counts_as
    }

def create_tavollet_response(tavollet: Tavollet) -> dict:
    """
    Create standardized absence response dictionary.
    
    Args:
        tavollet: Tavollet model instance
        
    Returns:
        Dictionary with absence information
    """
    # Calculate duration in days (considering datetime fields)
    start_date = tavollet.start_date.date() if hasattr(tavollet.start_date, 'date') else tavollet.start_date
    end_date = tavollet.end_date.date() if hasattr(tavollet.end_date, 'date') else tavollet.end_date
    duration = (end_date - start_date).days + 1
    
    # Determine status based on approval/denial state and time
    current_datetime = datetime.now()
    # Ensure comparison compatibility by converting to local naive datetimes
    tavollet_end = convert_to_local_naive_datetime(tavollet.end_date)
    tavollet_start = convert_to_local_naive_datetime(tavollet.start_date)
    
    if tavollet.denied and tavollet.approved:
        # This shouldn't happen but handle it gracefully
        status = "konfliktus"  # Both flags set - should be fixed
    elif tavollet.denied:
        status = "elutasítva"
    elif tavollet.approved:
        status = "jóváhagyva"
    elif tavollet_end < current_datetime:
        status = "lezárt"
    elif tavollet_start <= current_datetime <= tavollet_end:
        status = "folyamatban"
    else:
        status = "függőben"  # Changed from "jövőbeli" to be more descriptive of pending approval
    
    # Include absence type information if available
    tipus_info = None
    if tavollet.tipus:
        tipus_info = create_tavollet_tipus_basic_response(tavollet.tipus)
    
    return {
        "id": tavollet.id,
        "user": create_user_basic_response(tavollet.user),
        "start_date": tavollet.start_date.isoformat(),
        "end_date": tavollet.end_date.isoformat(),
        "reason": tavollet.reason,
        "denied": tavollet.denied,
        "approved": tavollet.approved,
        "duration_days": duration,
        "status": status,
        "tipus": tipus_info,
        "teacher_reason": getattr(tavollet, 'teacher_reason', None)
    }

def check_admin_permissions(user) -> tuple[bool, str]:
    """
    Check if user has admin permissions for absence management.
    
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

def can_user_manage_absence(requesting_user: User, absence: Tavollet) -> bool:
    """
    Check if user can manage a specific absence.
    
    Args:
        requesting_user: User making the request
        absence: Tavollet instance
        
    Returns:
        Boolean indicating if user can manage the absence
    """
    # Own absence can be managed
    if absence.user.id == requesting_user.id:
        return True
    
    # Admin can manage any absence
    try:
        from api.models import Profile
        profile = Profile.objects.get(user=requesting_user)
        if profile.has_admin_permission('any'):
            return True
    except Profile.DoesNotExist:
        pass
    
    return False

# ============================================================================
# API Endpoints
# ============================================================================

def register_absence_endpoints(api):
    """Register all absence-related endpoints with the API router."""
    
    # ============================================================================
    # Absence Type (TavolletTipus) Endpoints
    # ============================================================================
    
    @api.get("/absence-types", auth=JWTAuth(), response={200: list[TavolletTipusSchema], 401: ErrorSchema})
    def get_absence_types(request):
        """
        Get all available absence types.
        
        Requires authentication. Returns all absence types with their settings.
        
        Returns:
            200: List of absence types
            401: Authentication failed
        """
        try:
            absence_types = TavolletTipus.objects.all().order_by('name')
            
            response = []
            for tipus in absence_types:
                response.append(create_tavollet_tipus_response(tipus))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching absence types: {str(e)}"}

    @api.get("/absence-types/{tipus_id}", auth=JWTAuth(), response={200: TavolletTipusSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_absence_type_details(request, tipus_id: int):
        """
        Get detailed information about a specific absence type.
        
        Requires authentication.
        
        Args:
            tipus_id: Unique absence type identifier
            
        Returns:
            200: Detailed absence type information
            404: Absence type not found
            401: Authentication failed
        """
        try:
            tipus = TavolletTipus.objects.get(id=tipus_id)
            return 200, create_tavollet_tipus_response(tipus)
        except TavolletTipus.DoesNotExist:
            return 404, {"message": "Távolléti típus nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching absence type details: {str(e)}"}

    @api.post("/absence-types", auth=JWTAuth(), response={201: TavolletTipusSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_absence_type(request, data: TavolletTipusCreateSchema):
        """
        Create new absence type.
        
        Requires admin permissions.
        
        Args:
            data: Absence type creation data
            
        Returns:
            201: Absence type created successfully
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Validate ignored_counts_as field
            if data.ignored_counts_as not in ['approved', 'denied']:
                return 400, {"message": "ignored_counts_as mező értéke 'approved' vagy 'denied' lehet csak"}
            
            # Check for duplicate name
            if TavolletTipus.objects.filter(name=data.name).exists():
                return 400, {"message": "Ilyen nevű távolléti típus már létezik"}
            
            # Create absence type
            tipus = TavolletTipus.objects.create(
                name=data.name,
                explanation=data.explanation,
                ignored_counts_as=data.ignored_counts_as
            )
            
            return 201, create_tavollet_tipus_response(tipus)
        except Exception as e:
            return 400, {"message": f"Error creating absence type: {str(e)}"}

    @api.put("/absence-types/{tipus_id}", auth=JWTAuth(), response={200: TavolletTipusSchema, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
    def update_absence_type(request, tipus_id: int, data: TavolletTipusUpdateSchema):
        """
        Update existing absence type.
        
        Requires admin permissions. Only non-None fields are updated.
        
        Args:
            tipus_id: Unique absence type identifier
            data: Absence type update data
            
        Returns:
            200: Absence type updated successfully
            404: Absence type not found
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            tipus = TavolletTipus.objects.get(id=tipus_id)
            
            # Update fields if provided
            if data.name is not None:
                # Check for duplicate name (excluding current)
                if TavolletTipus.objects.filter(name=data.name).exclude(id=tipus.id).exists():
                    return 400, {"message": "Ilyen nevű távolléti típus már létezik"}
                tipus.name = data.name
            
            if data.explanation is not None:
                tipus.explanation = data.explanation
            
            if data.ignored_counts_as is not None:
                if data.ignored_counts_as not in ['approved', 'denied']:
                    return 400, {"message": "ignored_counts_as mező értéke 'approved' vagy 'denied' lehet csak"}
                tipus.ignored_counts_as = data.ignored_counts_as
            
            tipus.save()
            
            return 200, create_tavollet_tipus_response(tipus)
        except TavolletTipus.DoesNotExist:
            return 404, {"message": "Távolléti típus nem található"}
        except Exception as e:
            return 400, {"message": f"Error updating absence type: {str(e)}"}

    @api.delete("/absence-types/{tipus_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema, 400: ErrorSchema})
    def delete_absence_type(request, tipus_id: int):
        """
        Delete absence type.
        
        Requires admin permissions. Cannot delete if type is being used by absences.
        
        Args:
            tipus_id: Unique absence type identifier
            
        Returns:
            200: Absence type deleted successfully
            404: Absence type not found
            400: Absence type is being used
            401: Authentication or permission failed
        """
        try:
            # Check admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            tipus = TavolletTipus.objects.get(id=tipus_id)
            
            # Check if type is being used
            usage_count = Tavollet.objects.filter(tipus=tipus).count()
            if usage_count > 0:
                return 400, {"message": f"Nem törölhető, mert {usage_count} távollét használja ezt a típust"}
            
            tipus_name = tipus.name
            tipus.delete()
            
            return 200, {"message": f"Távolléti típus '{tipus_name}' sikeresen törölve"}
        except TavolletTipus.DoesNotExist:
            return 404, {"message": "Távolléti típus nem található"}
        except Exception as e:
            return 400, {"message": f"Error deleting absence type: {str(e)}"}

    # ============================================================================
    # Absence (Tavollet) Endpoints
    # ============================================================================
    
    @api.get("/absences", auth=JWTAuth(), response={200: list[TavolletSchema], 401: ErrorSchema})
    def get_absences(request, user_id: int = None, start_date: str = None, end_date: str = None, my_absences: bool = False):
        """
        Get absences with optional filtering.
        
        Requires authentication. Returns absences visible to the user.
        Users can see their own absences, admins can see all.
        
        Args:
            user_id: Optional user filter (admin only)
            start_date: Optional start date filter (ISO format)
            end_date: Optional end date filter (ISO format)
            my_absences: If true, only return current user's absences
            
        Returns:
            200: List of absences
            401: Authentication failed
        """
        try:
            requesting_user = request.auth
            
            # Check admin permissions for viewing other users' absences
            has_admin_permission = False
            try:
                from api.models import Profile
                profile = Profile.objects.get(user=requesting_user)
                has_admin_permission = profile.has_admin_permission('any')
            except Profile.DoesNotExist:
                pass
            
            # Build queryset based on permissions
            if my_absences or (not has_admin_permission and user_id != requesting_user.id):
                # Regular user - only their own absences
                absences = Tavollet.objects.filter(user=requesting_user)
            elif user_id and has_admin_permission:
                # Admin requesting specific user's absences
                absences = Tavollet.objects.filter(user_id=user_id)
            elif has_admin_permission:
                # Admin requesting all absences
                absences = Tavollet.objects.all()
            else:
                # Regular user - only their own absences
                absences = Tavollet.objects.filter(user=requesting_user)
            
            # Apply date filters
            if start_date:
                absences = absences.filter(end_date__gte=start_date)
            if end_date:
                absences = absences.filter(start_date__lte=end_date)
            
            absences = absences.select_related('user', 'tipus').order_by('-start_date')
            
            response = []
            for absence in absences:
                response.append(create_tavollet_response(absence))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching absences: {str(e)}"}

    @api.get("/absences/{absence_id}", auth=JWTAuth(), response={200: TavolletSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_absence_details(request, absence_id: int):
        """
        Get detailed information about a specific absence.
        
        Requires authentication and proper permissions to view the absence.
        
        Args:
            absence_id: Unique absence identifier
            
        Returns:
            200: Detailed absence information
            404: Absence not found or no permission to view
            401: Authentication failed
        """
        try:
            requesting_user = request.auth
            absence = Tavollet.objects.select_related('user', 'tipus').get(id=absence_id)
            
            # Check if user can view this absence
            if not can_user_manage_absence(requesting_user, absence):
                return 404, {"message": "Távollét nem található vagy nincs jogosultság megtekintéséhez"}
            
            return 200, create_tavollet_response(absence)
        except Tavollet.DoesNotExist:
            return 404, {"message": "Távollét nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching absence details: {str(e)}"}

    @api.post("/absences", auth=JWTAuth(), response={201: TavolletSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_absence(request, data: TavolletCreateSchema):
        """
        Create new absence.
        
        Requires authentication. Users can create absences for themselves,
        admins can create absences for any user.
        
        Args:
            data: Absence creation data
            
        Returns:
            201: Absence created successfully
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            requesting_user = request.auth
            
            # Determine target user
            if data.user_id:
                # Creating for specific user - need admin permission
                has_admin_permission, error_message = check_admin_permissions(requesting_user)
                if not has_admin_permission:
                    return 401, {"message": error_message}
                
                try:
                    target_user = User.objects.get(id=data.user_id)
                except User.DoesNotExist:
                    return 400, {"message": "Felhasználó nem található"}
            else:
                # Creating for self
                target_user = requesting_user
            
            # Validate datetime strings
            try:
                start_datetime = datetime.fromisoformat(data.start_date.replace('Z', '+00:00'))
                end_datetime = datetime.fromisoformat(data.end_date.replace('Z', '+00:00'))
                
                # Convert to local naive datetimes for SQLite compatibility
                start_datetime = convert_to_local_naive_datetime(start_datetime)
                end_datetime = convert_to_local_naive_datetime(end_datetime)
                    
            except ValueError:
                return 400, {"message": "Hibás dátum/idő formátum. Használj ISO formátumot (pl. 2024-03-15T14:00:00)"}
            
            if start_datetime >= end_datetime:
                return 400, {"message": "A záró időpontnak a kezdő időpont után kell lennie"}
            
            # Check for overlapping absences using TavolletTipus logic
            overlapping_absences = Tavollet.objects.filter(
                user=target_user,
                start_date__lt=end_datetime,
                end_date__gt=start_datetime
            ).select_related('tipus')
            
            overlapping = False
            for absence in overlapping_absences:
                if absence.denied:
                    continue  # Denied absences don't count as conflicts
                elif absence.approved:
                    overlapping = True
                    break
                else:
                    # Pending absence - check tipus
                    if absence.tipus and absence.tipus.ignored_counts_as == 'denied':
                        continue  # Type defaults to denied - no conflict
                    else:
                        # No tipus or defaults to approved - conflict
                        overlapping = True
                        break
            
            if overlapping:
                return 400, {"message": "Átfedő távollét már létezik ebben az időszakban"}
            
            # Validate absence type if provided
            tipus = None
            if data.tipus_id:
                try:
                    tipus = TavolletTipus.objects.get(id=data.tipus_id)
                except TavolletTipus.DoesNotExist:
                    return 400, {"message": "Távolléti típus nem található"}
            
            # Create absence
            absence = Tavollet.objects.create(
                user=target_user,
                start_date=start_datetime,
                end_date=end_datetime,
                reason=data.reason,
                denied=False,
                approved=False,
                tipus=tipus
            )
            
            return 201, create_tavollet_response(absence)
        except Exception as e:
            return 400, {"message": f"Error creating absence: {str(e)}"}

    @api.post("/absences/bulk-create", auth=JWTAuth(), response={201: TavolletBulkCreateResponseSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_bulk_absences(request, data: TavolletBulkCreateSchema):
        """
        Create multiple absences for multiple users (admin only).
        
        Creates automatically approved absences for the selected users.
        This is an admin-only function used to create absences en masse.
        
        Args:
            data: Bulk absence creation data with user IDs
            
        Returns:
            201: Absences created successfully
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            requesting_user = request.auth
            
            # Only admins can create bulk absences
            has_admin_permission, error_message = check_admin_permissions(requesting_user)
            if not has_admin_permission:
                return 401, {"message": error_message}
            
            # Validate user IDs
            if not data.user_ids or len(data.user_ids) == 0:
                return 400, {"message": "Legalább egy felhasználót ki kell választani"}
            
            # Validate datetime strings
            try:
                start_datetime = datetime.fromisoformat(data.start_date.replace('Z', '+00:00'))
                end_datetime = datetime.fromisoformat(data.end_date.replace('Z', '+00:00'))
                
                # Convert to local naive datetimes for SQLite compatibility
                start_datetime = convert_to_local_naive_datetime(start_datetime)
                end_datetime = convert_to_local_naive_datetime(end_datetime)
                    
            except ValueError:
                return 400, {"message": "Hibás dátum/idő formátum. Használj ISO formátumot (pl. 2024-03-15T14:00:00)"}
            
            if start_datetime >= end_datetime:
                return 400, {"message": "A záró időpontnak a kezdő időpont után kell lennie"}
            
            # Validate absence type if provided
            tipus = None
            if data.tipus_id:
                try:
                    tipus = TavolletTipus.objects.get(id=data.tipus_id)
                except TavolletTipus.DoesNotExist:
                    return 400, {"message": "Távolléti típus nem található"}
            
            # Create absences for each user
            created_absences = []
            errors = []
            
            for user_id in data.user_ids:
                try:
                    # Get target user
                    try:
                        target_user = User.objects.get(id=user_id)
                    except User.DoesNotExist:
                        errors.append(f"Felhasználó ID {user_id} nem található")
                        continue
                    
                    # Check for overlapping absences (optional - we could skip this for admin-created absences)
                    overlapping_absences = Tavollet.objects.filter(
                        user=target_user,
                        start_date__lt=end_datetime,
                        end_date__gt=start_datetime
                    ).select_related('tipus')
                    
                    overlapping = False
                    for absence in overlapping_absences:
                        if absence.denied:
                            continue  # Denied absences don't count as conflicts
                        elif absence.approved:
                            overlapping = True
                            break
                        else:
                            # Pending absence - check tipus
                            if absence.tipus and absence.tipus.ignored_counts_as == 'denied':
                                continue  # Type defaults to denied - no conflict
                            else:
                                # No tipus or defaults to approved - conflict
                                overlapping = True
                                break
                    
                    if overlapping:
                        errors.append(f"Átfedő távollét már létezik {target_user.last_name} {target_user.first_name} részére")
                        continue
                    
                    # Create absence - automatically approved for admin-created absences
                    absence = Tavollet.objects.create(
                        user=target_user,
                        start_date=start_datetime,
                        end_date=end_datetime,
                        reason=data.reason,
                        denied=False,
                        approved=True,  # Automatically approved for admin-created absences
                        tipus=tipus
                    )
                    
                    created_absences.append(absence)
                    
                except Exception as e:
                    errors.append(f"Hiba {target_user.last_name} {target_user.first_name} részére: {str(e)}")
            
            # Prepare response
            response_absences = [create_tavollet_response(absence) for absence in created_absences]
            
            return 201, {
                "created_count": len(created_absences),
                "absences": response_absences,
                "errors": errors if errors else None
            }
            
        except Exception as e:
            return 400, {"message": f"Error creating bulk absences: {str(e)}"}

    @api.put("/absences/{absence_id}", auth=JWTAuth(), response={200: TavolletSchema, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
    def update_absence(request, absence_id: int, data: TavolletUpdateSchema):
        """
        Update existing absence.
        
        Requires proper permissions. Users can update their own absences,
        admins can update any absence. Only non-None fields are updated.
        
        Args:
            absence_id: Unique absence identifier
            data: Absence update data
            
        Returns:
            200: Absence updated successfully
            404: Absence not found
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            requesting_user = request.auth
            absence = Tavollet.objects.get(id=absence_id)
            
            # Check permissions
            if not can_user_manage_absence(requesting_user, absence):
                return 401, {"message": "Nincs jogosultság a távollét szerkesztéséhez"}
            
            # Update dates if provided
            updated_start_date = absence.start_date
            updated_end_date = absence.end_date
            
            if data.start_date is not None:
                try:
                    updated_start_date = datetime.fromisoformat(data.start_date.replace('Z', '+00:00'))
                    updated_start_date = convert_to_local_naive_datetime(updated_start_date)
                except ValueError:
                    return 400, {"message": "Hibás kezdő dátum/idő formátum. Használj ISO formátumot"}
            
            if data.end_date is not None:
                try:
                    updated_end_date = datetime.fromisoformat(data.end_date.replace('Z', '+00:00'))
                    updated_end_date = convert_to_local_naive_datetime(updated_end_date)
                except ValueError:
                    return 400, {"message": "Hibás záró dátum/idő formátum. Használj ISO formátumot"}
            
            # Validate datetime range
            if updated_start_date >= updated_end_date:
                return 400, {"message": "A záró időpontnak a kezdő időpont után kell lennie"}
            
            # Check for overlapping absences using TavolletTipus logic (excluding current one)
            overlapping_absences = Tavollet.objects.filter(
                user=absence.user,
                start_date__lt=updated_end_date,
                end_date__gt=updated_start_date
            ).exclude(id=absence.id).select_related('tipus')
            
            overlapping = False
            for other_absence in overlapping_absences:
                if other_absence.denied:
                    continue  # Denied absences don't count as conflicts
                elif other_absence.approved:
                    overlapping = True
                    break
                else:
                    # Pending absence - check tipus
                    if other_absence.tipus and other_absence.tipus.ignored_counts_as == 'denied':
                        continue  # Type defaults to denied - no conflict
                    else:
                        # No tipus or defaults to approved - conflict
                        overlapping = True
                        break
            
            if overlapping:
                return 400, {"message": "Átfedő távollét már létezik ebben az időszakban"}
            
            # Update fields
            if data.start_date is not None:
                absence.start_date = updated_start_date
            if data.end_date is not None:
                absence.end_date = updated_end_date
            if data.reason is not None:
                absence.reason = data.reason
            if data.denied is not None:
                # Only admins can change denied status
                has_admin_permission = False
                try:
                    from api.models import Profile
                    profile = Profile.objects.get(user=requesting_user)
                    has_admin_permission = profile.has_admin_permission('any')
                except Profile.DoesNotExist:
                    pass
                
                if has_admin_permission:
                    absence.denied = data.denied
                    # If denied is set to True, ensure approved is False
                    if data.denied:
                        absence.approved = False
                elif data.denied != absence.denied:
                    return 401, {"message": "Nincs jogosultság a státusz módosításához"}
            
            if data.approved is not None:
                # Only admins can change approved status
                has_admin_permission = False
                try:
                    from api.models import Profile
                    profile = Profile.objects.get(user=requesting_user)
                    has_admin_permission = profile.has_admin_permission('any')
                except Profile.DoesNotExist:
                    pass
                
                if has_admin_permission:
                    absence.approved = data.approved
                    # If approved is set to True, ensure denied is False
                    if data.approved:
                        absence.denied = False
                elif data.approved != absence.approved:
                    return 401, {"message": "Nincs jogosultság a státusz módosításához"}
            
            # Update absence type if provided
            if data.tipus_id is not None:
                if data.tipus_id == 0:
                    # Setting tipus_id to 0 means remove the type
                    absence.tipus = None
                else:
                    try:
                        tipus = TavolletTipus.objects.get(id=data.tipus_id)
                        absence.tipus = tipus
                    except TavolletTipus.DoesNotExist:
                        return 400, {"message": "Távolléti típus nem található"}
            
            absence.save()
            
            return 200, create_tavollet_response(absence)
        except Tavollet.DoesNotExist:
            return 404, {"message": "Távollét nem található"}
        except Exception as e:
            return 400, {"message": f"Error updating absence: {str(e)}"}

    @api.put("/absences/{absence_id}/approve", auth=JWTAuth(), response={200: TavolletSchema, 401: ErrorSchema, 404: ErrorSchema})
    def approve_absence(request, absence_id: int, payload: TeacherReasonSchema = None):
        """
        Approve absence (set approved=True, denied=False).
        
        Requires admin permissions. Approves an absence.
        
        Args:
            absence_id: Unique absence identifier
            payload: Optional TeacherReasonSchema with 'teacher_reason' field
            
        Returns:
            200: Absence approved successfully
            404: Absence not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            absence = Tavollet.objects.get(id=absence_id)
            absence.approved = True
            absence.denied = False  # Ensure mutual exclusivity
            
            # Update teacher reason if provided
            if payload and payload.teacher_reason:
                absence.teacher_reason = payload.teacher_reason
            
            absence.save()
            
            return 200, create_tavollet_response(absence)
        except Tavollet.DoesNotExist:
            return 404, {"message": "Távollét nem található"}
        except Exception as e:
            return 400, {"message": f"Error approving absence: {str(e)}"}

    @api.put("/absences/{absence_id}/deny", auth=JWTAuth(), response={200: TavolletSchema, 401: ErrorSchema, 404: ErrorSchema})
    def deny_absence(request, absence_id: int, payload: TeacherReasonSchema = None):
        """
        Deny absence (set denied=True, approved=False).
        
        Requires admin permissions. Denies an absence.
        
        Args:
            absence_id: Unique absence identifier
            payload: Optional TeacherReasonSchema with 'teacher_reason' field
            
        Returns:
            200: Absence denied successfully
            404: Absence not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            absence = Tavollet.objects.get(id=absence_id)
            absence.denied = True
            absence.approved = False  # Ensure mutual exclusivity
            
            # Update teacher reason if provided
            if payload and payload.teacher_reason:
                absence.teacher_reason = payload.teacher_reason
            
            absence.save()
            
            return 200, create_tavollet_response(absence)
        except Tavollet.DoesNotExist:
            return 404, {"message": "Távollét nem található"}
        except Exception as e:
            return 400, {"message": f"Error denying absence: {str(e)}"}

    @api.put("/absences/{absence_id}/reset", auth=JWTAuth(), response={200: TavolletSchema, 401: ErrorSchema, 404: ErrorSchema})
    def reset_absence_status(request, absence_id: int):
        """
        Reset absence status (set both approved=False and denied=False).
        
        Requires admin permissions. Resets an absence to pending status.
        
        Args:
            absence_id: Unique absence identifier
            
        Returns:
            200: Absence status reset successfully
            404: Absence not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            absence = Tavollet.objects.get(id=absence_id)
            absence.approved = False
            absence.denied = False
            absence.save()
            
            return 200, create_tavollet_response(absence)
        except Tavollet.DoesNotExist:
            return 404, {"message": "Távollét nem található"}
        except Exception as e:
            return 400, {"message": f"Error resetting absence status: {str(e)}"}

    @api.put("/absences/{absence_id}/teacher-reason", auth=JWTAuth(), response={200: TavolletSchema, 401: ErrorSchema, 404: ErrorSchema})
    def update_teacher_reason(request, absence_id: int, payload: TeacherReasonSchema):
        """
        Update teacher reason for an absence decision.
        
        Requires admin permissions. Allows teachers to provide reasoning for approval/denial.
        
        Args:
            absence_id: Unique absence identifier
            payload: TeacherReasonSchema with 'teacher_reason' field
            
        Returns:
            200: Teacher reason updated successfully
            404: Absence not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            absence = Tavollet.objects.get(id=absence_id)
            absence.teacher_reason = payload.teacher_reason
            absence.save()
            
            return 200, create_tavollet_response(absence)
        except Tavollet.DoesNotExist:
            return 404, {"message": "Távollét nem található"}
        except Exception as e:
            return 400, {"message": f"Error updating teacher reason: {str(e)}"}

    @api.delete("/absences/{absence_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
    def delete_absence(request, absence_id: int):
        """
        Delete absence.
        
        Requires proper permissions. Users can delete their own absences,
        admins can delete any absence.
        
        Args:
            absence_id: Unique absence identifier
            
        Returns:
            200: Absence deleted successfully
            404: Absence not found
            401: Authentication or permission failed
        """
        try:
            requesting_user = request.auth
            absence = Tavollet.objects.get(id=absence_id)
            
            # Check permissions
            if not can_user_manage_absence(requesting_user, absence):
                return 401, {"message": "Nincs jogosultság a távollét törléséhez"}
            
            absence_info = f"{absence.user.get_full_name()} ({absence.start_date} - {absence.end_date})"
            absence.delete()
            
            return 200, {"message": f"Távollét '{absence_info}' sikeresen törölve"}
        except Tavollet.DoesNotExist:
            return 404, {"message": "Távollét nem található"}
        except Exception as e:
            return 400, {"message": f"Error deleting absence: {str(e)}"}

    @api.get("/absences/user/{user_id}/conflicts", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
    def check_user_absence_conflicts(request, user_id: int, start_date: str, end_date: str):
        """
        Check for absence conflicts for a specific user in a date range.
        
        Requires authentication and proper permissions.
        
        Args:
            user_id: Unique user identifier
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            
        Returns:
            200: Conflict information
            404: User not found
            401: Authentication or permission failed
        """
        try:
            requesting_user = request.auth
            
            # Check if requesting user can view this user's absences
            has_admin_permission = False
            try:
                from api.models import Profile
                profile = Profile.objects.get(user=requesting_user)
                has_admin_permission = profile.has_admin_permission('any')
            except Profile.DoesNotExist:
                pass
            
            if user_id != requesting_user.id and not has_admin_permission:
                return 401, {"message": "Nincs jogosultság másik felhasználó távollétének megtekintéséhez"}
            
            # Get target user
            try:
                target_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return 404, {"message": "Felhasználó nem található"}
            
            # Parse dates/datetimes
            try:
                # Try to parse as datetime first, fallback to date
                try:
                    check_start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    check_end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    
                    # Convert to local naive datetimes for SQLite compatibility
                    check_start = convert_to_local_naive_datetime(check_start)
                    check_end = convert_to_local_naive_datetime(check_end)
                        
                except ValueError:
                    # If not datetime, try as date and convert to datetime range
                    check_start_date = datetime.fromisoformat(start_date).date()
                    check_end_date = datetime.fromisoformat(end_date).date()
                    check_start = datetime.combine(check_start_date, datetime.min.time())
                    check_end = datetime.combine(check_end_date, datetime.max.time())
            except ValueError:
                return 400, {"message": "Hibás dátum/idő formátum"}
            
            # Find conflicting absences using TavolletTipus logic
            potential_conflicts = Tavollet.objects.filter(
                user=target_user,
                start_date__lt=check_end,
                end_date__gt=check_start
            ).select_related('tipus')
            
            conflict_data = []
            for absence in potential_conflicts:
                should_count_as_conflict = False
                
                if absence.denied:
                    continue  # Denied absences don't count as conflicts
                elif absence.approved:
                    should_count_as_conflict = True
                else:
                    # Pending absence - check tipus
                    if absence.tipus:
                        if absence.tipus.ignored_counts_as == 'approved':
                            should_count_as_conflict = True
                        # If ignored_counts_as == 'denied', user is available (skip)
                    else:
                        # No tipus specified for pending absence - conservative approach (conflict)
                        should_count_as_conflict = True
                
                if should_count_as_conflict:
                    conflict_data.append(create_tavollet_response(absence))
            
            return 200, {
                "user": create_user_basic_response(target_user),
                "check_period": {
                    "start_date": check_start.isoformat(),
                    "end_date": check_end.isoformat()
                },
                "has_conflicts": len(conflict_data) > 0,
                "conflicts": conflict_data
            }
            
        except Exception as e:
            return 401, {"message": f"Error checking absence conflicts: {str(e)}"}
