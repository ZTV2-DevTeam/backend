"""
ZTV2 Backend API - Main API Router

This is the main API configuration file that brings together all API modules
in an organized and maintainable structure.

API Structure:
- /api/auth/     - Authentication (login, logout, password reset)
- /api/partners/ - Partner management (CRUD operations)
- /api/radio/    - Radio stab and session management
- /api/users/    - User management and profiles
- /api/core/     - Basic/utility endpoints

Each module is self-contained and handles its own endpoints, schemas, and logic.
"""

from ninja import NinjaAPI

# Import our modular API components
from .api_modules.auth import register_auth_endpoints
from .api_modules.partners import register_partner_endpoints
from .api_modules.radio import register_radio_endpoints
from .api_modules.users import register_user_endpoints
from .api_modules.core import register_core_endpoints

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
register_core_endpoints(api)      # Basic endpoints like /hello, /test-auth
register_auth_endpoints(api)      # Authentication endpoints
register_partner_endpoints(api)   # Partner management endpoints
register_radio_endpoints(api)     # Radio management endpoints  
register_user_endpoints(api)      # User management endpoints