"""
Core API utilities and basic endpoints.
Contains general-purpose endpoints and utility functions.
"""

from datetime import datetime
from ninja import Schema
from .auth import JWTAuth, ErrorSchema
from api.models import Profile

# ============================================================================
# Permission Schemas
# ============================================================================

class UserPermissionsSchema(Schema):
    """Response schema for user permissions and display properties."""
    user_info: dict
    permissions: dict
    display_properties: dict
    role_info: dict

class TanevConfigStatusSchema(Schema):
    """Response schema for school year configuration status."""
    config_necessary: bool
    system_admin_setup_required: bool
    current_tanev: dict = None
    missing_components: list[str] = []
    setup_steps: list[dict] = []

# ============================================================================
# Basic API Endpoints
# ============================================================================

def register_core_endpoints(api):
    """Register core/basic API endpoints."""
    
    @api.get("/hello")
    def hello(request, name: str = "World"):
        """
        Simple hello world endpoint.
        
        Basic test endpoint to verify API functionality.
        
        Args:
            name: Optional name parameter (defaults to "World")
            
        Returns:
            Greeting message
        """
        return f"Hello, {name}!"

    @api.get("/test-auth")
    def test_auth(request):
        """
        Test endpoint to check API status.
        
        Basic endpoint to verify API functionality and authentication status.
        
        Returns:
            Dictionary with API status and user authentication info
        """
        return {
            "message": "API is working!",
            "user_authenticated": request.user.is_authenticated if hasattr(request, 'user') else False,
            "timestamp": datetime.utcnow().isoformat()
        }

    @api.get("/permissions", auth=JWTAuth(), response={200: UserPermissionsSchema, 401: ErrorSchema})
    def get_user_permissions(request):
        """
        Get comprehensive permissions and display properties for the authenticated user.
        
        Returns detailed information about what the frontend should display based on
        the user's role, admin type, class assignment, and other properties.
        
        Returns:
            200: Complete permissions and display properties
            401: Authentication failed
        """
        try:
            user = request.auth
            
            # Get user profile if it exists
            try:
                profile = Profile.objects.select_related(
                    'stab', 'radio_stab', 'osztaly'
                ).get(user=user)
            except Profile.DoesNotExist:
                profile = None
            
            # Base user information
            user_info = {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "full_name": user.get_full_name(),
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "is_active": user.is_active,
                "date_joined": user.date_joined.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
            
            # Initialize permission flags
            permissions = {
                # Admin permissions
                "is_admin": False,
                "is_developer_admin": False,
                "is_teacher_admin": False,
                "is_system_admin": False,
                "is_superuser": user.is_superuser,
                "is_staff": user.is_staff,
                
                # Special roles
                "is_production_leader": False,
                
                # Content management permissions
                "can_manage_users": False,
                "can_manage_partners": False,
                "can_manage_equipment": False,
                "can_manage_forgatas": False,
                "can_manage_announcements": False,
                "can_manage_radio_sessions": False,
                "can_manage_system_config": False,
                
                # Access permissions  
                "can_access_admin_panel": user.is_staff or user.is_superuser,
                "can_view_all_users": False,
                "can_view_all_forgatas": False,
                "can_create_forgatas": False,
                "can_edit_forgatas": False,
                "can_delete_forgatas": False,
                
                # Special role permissions
                "is_osztaly_fonok": False,
                "can_manage_class_students": False,
                "can_view_class_info": False,
                
                # Radio permissions
                "can_participate_in_radio": False,
                "can_view_radio_schedule": False,
                "can_manage_radio_stab": False,
            }
            
            # Role and assignment information
            role_info = {
                "admin_type": "none",
                "special_role": "none",
                "primary_role": "student",
                "stab_assignment": None,
                "radio_stab_assignment": None,
                "class_assignment": None,
                "class_display_name": None,
                "is_second_year_radio": False,
                "roles": []
            }
            
            # Display properties for frontend
            display_properties = {
                "show_admin_menu": False,
                "show_teacher_menu": False,
                "show_student_menu": True,
                "show_radio_menu": False,
                "show_class_management": False,
                "show_equipment_management": False,
                "show_partner_management": False,
                "show_user_management": False,
                "show_statistics": False,
                "show_reports": False,
                "dashboard_widgets": ["announcements", "my_forgatas"],
                "navigation_items": ["dashboard", "forgatas", "profile"],
                "quick_actions": ["view_announcements", "check_schedule"]
            }
            
            # If user has a profile, process role-specific permissions
            if profile:
                # Admin type permissions
                role_info["admin_type"] = profile.admin_type
                role_info["special_role"] = profile.special_role
                permissions["is_admin"] = profile.is_admin
                permissions["is_developer_admin"] = profile.is_developer_admin
                permissions["is_teacher_admin"] = profile.is_teacher_admin
                permissions["is_system_admin"] = profile.is_system_admin
                permissions["is_production_leader"] = profile.is_production_leader
                
                # Set primary role based on admin type and assignments
                if profile.is_system_admin:
                    role_info["primary_role"] = "system_admin"
                    role_info["roles"].append("Rendszeradminisztrátor")
                elif profile.is_developer_admin:
                    role_info["primary_role"] = "developer_admin"
                    role_info["roles"].append("Developer Admin")
                elif profile.is_teacher_admin:
                    role_info["primary_role"] = "teacher_admin"
                    role_info["roles"].append("Médiatanár")
                
                # Add special role information
                if profile.is_production_leader:
                    role_info["roles"].append("Gyártásvezető")
                
                # Class assignment (potential osztályfőnök)
                if profile.osztaly:
                    role_info["class_assignment"] = {
                        "id": profile.osztaly.id,
                        "start_year": profile.osztaly.startYear,
                        "szekcio": profile.osztaly.szekcio,
                        "display_name": str(profile.osztaly)
                    }
                    role_info["class_display_name"] = str(profile.osztaly)
                    
                    # Check if they are potentially an osztályfőnök (teacher admin with class assignment)
                    if profile.is_teacher_admin:
                        permissions["is_osztaly_fonok"] = True
                        permissions["can_manage_class_students"] = True
                        permissions["can_view_class_info"] = True
                        role_info["roles"].append("Osztályfőnök")
                        role_info["primary_role"] = "osztaly_fonok"
                
                # Stab assignment
                if profile.stab:
                    role_info["stab_assignment"] = {
                        "id": profile.stab.id,
                        "name": profile.stab.name
                    }
                    role_info["roles"].append(f"Stáb: {profile.stab.name}")
                
                # Radio stab assignment and second year radio student
                role_info["is_second_year_radio"] = profile.is_second_year_radio_student
                if profile.radio_stab:
                    role_info["radio_stab_assignment"] = {
                        "id": profile.radio_stab.id,
                        "name": profile.radio_stab.name,
                        "team_code": profile.radio_stab.team_code
                    }
                    role_info["roles"].append(f"Rádió: {profile.radio_stab.name} ({profile.radio_stab.team_code})")
                    permissions["can_participate_in_radio"] = True
                    permissions["can_view_radio_schedule"] = True
                
                if role_info["is_second_year_radio"]:
                    role_info["roles"].append("9F Rádiós Diák")
                    permissions["can_participate_in_radio"] = True
                    permissions["can_view_radio_schedule"] = True
                
                # Set permissions based on admin type
                if permissions["is_developer_admin"]:
                    # Developer admin has all permissions
                    permissions.update({
                        "can_manage_users": True,
                        "can_manage_partners": True,
                        "can_manage_equipment": True,
                        "can_manage_forgatas": True,
                        "can_manage_announcements": True,
                        "can_manage_radio_sessions": True,
                        "can_view_all_users": True,
                        "can_view_all_forgatas": True,
                        "can_create_forgatas": True,
                        "can_edit_forgatas": True,
                        "can_delete_forgatas": True,
                        "can_manage_radio_stab": True,
                    })
                    
                    display_properties.update({
                        "show_admin_menu": True,
                        "show_teacher_menu": True,
                        "show_radio_menu": True,
                        "show_class_management": True,
                        "show_equipment_management": True,
                        "show_partner_management": True,
                        "show_user_management": True,
                        "show_statistics": True,
                        "show_reports": True,
                        "dashboard_widgets": ["announcements", "my_forgatas", "system_stats", "recent_activity", "user_summary"],
                        "navigation_items": ["dashboard", "forgatas", "users", "partners", "equipment", "radio", "announcements", "reports", "settings", "profile"],
                        "quick_actions": ["create_forgatas", "manage_users", "system_settings", "view_reports"]
                    })
                
                elif permissions["is_teacher_admin"]:
                    # Teacher admin (Médiatanár) permissions
                    permissions.update({
                        "can_manage_forgatas": True,
                        "can_manage_announcements": True,
                        "can_view_all_forgatas": True,
                        "can_create_forgatas": True,
                        "can_edit_forgatas": True,
                        "can_delete_forgatas": True,
                        "can_manage_radio_sessions": True,
                        "can_manage_radio_stab": True,
                    })
                    
                    display_properties.update({
                        "show_teacher_menu": True,
                        "show_radio_menu": True,
                        "dashboard_widgets": ["announcements", "my_forgatas", "class_info", "radio_schedule"],
                        "navigation_items": ["dashboard", "forgatas", "announcements", "radio", "class", "profile"],
                        "quick_actions": ["create_forgatas", "manage_announcements", "radio_schedule"]
                    })
                    
                    # Additional permissions if they are osztályfőnök
                    if permissions["is_osztaly_fonok"]:
                        display_properties.update({
                            "show_class_management": True,
                            "dashboard_widgets": display_properties["dashboard_widgets"] + ["class_students"],
                            "quick_actions": display_properties["quick_actions"] + ["manage_class"]
                        })
            
            # If no profile or basic student
            if not profile or not permissions["is_admin"]:
                # Basic student permissions
                display_properties.update({
                    "dashboard_widgets": ["announcements", "my_forgatas", "upcoming_events"],
                    "navigation_items": ["dashboard", "forgatas", "profile"],
                    "quick_actions": ["view_announcements", "check_schedule"]
                })
                
                # Add radio menu for radio students
                if profile and (permissions["can_participate_in_radio"] or role_info["is_second_year_radio"]):
                    display_properties["show_radio_menu"] = True
                    display_properties["navigation_items"].append("radio")
                    display_properties["dashboard_widgets"].append("radio_schedule")
                    display_properties["quick_actions"].append("radio_schedule")
            
            # Add profile-specific information to user_info if profile exists
            if profile:
                user_info.update({
                    "telefonszam": profile.telefonszam,
                    "medias": profile.medias,
                    "has_profile": True
                })
            else:
                user_info.update({
                    "telefonszam": None,
                    "medias": False,
                    "has_profile": False
                })
            
            return 200, {
                "user_info": user_info,
                "permissions": permissions,
                "display_properties": display_properties,
                "role_info": role_info
            }
            
        except Exception as e:
            return 401, {"message": f"Error fetching permissions: {str(e)}"}

    @api.get("/tanev-config-status", response=TanevConfigStatusSchema)
    def check_tanev_config_necessary(request, auth: JWTAuth = Depends()):
        """
        Checks if the system configuration setup wizard should be shown to system administrators.
        Returns detailed status of configuration steps that need to be completed.
        """
        if not auth.profile or not auth.profile.is_system_admin:
            raise HttpError(403, "Only system administrators can check configuration status")
        
        from api.models import (
            Tanev, Osztaly, Stab, Config, 
            EquipmentTipus, Equipment, Partner,
            Szerepkor, User, Profile
        )
        
        status = {
            "config_necessary": False,
            "steps_incomplete": [],
            "details": {},
            "completion_percentage": 0
        }
        
        steps = []
        completed = 0
        
        # Step 1: Basic system configuration
        config_count = Config.objects.count()
        step_completed = config_count > 0
        steps.append({
            "step": "basic_config",
            "name": "Alapvető rendszerbeállítások",
            "required": True,
            "completed": step_completed,
            "description": "Rendszer alapbeállításainak konfigurálása"
        })
        if step_completed:
            completed += 1
        
        # Step 2: School year setup
        tanev_count = Tanev.objects.count()
        step_completed = tanev_count > 0
        steps.append({
            "step": "school_year",
            "name": "Tanév beállítása",
            "required": True,
            "completed": step_completed,
            "description": "Aktuális tanév létrehozása és beállítása"
        })
        if step_completed:
            completed += 1
        
        # Step 3: Classes setup
        osztaly_count = Osztaly.objects.count()
        step_completed = osztaly_count > 0
        steps.append({
            "step": "classes",
            "name": "Osztályok létrehozása",
            "required": True,
            "completed": step_completed,
            "description": "Iskolai osztályok hozzáadása a rendszerhez"
        })
        if step_completed:
            completed += 1
        
        # Step 4: Equipment types
        equipment_tipus_count = EquipmentTipus.objects.count()
        step_completed = equipment_tipus_count > 0
        steps.append({
            "step": "equipment_types",
            "name": "Eszköztípusok definiálása",
            "required": True,
            "completed": step_completed,
            "description": "Különböző eszköztípusok létrehozása"
        })
        if step_completed:
            completed += 1
        
        # Step 5: Equipment inventory
        equipment_count = Equipment.objects.count()
        step_completed = equipment_count > 0
        steps.append({
            "step": "equipment",
            "name": "Eszközök hozzáadása",
            "required": True,
            "completed": step_completed,
            "description": "Eszközök felvétele a rendszerbe"
        })
        if step_completed:
            completed += 1
        
        # Step 6: Partners/institutions
        partner_count = Partner.objects.count()
        step_completed = partner_count > 0
        steps.append({
            "step": "partners",
            "name": "Partnerintézmények",
            "required": False,
            "completed": step_completed,
            "description": "Együttműködő intézmények hozzáadása"
        })
        if step_completed:
            completed += 1
        
        # Step 7: Roles setup  
        szerepkor_count = Szerepkor.objects.count()
        step_completed = szerepkor_count > 0
        steps.append({
            "step": "roles",
            "name": "Szerepkörök definiálása",
            "required": True,
            "completed": step_completed,
            "description": "Különböző szerepkörök létrehozása"
        })
        if step_completed:
            completed += 1
        
        # Step 8: Staff/stab setup
        stab_count = Stab.objects.count()
        step_completed = stab_count > 0
        steps.append({
            "step": "staff",
            "name": "Stáb létrehozása",
            "required": True,
            "completed": step_completed,
            "description": "Munkacsoport/stáb felállítása"
        })
        if step_completed:
            completed += 1
        
        # Step 9: User accounts setup
        non_admin_users = User.objects.exclude(
            profile__admin_type__in=['developer', 'teacher', 'system_admin']
        ).count()
        step_completed = non_admin_users > 0
        steps.append({
            "step": "users",
            "name": "Felhasználói fiókok",
            "required": True,
            "completed": step_completed,
            "description": "Diákok és tanárok fiókjainak létrehozása"
        })
        if step_completed:
            completed += 1
        
        # Calculate completion percentage
        total_steps = len(steps)
        completion_percentage = round((completed / total_steps) * 100) if total_steps > 0 else 0
        
        # Determine if config is necessary (check only required steps)
        required_steps = [step for step in steps if step["required"]]
        required_completed = len([step for step in required_steps if step["completed"]])
        config_necessary = required_completed < len(required_steps)
        
        # Get incomplete steps
        steps_incomplete = [
            step["step"] for step in steps 
            if not step["completed"] and step["required"]
        ]
        
        status.update({
            "config_necessary": config_necessary,
            "steps_incomplete": steps_incomplete,
            "details": {
                "total_steps": total_steps,
                "completed_steps": completed,
                "required_steps": len(required_steps),
                "required_completed": required_completed,
                "steps": steps
            },
            "completion_percentage": completion_percentage
        })
        
        return status

# ============================================================================
# Utility Functions
# ============================================================================

def format_error_response(message: str, code: str = None) -> dict:
    """
    Create standardized error response.
    
    Args:
        message: Error message
        code: Optional error code
        
    Returns:
        Standardized error dictionary
    """
    response = {"message": message}
    if code:
        response["code"] = code
    return response

def validate_date_range(start_date: str, end_date: str = None) -> tuple[bool, str]:
    """
    Validate date range parameters.
    
    Args:
        start_date: Start date string
        end_date: Optional end date string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        if start_date:
            datetime.fromisoformat(start_date)
        if end_date:
            datetime.fromisoformat(end_date)
            if start_date and end_date and start_date > end_date:
                return False, "End date must be after start date"
        return True, ""
    except ValueError:
        return False, "Invalid date format. Use ISO format (YYYY-MM-DD)"

def paginate_response(queryset, page: int = 1, per_page: int = 20):
    """
    Apply pagination to queryset.
    
    Args:
        queryset: Django queryset
        page: Page number (1-based)
        per_page: Items per page
        
    Returns:
        Dictionary with paginated data and metadata
    """
    from django.core.paginator import Paginator, EmptyPage
    
    try:
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.page(page)
        
        return {
            "results": list(page_obj),
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_pages": paginator.num_pages,
                "total_items": paginator.count,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous()
            }
        }
    except EmptyPage:
        return {
            "results": [],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_pages": 0,
                "total_items": 0,
                "has_next": False,
                "has_previous": False
            }
        }
