"""
Academic management API endpoints.
Handles school years (Tanev), classes (Osztaly), and academic-related functionality.
"""

from ninja import Schema
from api.models import Tanev, Osztaly
from .auth import JWTAuth, ErrorSchema
from datetime import date, datetime

# ============================================================================
# Schemas
# ============================================================================

class TanevSchema(Schema):
    """Response schema for school year data."""
    id: int
    start_date: str
    end_date: str
    start_year: int
    end_year: int
    display_name: str
    is_active: bool
    osztaly_count: int = 0

class TanevCreateSchema(Schema):
    """Request schema for creating new school year."""
    start_date: str
    end_date: str

class OsztalySchema(Schema):
    """Response schema for class data."""
    id: int
    start_year: int
    szekcio: str
    display_name: str
    current_display_name: str = None
    tanev: TanevSchema = None
    student_count: int = 0

class OsztalyCreateSchema(Schema):
    """Request schema for creating new class."""
    start_year: int
    szekcio: str
    tanev_id: int = None

class OsztalyUpdateSchema(Schema):
    """Request schema for updating existing class."""
    start_year: int = None
    szekcio: str = None
    tanev_id: int = None

# ============================================================================
# Utility Functions
# ============================================================================

def create_tanev_response(tanev: Tanev) -> dict:
    """
    Create standardized school year response dictionary.
    
    Args:
        tanev: Tanev model instance
        
    Returns:
        Dictionary with school year information
    """
    active_tanev = Tanev.get_active()
    is_active = active_tanev and active_tanev.id == tanev.id
    
    return {
        "id": tanev.id,
        "start_date": tanev.start_date.isoformat(),
        "end_date": tanev.end_date.isoformat(),
        "start_year": tanev.start_year,
        "end_year": tanev.end_year,
        "display_name": str(tanev),
        "is_active": is_active,
        "osztaly_count": tanev.osztalyok.count()
    }

def create_osztaly_response(osztaly: Osztaly) -> dict:
    """
    Create standardized class response dictionary.
    
    Args:
        osztaly: Osztaly model instance
        
    Returns:
        Dictionary with class information
    """
    return {
        "id": osztaly.id,
        "start_year": osztaly.startYear,
        "szekcio": osztaly.szekcio,
        "display_name": str(osztaly),
        "current_display_name": osztaly.get_current_year_name() if hasattr(osztaly, 'get_current_year_name') else str(osztaly),
        "tanev": create_tanev_response(osztaly.tanev) if osztaly.tanev else None,
        "student_count": osztaly.profile_set.count() if hasattr(osztaly, 'profile_set') else 0
    }

def check_admin_permissions(user) -> tuple[bool, str]:
    """
    Check if user has admin permissions for academic management.
    
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

def register_academic_endpoints(api):
    """Register all academic-related endpoints with the API router."""
    
    # ========================================================================
    # School Year (Tanev) Endpoints
    # ========================================================================
    
    @api.get("/school-years", auth=JWTAuth(), response={200: list[TanevSchema], 401: ErrorSchema})
    def get_school_years(request):
        """
        Get all school years.
        
        Requires authentication. Returns all school years with their
        basic information and class counts.
        
        Returns:
            200: List of all school years
            401: Authentication failed
        """
        try:
            school_years = Tanev.objects.prefetch_related('osztalyok').all()
            
            response = []
            for tanev in school_years:
                response.append(create_tanev_response(tanev))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching school years: {str(e)}"}

    @api.get("/school-years/{tanev_id}", auth=JWTAuth(), response={200: TanevSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_school_year(request, tanev_id: int):
        """
        Get single school year by ID.
        
        Requires authentication. Returns detailed information about a specific school year.
        
        Args:
            tanev_id: Unique school year identifier
            
        Returns:
            200: School year details
            404: School year not found
            401: Authentication failed
        """
        try:
            tanev = Tanev.objects.prefetch_related('osztalyok').get(id=tanev_id)
            return 200, create_tanev_response(tanev)
        except Tanev.DoesNotExist:
            return 404, {"message": "Tanév nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching school year: {str(e)}"}

    @api.get("/school-years/active", auth=JWTAuth(), response={200: TanevSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_active_school_year(request):
        """
        Get currently active school year.
        
        Requires authentication. Returns the school year that contains today's date.
        
        Returns:
            200: Active school year details
            404: No active school year found
            401: Authentication failed
        """
        try:
            active_tanev = Tanev.get_active()
            if not active_tanev:
                return 404, {"message": "Nincs aktív tanév"}
            return 200, create_tanev_response(active_tanev)
        except Exception as e:
            return 401, {"message": f"Error fetching active school year: {str(e)}"}

    @api.post("/school-years", auth=JWTAuth(), response={201: TanevSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_school_year(request, data: TanevCreateSchema):
        """
        Create new school year.
        
        Requires admin permissions. Creates a new school year with specified dates.
        
        Args:
            data: School year creation data
            
        Returns:
            201: School year created successfully
            400: Invalid data or date validation failed
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Validate dates
            try:
                start_date = datetime.fromisoformat(data.start_date).date()
                end_date = datetime.fromisoformat(data.end_date).date()
            except ValueError:
                return 400, {"message": "Hibás dátum formátum"}
            
            if start_date >= end_date:
                return 400, {"message": "A záró dátumnak a kezdő dátum után kell lennie"}
            
            tanev = Tanev.objects.create(
                start_date=start_date,
                end_date=end_date
            )
            
            return 201, create_tanev_response(tanev)
        except Exception as e:
            return 400, {"message": f"Error creating school year: {str(e)}"}

    # ========================================================================
    # Class (Osztaly) Endpoints
    # ========================================================================
    
    @api.get("/classes", auth=JWTAuth(), response={200: list[OsztalySchema], 401: ErrorSchema})
    def get_classes(request):
        """
        Get all classes.
        
        Requires authentication. Returns all classes with their
        basic information and student counts.
        
        Returns:
            200: List of all classes
            401: Authentication failed
        """
        try:
            classes = Osztaly.objects.select_related('tanev').all()
            
            response = []
            for osztaly in classes:
                response.append(create_osztaly_response(osztaly))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching classes: {str(e)}"}

    @api.get("/classes/{osztaly_id}", auth=JWTAuth(), response={200: OsztalySchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_class(request, osztaly_id: int):
        """
        Get single class by ID.
        
        Requires authentication. Returns detailed information about a specific class.
        
        Args:
            osztaly_id: Unique class identifier
            
        Returns:
            200: Class details
            404: Class not found
            401: Authentication failed
        """
        try:
            osztaly = Osztaly.objects.select_related('tanev').get(id=osztaly_id)
            return 200, create_osztaly_response(osztaly)
        except Osztaly.DoesNotExist:
            return 404, {"message": "Osztály nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching class: {str(e)}"}

    @api.get("/classes/by-section/{szekcio}", auth=JWTAuth(), response={200: list[OsztalySchema], 401: ErrorSchema})
    def get_classes_by_section(request, szekcio: str):
        """
        Get classes by section (A, B, F, etc.).
        
        Requires authentication. Returns all classes in the specified section.
        
        Args:
            szekcio: Section letter (e.g., 'F', 'A', 'B')
            
        Returns:
            200: List of classes in section
            401: Authentication failed
        """
        try:
            classes = Osztaly.objects.select_related('tanev').filter(
                szekcio__iexact=szekcio
            )
            
            response = []
            for osztaly in classes:
                response.append(create_osztaly_response(osztaly))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching classes by section: {str(e)}"}

    @api.post("/classes", auth=JWTAuth(), response={201: OsztalySchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_class(request, data: OsztalyCreateSchema):
        """
        Create new class.
        
        Requires admin permissions. Creates a new class with specified parameters.
        
        Args:
            data: Class creation data
            
        Returns:
            201: Class created successfully
            400: Invalid data or validation failed
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Validate section
            if len(data.szekcio) != 1:
                return 400, {"message": "A szekció egy karakterből kell álljon"}
            
            # Get school year if provided
            tanev = None
            if data.tanev_id:
                try:
                    tanev = Tanev.objects.get(id=data.tanev_id)
                except Tanev.DoesNotExist:
                    return 400, {"message": "Tanév nem található"}
            
            osztaly = Osztaly.objects.create(
                startYear=data.start_year,
                szekcio=data.szekcio.upper(),
                tanev=tanev
            )
            
            return 201, create_osztaly_response(osztaly)
        except Exception as e:
            return 400, {"message": f"Error creating class: {str(e)}"}

    @api.put("/classes/{osztaly_id}", auth=JWTAuth(), response={200: OsztalySchema, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
    def update_class(request, osztaly_id: int, data: OsztalyUpdateSchema):
        """
        Update existing class.
        
        Requires admin permissions. Updates class information with provided data.
        Only non-None fields are updated.
        
        Args:
            osztaly_id: Unique class identifier
            data: Class update data
            
        Returns:
            200: Class updated successfully
            404: Class not found
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            osztaly = Osztaly.objects.get(id=osztaly_id)
            
            # Update fields only if they are provided (not None)
            if data.start_year is not None:
                osztaly.startYear = data.start_year
            if data.szekcio is not None:
                if len(data.szekcio) != 1:
                    return 400, {"message": "A szekció egy karakterből kell álljon"}
                osztaly.szekcio = data.szekcio.upper()
            if data.tanev_id is not None:
                try:
                    tanev = Tanev.objects.get(id=data.tanev_id)
                    osztaly.tanev = tanev
                except Tanev.DoesNotExist:
                    return 400, {"message": "Tanév nem található"}
            
            osztaly.save()
            
            return 200, create_osztaly_response(osztaly)
        except Osztaly.DoesNotExist:
            return 404, {"message": "Osztály nem található"}
        except Exception as e:
            return 400, {"message": f"Error updating class: {str(e)}"}

    @api.delete("/classes/{osztaly_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
    def delete_class(request, osztaly_id: int):
        """
        Delete class.
        
        Requires admin permissions. Permanently removes class from database.
        Note: This will fail if there are students assigned to this class.
        
        Args:
            osztaly_id: Unique class identifier
            
        Returns:
            200: Class deleted successfully
            404: Class not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            osztaly = Osztaly.objects.get(id=osztaly_id)
            osztaly_name = str(osztaly)
            osztaly.delete()
            
            return 200, {"message": f"Osztály '{osztaly_name}' sikeresen törölve"}
        except Osztaly.DoesNotExist:
            return 404, {"message": "Osztály nem található"}
        except Exception as e:
            return 400, {"message": f"Error deleting class: {str(e)}"}
