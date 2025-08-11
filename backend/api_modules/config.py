"""
System configuration API endpoints.
Handles system configuration and settings (Config model).
"""

from ninja import Schema
from api.models import Config
from .auth import JWTAuth, ErrorSchema

# ============================================================================
# Schemas
# ============================================================================

class ConfigSchema(Schema):
    """Response schema for configuration data."""
    id: int
    active: bool
    allow_emails: bool
    status: str

class ConfigUpdateSchema(Schema):
    """Request schema for updating configuration."""
    active: bool = None
    allow_emails: bool = None

# ============================================================================
# Utility Functions
# ============================================================================

def create_config_response(config: Config) -> dict:
    """
    Create standardized configuration response dictionary.
    
    Args:
        config: Config model instance
        
    Returns:
        Dictionary with configuration information
    """
    # Determine overall status
    if config.active and config.allowEmails:
        status = "fully_active"
    elif config.active:
        status = "active_no_email"
    elif config.allowEmails:
        status = "inactive_email_only"
    else:
        status = "inactive"
    
    return {
        "id": config.id,
        "active": config.active,
        "allow_emails": config.allow_emails,
        "status": status
    }

def check_developer_admin_permissions(user) -> tuple[bool, str]:
    """
    Check if user has developer admin permissions for configuration management.
    Only developer admins should be able to modify system configuration.
    
    Args:
        user: Django User object
        
    Returns:
        Tuple of (has_permission, error_message)
    """
    try:
        from api.models import Profile
        profile = Profile.objects.get(user=user)
        if not profile.is_developer_admin:
            return False, "Developer adminisztrátor jogosultság szükséges"
        return True, ""
    except Profile.DoesNotExist:
        return False, "Felhasználói profil nem található"

def check_admin_permissions(user) -> tuple[bool, str]:
    """
    Check if user has any admin permissions for configuration viewing.
    
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

def register_config_endpoints(api):
    """Register all configuration-related endpoints with the API router."""
    
    @api.get("/config", auth=JWTAuth(), response={200: list[ConfigSchema], 401: ErrorSchema})
    def get_configurations(request):
        """
        Get all system configurations.
        
        Requires admin permissions. Returns all configuration objects.
        Note: Usually there should be only one Config instance.
        
        Returns:
            200: List of all configurations
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions (any admin can view config)
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            configs = Config.objects.all()
            
            response = []
            for config in configs:
                # Convert allowEmails to allow_emails for consistency
                config_data = create_config_response(config)
                response.append(config_data)
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching configurations: {str(e)}"}

    @api.get("/config/{config_id}", auth=JWTAuth(), response={200: ConfigSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_configuration(request, config_id: int):
        """
        Get specific system configuration by ID.
        
        Requires admin permissions. Returns detailed configuration information.
        
        Args:
            config_id: Unique configuration identifier
            
        Returns:
            200: Configuration details
            404: Configuration not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            config = Config.objects.get(id=config_id)
            return 200, create_config_response(config)
        except Config.DoesNotExist:
            return 404, {"message": "Konfiguráció nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching configuration: {str(e)}"}

    @api.get("/config/current", auth=JWTAuth(), response={200: ConfigSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_current_configuration(request):
        """
        Get current/active system configuration.
        
        Requires admin permissions. Returns the first configuration object,
        which is typically the active one.
        
        Returns:
            200: Current configuration details
            404: No configuration found
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Get the first (and usually only) configuration
            config = Config.objects.first()
            if not config:
                return 404, {"message": "Nincs konfiguráció beállítva"}
            
            return 200, create_config_response(config)
        except Exception as e:
            return 401, {"message": f"Error fetching current configuration: {str(e)}"}

    @api.post("/config", auth=JWTAuth(), response={201: ConfigSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_configuration(request, data: ConfigUpdateSchema):
        """
        Create new system configuration.
        
        Requires developer admin permissions. Creates a new configuration object.
        Note: Usually there should be only one Config instance.
        
        Args:
            data: Configuration creation data
            
        Returns:
            201: Configuration created successfully
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check if user has developer admin permissions
            has_permission, error_message = check_developer_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Check if configuration already exists
            existing_count = Config.objects.count()
            if existing_count > 0:
                return 400, {"message": "Konfiguráció már létezik. Használja a frissítés műveletet."}
            
            config = Config.objects.create(
                active=data.active if data.active is not None else False,
                allowEmails=data.allow_emails if data.allow_emails is not None else False
            )
            
            return 201, create_config_response(config)
        except Exception as e:
            return 400, {"message": f"Error creating configuration: {str(e)}"}

    @api.put("/config/{config_id}", auth=JWTAuth(), response={200: ConfigSchema, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
    def update_configuration(request, config_id: int, data: ConfigUpdateSchema):
        """
        Update existing system configuration.
        
        Requires developer admin permissions. Updates configuration with provided data.
        Only non-None fields are updated.
        
        Args:
            config_id: Unique configuration identifier
            data: Configuration update data
            
        Returns:
            200: Configuration updated successfully
            404: Configuration not found
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check if user has developer admin permissions
            has_permission, error_message = check_developer_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            config = Config.objects.get(id=config_id)
            
            # Update fields only if they are provided (not None)
            if data.active is not None:
                config.active = data.active
            if data.allow_emails is not None:
                config.allowEmails = data.allow_emails
            
            config.save()
            
            return 200, create_config_response(config)
        except Config.DoesNotExist:
            return 404, {"message": "Konfiguráció nem található"}
        except Exception as e:
            return 400, {"message": f"Error updating configuration: {str(e)}"}

    @api.put("/config/current", auth=JWTAuth(), response={200: ConfigSchema, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
    def update_current_configuration(request, data: ConfigUpdateSchema):
        """
        Update the current/active system configuration.
        
        Requires developer admin permissions. Updates the first configuration object.
        
        Args:
            data: Configuration update data
            
        Returns:
            200: Configuration updated successfully
            404: No configuration found
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check if user has developer admin permissions
            has_permission, error_message = check_developer_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Get the first (and usually only) configuration
            config = Config.objects.first()
            if not config:
                # Create new configuration if none exists
                config = Config.objects.create(
                    active=data.active if data.active is not None else False,
                    allowEmails=data.allow_emails if data.allow_emails is not None else False
                )
                return 200, create_config_response(config)
            
            # Update existing configuration
            if data.active is not None:
                config.active = data.active
            if data.allow_emails is not None:
                config.allowEmails = data.allow_emails
            
            config.save()
            
            return 200, create_config_response(config)
        except Exception as e:
            return 400, {"message": f"Error updating current configuration: {str(e)}"}

    @api.put("/config/{config_id}/toggle-active", auth=JWTAuth(), response={200: ConfigSchema, 401: ErrorSchema, 404: ErrorSchema})
    def toggle_configuration_active(request, config_id: int):
        """
        Toggle the active status of a configuration.
        
        Requires developer admin permissions. Toggles the 'active' field.
        
        Args:
            config_id: Unique configuration identifier
            
        Returns:
            200: Configuration toggled successfully
            404: Configuration not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has developer admin permissions
            has_permission, error_message = check_developer_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            config = Config.objects.get(id=config_id)
            config.active = not config.active
            config.save()
            
            return 200, create_config_response(config)
        except Config.DoesNotExist:
            return 404, {"message": "Konfiguráció nem található"}
        except Exception as e:
            return 400, {"message": f"Error toggling configuration: {str(e)}"}

    @api.put("/config/{config_id}/toggle-emails", auth=JWTAuth(), response={200: ConfigSchema, 401: ErrorSchema, 404: ErrorSchema})
    def toggle_configuration_emails(request, config_id: int):
        """
        Toggle the email permission of a configuration.
        
        Requires developer admin permissions. Toggles the 'allowEmails' field.
        
        Args:
            config_id: Unique configuration identifier
            
        Returns:
            200: Configuration toggled successfully
            404: Configuration not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has developer admin permissions
            has_permission, error_message = check_developer_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            config = Config.objects.get(id=config_id)
            config.allowEmails = not config.allowEmails
            config.save()
            
            return 200, create_config_response(config)
        except Config.DoesNotExist:
            return 404, {"message": "Konfiguráció nem található"}
        except Exception as e:
            return 400, {"message": f"Error toggling configuration emails: {str(e)}"}

    @api.delete("/config/{config_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
    def delete_configuration(request, config_id: int):
        """
        Delete system configuration.
        
        Requires developer admin permissions. Permanently removes configuration.
        WARNING: This should be used very carefully as it affects system functionality.
        
        Args:
            config_id: Unique configuration identifier
            
        Returns:
            200: Configuration deleted successfully
            404: Configuration not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has developer admin permissions
            has_permission, error_message = check_developer_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            config = Config.objects.get(id=config_id)
            config.delete()
            
            return 200, {"message": f"Konfiguráció #{config_id} sikeresen törölve"}
        except Config.DoesNotExist:
            return 404, {"message": "Konfiguráció nem található"}
        except Exception as e:
            return 400, {"message": f"Error deleting configuration: {str(e)}"}

    @api.get("/config/status", response={200: dict})
    def get_system_status(request):
        """
        Get basic system status information.
        
        Public endpoint (no authentication required) that returns basic
        system operational status based on configuration.
        
        Returns:
            200: Basic system status
        """
        try:
            config = Config.objects.first()
            
            if not config:
                return 200, {
                    "system_active": False,
                    "emails_enabled": False,
                    "status": "not_configured",
                    "message": "Rendszer nincs konfigurálva"
                }
            
            return 200, {
                "system_active": config.active,
                "emails_enabled": config.allowEmails,
                "status": "configured",
                "message": "Rendszer konfigurálva" if config.active else "Rendszer inaktív"
            }
        except Exception as e:
            return 200, {
                "system_active": False,
                "emails_enabled": False,
                "status": "error",
                "message": f"Hiba a rendszer státusz lekérdezésekor: {str(e)}"
            }
