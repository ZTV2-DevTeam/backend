"""
Absence management API endpoints.
Handles absences (Tavollet) and availability tracking.
"""

from ninja import Schema
from django.contrib.auth.models import User
from api.models import Tavollet
from .auth import JWTAuth, ErrorSchema
from datetime import datetime, date
from typing import Optional

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

class TavolletSchema(Schema):
    """Response schema for absence data."""
    id: int
    user: UserBasicSchema
    start_date: str
    end_date: str
    reason: Optional[str] = None
    denied: bool
    approved: bool
    duration_days: int
    status: str

class TavolletCreateSchema(Schema):
    """Request schema for creating new absence."""
    user_id: Optional[int] = None  # Optional - if not provided, uses current user
    start_date: str
    end_date: str
    reason: Optional[str] = None

class TavolletUpdateSchema(Schema):
    """Request schema for updating existing absence."""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    reason: Optional[str] = None
    denied: Optional[bool] = None
    approved: Optional[bool] = None

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

def create_tavollet_response(tavollet: Tavollet) -> dict:
    """
    Create standardized absence response dictionary.
    
    Args:
        tavollet: Tavollet model instance
        
    Returns:
        Dictionary with absence information
    """
    # Calculate duration in days
    duration = (tavollet.end_date - tavollet.start_date).days + 1
    
    # Determine status based on approval/denial state and time
    if tavollet.denied and tavollet.approved:
        # This shouldn't happen but handle it gracefully
        status = "konfliktus"  # Both flags set - should be fixed
    elif tavollet.denied:
        status = "elutasítva"
    elif tavollet.approved:
        status = "jóváhagyva"
    elif tavollet.end_date < date.today():
        status = "lezárt"
    elif tavollet.start_date <= date.today() <= tavollet.end_date:
        status = "folyamatban"
    else:
        status = "függőben"  # Changed from "jövőbeli" to be more descriptive of pending approval
    
    return {
        "id": tavollet.id,
        "user": create_user_basic_response(tavollet.user),
        "start_date": tavollet.start_date.isoformat(),
        "end_date": tavollet.end_date.isoformat(),
        "reason": tavollet.reason,
        "denied": tavollet.denied,
        "approved": tavollet.approved,
        "duration_days": duration,
        "status": status
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
            
            absences = absences.select_related('user').order_by('-start_date')
            
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
            absence = Tavollet.objects.select_related('user').get(id=absence_id)
            
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
            
            # Validate dates
            try:
                start_date = datetime.fromisoformat(data.start_date).date()
                end_date = datetime.fromisoformat(data.end_date).date()
            except ValueError:
                return 400, {"message": "Hibás dátum formátum"}
            
            if start_date > end_date:
                return 400, {"message": "A záró dátumnak a kezdő dátum után kell lennie"}
            
            # Check for overlapping absences (not denied)
            overlapping = Tavollet.objects.filter(
                user=target_user,
                start_date__lte=end_date,
                end_date__gte=start_date,
                denied=False
            ).exists()
            
            if overlapping:
                return 400, {"message": "Átfedő távollét már létezik ebben az időszakban"}
            
            # Create absence
            absence = Tavollet.objects.create(
                user=target_user,
                start_date=start_date,
                end_date=end_date,
                reason=data.reason,
                denied=False,
                approved=False
            )
            
            return 201, create_tavollet_response(absence)
        except Exception as e:
            return 400, {"message": f"Error creating absence: {str(e)}"}

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
                    updated_start_date = datetime.fromisoformat(data.start_date).date()
                except ValueError:
                    return 400, {"message": "Hibás kezdő dátum formátum"}
            
            if data.end_date is not None:
                try:
                    updated_end_date = datetime.fromisoformat(data.end_date).date()
                except ValueError:
                    return 400, {"message": "Hibás záró dátum formátum"}
            
            # Validate date range
            if updated_start_date > updated_end_date:
                return 400, {"message": "A záró dátumnak a kezdő dátum után kell lennie"}
            
            # Check for overlapping absences (excluding current one, not denied)
            overlapping = Tavollet.objects.filter(
                user=absence.user,
                start_date__lte=updated_end_date,
                end_date__gte=updated_start_date,
                denied=False
            ).exclude(id=absence.id).exists()
            
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
            
            absence.save()
            
            return 200, create_tavollet_response(absence)
        except Tavollet.DoesNotExist:
            return 404, {"message": "Távollét nem található"}
        except Exception as e:
            return 400, {"message": f"Error updating absence: {str(e)}"}

    @api.put("/absences/{absence_id}/approve", auth=JWTAuth(), response={200: TavolletSchema, 401: ErrorSchema, 404: ErrorSchema})
    def approve_absence(request, absence_id: int):
        """
        Approve absence (set approved=True, denied=False).
        
        Requires admin permissions. Approves an absence.
        
        Args:
            absence_id: Unique absence identifier
            
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
            absence.save()
            
            return 200, create_tavollet_response(absence)
        except Tavollet.DoesNotExist:
            return 404, {"message": "Távollét nem található"}
        except Exception as e:
            return 400, {"message": f"Error approving absence: {str(e)}"}

    @api.put("/absences/{absence_id}/deny", auth=JWTAuth(), response={200: TavolletSchema, 401: ErrorSchema, 404: ErrorSchema})
    def deny_absence(request, absence_id: int):
        """
        Deny absence (set denied=True, approved=False).
        
        Requires admin permissions. Denies an absence.
        
        Args:
            absence_id: Unique absence identifier
            
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
            
            # Parse dates
            try:
                check_start = datetime.fromisoformat(start_date).date()
                check_end = datetime.fromisoformat(end_date).date()
            except ValueError:
                return 400, {"message": "Hibás dátum formátum"}
            
            # Find conflicting absences (approved or pending - not denied)
            conflicts = Tavollet.objects.filter(
                user=target_user,
                start_date__lte=check_end,
                end_date__gte=check_start,
                denied=False
            )
            
            conflict_data = []
            for conflict in conflicts:
                conflict_data.append(create_tavollet_response(conflict))
            
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
