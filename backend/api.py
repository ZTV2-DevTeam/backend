"""
ZTV2 Backend API - Main API Router

This is the main API configuration file that brings together all API modules
in an organized and maintainable structure.

API Structure:
- /api/auth/         - Authentication (login, logout, password reset)
- /api/partners/     - Partner management (CRUD operations)
- /api/radio/        - Radio stab and session management
- /api/users/        - User management and profiles
- /api/core/         - Basic/utility endpoints
- /api/academic/     - School years and classes
- /api/equipment/    - Equipment and equipment types
- /api/production/   - Filming sessions and contact persons
- /api/communications/ - Announcements and messaging
- /api/organization/ - Stabs, roles, and assignments
- /api/absence/      - Absence management
- /api/config/       - System configuration

Each module is self-contained and handles its own endpoints, schemas, and logic.
"""

from ninja import NinjaAPI

# Import our modular API components
from .api_modules.auth import register_auth_endpoints
from .api_modules.partners import register_partner_endpoints
from .api_modules.radio import register_radio_endpoints
from .api_modules.users import register_user_endpoints
from .api_modules.core import register_core_endpoints
from .api_modules.academic import register_academic_endpoints
from .api_modules.equipment import register_equipment_endpoints
from .api_modules.production import register_production_endpoints
from .api_modules.communications import register_communications_endpoints
from .api_modules.organization import register_organization_endpoints
from .api_modules.absence import register_absence_endpoints
from .api_modules.config import register_config_endpoints
from .api_modules.user_management import register_user_management_endpoints

# ============================================================================
# API Configuration
# ============================================================================

# Initialize the main API instance
api = NinjaAPI(
    title="ZTV2 Backend API",
    description="Organized API for ZTV2 backend application with modular structure",
    version="2.0.0",
    csrf=False  # Disable CSRF for API endpoints
)

# ============================================================================
# Register API Modules
# ============================================================================

# Register all endpoint modules with the main API router
register_core_endpoints(api)            # Basic endpoints like /hello, /test-auth
register_auth_endpoints(api)            # Authentication endpoints
register_partner_endpoints(api)         # Partner management endpoints
register_radio_endpoints(api)           # Radio management endpoints
register_user_endpoints(api)            # User management endpoints
register_user_management_endpoints(api) # Comprehensive user CRUD management endpoints
register_academic_endpoints(api)        # School years and classes endpoints
register_equipment_endpoints(api)       # Equipment management endpoints
register_production_endpoints(api)      # Filming sessions and contact persons
register_communications_endpoints(api)  # Announcements and messaging
register_organization_endpoints(api)    # Stabs, roles, and assignments
register_absence_endpoints(api)         # Absence management endpoints
register_config_endpoints(api)          # System configuration endpoints