"""
Organization API endpoints.
Handles stabs (teams), roles, assignments and organizational functionality.
"""

from ninja import Schema
from django.contrib.auth.models import User
from api.models import Stab, Szerepkor, SzerepkorRelaciok, Beosztas, Tanev
from .auth import JWTAuth, ErrorSchema
from datetime import datetime
from typing import Optional

# ============================================================================
# Schemas
# ============================================================================

class StabSchema(Schema):
    """Response schema for stab (team) data."""
    id: int
    name: str
    member_count: int = 0

class StabCreateSchema(Schema):
    """Request schema for creating new stab."""
    name: str

class SzerepkorSchema(Schema):
    """Response schema for role data."""
    id: int
    name: str
    ev: Optional[int] = None
    year_display: Optional[str] = None

class SzerepkorCreateSchema(Schema):
    """Request schema for creating new role."""
    name: str
    ev: Optional[int] = None

class UserBasicSchema(Schema):
    """Basic user information schema."""
    id: int
    username: str
    first_name: str
    last_name: str
    full_name: str

class SzerepkorRelacioSchema(Schema):
    """Response schema for role relation data."""
    id: int
    user: UserBasicSchema
    szerepkor: SzerepkorSchema

class SzerepkorRelacioCreateSchema(Schema):
    """Request schema for creating new role relation."""
    user_id: int
    szerepkor_id: int

class BeosztasSchema(Schema):
    """Response schema for assignment data."""
    id: int
    kesz: bool
    author: Optional[UserBasicSchema] = None
    tanev: Optional[dict] = None
    created_at: str
    role_relation_count: int = 0

class BeosztasCreateSchema(Schema):
    """Request schema for creating new assignment."""
    kesz: bool = False
    tanev_id: Optional[int] = None
    szerepkor_relacio_ids: list[int] = []

class BeosztasDetailSchema(Schema):
    """Detailed response schema for assignment with role relations."""
    id: int
    kesz: bool
    author: Optional[UserBasicSchema] = None
    tanev: Optional[dict] = None
    created_at: str
    szerepkor_relaciok: list[SzerepkorRelacioSchema] = []

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

def create_stab_response(stab: Stab) -> dict:
    """
    Create standardized stab response dictionary.
    
    Args:
        stab: Stab model instance
        
    Returns:
        Dictionary with stab information
    """
    return {
        "id": stab.id,
        "name": stab.name,
        "member_count": stab.tagok.count() if hasattr(stab, 'tagok') else 0
    }

def create_szerepkor_response(szerepkor: Szerepkor) -> dict:
    """
    Create standardized role response dictionary.
    
    Args:
        szerepkor: Szerepkor model instance
        
    Returns:
        Dictionary with role information
    """
    return {
        "id": szerepkor.id,
        "name": szerepkor.name,
        "ev": szerepkor.ev,
        "year_display": str(szerepkor.ev) if szerepkor.ev else None
    }

def create_szerepkor_relacio_response(relacio: SzerepkorRelaciok) -> dict:
    """
    Create standardized role relation response dictionary.
    
    Args:
        relacio: SzerepkorRelaciok model instance
        
    Returns:
        Dictionary with role relation information
    """
    return {
        "id": relacio.id,
        "user": create_user_basic_response(relacio.user),
        "szerepkor": create_szerepkor_response(relacio.szerepkor)
    }

def create_beosztas_response(beosztas: Beosztas, include_relations: bool = False) -> dict:
    """
    Create standardized assignment response dictionary.
    
    Args:
        beosztas: Beosztas model instance
        include_relations: Whether to include full role relations list
        
    Returns:
        Dictionary with assignment information
    """
    response = {
        "id": beosztas.id,
        "kesz": beosztas.kesz,
        "author": create_user_basic_response(beosztas.author) if beosztas.author else None,
        "tanev": {
            "id": beosztas.tanev.id,
            "display_name": str(beosztas.tanev),
            "is_active": Tanev.get_active() and Tanev.get_active().id == beosztas.tanev.id
        } if beosztas.tanev else None,
        "created_at": beosztas.created_at.isoformat(),
        "role_relation_count": beosztas.szerepkor_relaciok.count()
    }
    
    if include_relations:
        response["szerepkor_relaciok"] = [
            create_szerepkor_relacio_response(relacio)
            for relacio in beosztas.szerepkor_relaciok.select_related('user', 'szerepkor').all()
        ]
    
    return response

def check_admin_permissions(user) -> tuple[bool, str]:
    """
    Check if user has admin permissions for organizational management.
    
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

def register_organization_endpoints(api):
    """Register all organization-related endpoints with the API router."""
    
    # ========================================================================
    # Stab (Team) Endpoints
    # ========================================================================
    
    @api.get("/stabs", auth=JWTAuth(), response={200: list[StabSchema], 401: ErrorSchema})
    def get_stabs(request):
        """
        Get all stabs (teams).
        
        Requires authentication. Returns all stabs with their member counts.
        
        Returns:
            200: List of all stabs
            401: Authentication failed
        """
        try:
            stabs = Stab.objects.all()
            
            response = []
            for stab in stabs:
                response.append(create_stab_response(stab))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching stabs: {str(e)}"}

    @api.post("/stabs", auth=JWTAuth(), response={201: StabSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_stab(request, data: StabCreateSchema):
        """
        Create new stab (team).
        
        Requires admin permissions. Creates a new stab.
        
        Args:
            data: Stab creation data
            
        Returns:
            201: Stab created successfully
            400: Invalid data or duplicate name
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            stab = Stab.objects.create(name=data.name)
            
            return 201, create_stab_response(stab)
        except Exception as e:
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                return 400, {"message": "Ezzel a névvel már létezik stáb"}
            return 400, {"message": f"Error creating stab: {str(e)}"}

    # ========================================================================
    # Role (Szerepkor) Endpoints
    # ========================================================================
    
    @api.get("/roles", auth=JWTAuth(), response={200: list[SzerepkorSchema], 401: ErrorSchema})
    def get_roles(request, year: int = None):
        """
        Get all roles (szerepkorok).
        
        Requires authentication. Returns all roles, optionally filtered by year.
        
        Args:
            year: Optional year filter
            
        Returns:
            200: List of roles
            401: Authentication failed
        """
        try:
            roles = Szerepkor.objects.all()
            
            if year:
                roles = roles.filter(ev=year)
            
            response = []
            for role in roles:
                response.append(create_szerepkor_response(role))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching roles: {str(e)}"}

    @api.post("/roles", auth=JWTAuth(), response={201: SzerepkorSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_role(request, data: SzerepkorCreateSchema):
        """
        Create new role (szerepkor).
        
        Requires admin permissions. Creates a new role.
        
        Args:
            data: Role creation data
            
        Returns:
            201: Role created successfully
            400: Invalid data or duplicate name
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            role = Szerepkor.objects.create(
                name=data.name,
                ev=data.ev
            )
            
            return 201, create_szerepkor_response(role)
        except Exception as e:
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                return 400, {"message": "Ezzel a névvel már létezik szerepkör"}
            return 400, {"message": f"Error creating role: {str(e)}"}

    # ========================================================================
    # Role Relation (SzerepkorRelaciok) Endpoints
    # ========================================================================
    
    @api.get("/role-relations", auth=JWTAuth(), response={200: list[SzerepkorRelacioSchema], 401: ErrorSchema})
    def get_role_relations(request, user_id: int = None, role_id: int = None):
        """
        Get role relations (user-role assignments).
        
        Requires authentication. Returns role relations, optionally filtered.
        
        Args:
            user_id: Optional user filter
            role_id: Optional role filter
            
        Returns:
            200: List of role relations
            401: Authentication failed
        """
        try:
            relations = SzerepkorRelaciok.objects.select_related('user', 'szerepkor').all()
            
            if user_id:
                relations = relations.filter(user_id=user_id)
            if role_id:
                relations = relations.filter(szerepkor_id=role_id)
            
            response = []
            for relation in relations:
                response.append(create_szerepkor_relacio_response(relation))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching role relations: {str(e)}"}

    @api.post("/role-relations", auth=JWTAuth(), response={201: SzerepkorRelacioSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_role_relation(request, data: SzerepkorRelacioCreateSchema):
        """
        Create new role relation (assign role to user).
        
        Requires admin permissions. Creates a new user-role assignment.
        
        Args:
            data: Role relation creation data
            
        Returns:
            201: Role relation created successfully
            400: Invalid data or relation already exists
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Get user and role
            try:
                user = User.objects.get(id=data.user_id)
                role = Szerepkor.objects.get(id=data.szerepkor_id)
            except User.DoesNotExist:
                return 400, {"message": "Felhasználó nem található"}
            except Szerepkor.DoesNotExist:
                return 400, {"message": "Szerepkör nem található"}
            
            # Check if relation already exists
            if SzerepkorRelaciok.objects.filter(user=user, szerepkor=role).exists():
                return 400, {"message": "Ez a szerepkör már hozzá van rendelve ehhez a felhasználóhoz"}
            
            relation = SzerepkorRelaciok.objects.create(
                user=user,
                szerepkor=role
            )
            
            return 201, create_szerepkor_relacio_response(relation)
        except Exception as e:
            return 400, {"message": f"Error creating role relation: {str(e)}"}

    @api.delete("/role-relations/{relation_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
    def delete_role_relation(request, relation_id: int):
        """
        Delete role relation (remove role from user).
        
        Requires admin permissions. Removes user-role assignment.
        
        Args:
            relation_id: Unique role relation identifier
            
        Returns:
            200: Role relation deleted successfully
            404: Role relation not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            relation = SzerepkorRelaciok.objects.select_related('user', 'szerepkor').get(id=relation_id)
            user_name = relation.user.get_full_name()
            role_name = relation.szerepkor.name
            relation.delete()
            
            return 200, {"message": f"Szerepkör '{role_name}' sikeresen eltávolítva '{user_name}' felhasználótól"}
        except SzerepkorRelaciok.DoesNotExist:
            return 404, {"message": "Szerepkör reláció nem található"}
        except Exception as e:
            return 400, {"message": f"Error deleting role relation: {str(e)}"}

    # ========================================================================
    # Assignment (Beosztas) Endpoints
    # ========================================================================
    
    @api.get("/assignments", auth=JWTAuth(), response={200: list[BeosztasSchema], 401: ErrorSchema})
    def get_assignments(request, tanev_id: int = None, kesz: bool = None):
        """
        Get assignments (beosztasok).
        
        Requires authentication. Returns assignments, optionally filtered.
        
        Args:
            tanev_id: Optional school year filter
            kesz: Optional completion status filter
            
        Returns:
            200: List of assignments
            401: Authentication failed
        """
        try:
            assignments = Beosztas.objects.select_related('author', 'tanev').prefetch_related('szerepkor_relaciok').all()
            
            if tanev_id:
                assignments = assignments.filter(tanev_id=tanev_id)
            if kesz is not None:
                assignments = assignments.filter(kesz=kesz)
            
            response = []
            for assignment in assignments:
                response.append(create_beosztas_response(assignment))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching assignments: {str(e)}"}

    @api.get("/assignments/{assignment_id}", auth=JWTAuth(), response={200: BeosztasDetailSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_assignment_details(request, assignment_id: int):
        """
        Get detailed assignment information.
        
        Requires authentication. Returns full assignment details including role relations.
        
        Args:
            assignment_id: Unique assignment identifier
            
        Returns:
            200: Detailed assignment information
            404: Assignment not found
            401: Authentication failed
        """
        try:
            assignment = Beosztas.objects.select_related('author', 'tanev').prefetch_related(
                'szerepkor_relaciok__user', 'szerepkor_relaciok__szerepkor'
            ).get(id=assignment_id)
            
            return 200, create_beosztas_response(assignment, include_relations=True)
        except Beosztas.DoesNotExist:
            return 404, {"message": "Beosztás nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching assignment details: {str(e)}"}

    @api.post("/assignments", auth=JWTAuth(), response={201: BeosztasDetailSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_assignment(request, data: BeosztasCreateSchema):
        """
        Create new assignment (beosztas).
        
        Requires admin permissions. Creates a new assignment with role relations.
        
        Args:
            data: Assignment creation data
            
        Returns:
            201: Assignment created successfully
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            user = request.auth
            
            # Get school year if provided
            tanev = None
            if data.tanev_id:
                try:
                    tanev = Tanev.objects.get(id=data.tanev_id)
                except Tanev.DoesNotExist:
                    return 400, {"message": "Tanév nem található"}
            
            # Create assignment
            assignment = Beosztas.objects.create(
                kesz=data.kesz,
                author=user,
                tanev=tanev
            )
            
            # Add role relations if provided
            if data.szerepkor_relacio_ids:
                relations = SzerepkorRelaciok.objects.filter(id__in=data.szerepkor_relacio_ids)
                assignment.szerepkor_relaciok.set(relations)
            
            return 201, create_beosztas_response(assignment, include_relations=True)
        except Exception as e:
            return 400, {"message": f"Error creating assignment: {str(e)}"}

    @api.put("/assignments/{assignment_id}/toggle-complete", auth=JWTAuth(), response={200: BeosztasDetailSchema, 401: ErrorSchema, 404: ErrorSchema})
    def toggle_assignment_completion(request, assignment_id: int):
        """
        Toggle assignment completion status.
        
        Requires admin permissions. Toggles the 'kesz' (complete) status of an assignment.
        
        Args:
            assignment_id: Unique assignment identifier
            
        Returns:
            200: Assignment status updated
            404: Assignment not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            assignment = Beosztas.objects.get(id=assignment_id)
            assignment.kesz = not assignment.kesz
            assignment.save()
            
            return 200, create_beosztas_response(assignment, include_relations=True)
        except Beosztas.DoesNotExist:
            return 404, {"message": "Beosztás nem található"}
        except Exception as e:
            return 400, {"message": f"Error updating assignment: {str(e)}"}

    @api.delete("/assignments/{assignment_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
    def delete_assignment(request, assignment_id: int):
        """
        Delete assignment.
        
        Requires admin permissions. Permanently removes assignment from database.
        
        Args:
            assignment_id: Unique assignment identifier
            
        Returns:
            200: Assignment deleted successfully
            404: Assignment not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            assignment = Beosztas.objects.get(id=assignment_id)
            assignment_id_display = assignment.id
            assignment.delete()
            
            return 200, {"message": f"Beosztás #{assignment_id_display} sikeresen törölve"}
        except Beosztas.DoesNotExist:
            return 404, {"message": "Beosztás nem található"}
        except Exception as e:
            return 400, {"message": f"Error deleting assignment: {str(e)}"}
