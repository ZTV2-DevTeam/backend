"""
FTV Backend API - Comprehensive Public API Documentation

This is the main API configuration file that provides a complete, organized, and 
maintainable REST API for the FTV school media system.

🎥 OVERVIEW
============

FTV is a comprehensive school media management system designed for SZLG, providing complete functionality for:

- Student and teacher management
- Media equipment tracking and booking
- Filming session planning and execution
- Radio program management (specialized for 9F students)  
- Partner institution collaboration
- Academic year and class organization
- Announcement and communication systems
- Absence and availability tracking

The API is built with Django Ninja for automatic OpenAPI documentation and 
type-safe request/response handling.

📚 API STRUCTURE
================

The API is organized into logical modules, each handling a specific domain:

🔐 AUTHENTICATION (/api/auth/)
   - JWT-based authentication system
   - Password reset functionality
   - User session management
   - Token refresh capabilities

👥 USER MANAGEMENT (/api/users/ & /api/user-management/)
   - User profiles and information
   - Administrative user CRUD operations
   - First-time login system with email automation
   - Role-based permission management
   - Bulk user operations

🏫 ACADEMIC SYSTEM (/api/academic/)
   - School year (Tanév) management
   - Class (Osztály) organization
   - Student-class assignments
   - Academic year calculations

🎬 MEDIA PRODUCTION
   - Equipment management (/api/equipment/)
     * Equipment types and inventory
     * Availability checking and booking
     * Maintenance status tracking
   
   - Filming sessions (/api/production/)
     * Session planning and scheduling
     * Equipment assignment
     * Participant management

📻 RADIO SYSTEM (/api/radio/)
   - Radio stab (team) management
   - Radio session scheduling
   - 9F student specialization support
   - Participant coordination

🏢 ORGANIZATION (/api/organization/)
   - Stab (team/department) management
   - Role and permission assignments
   - Organizational structure

🤝 PARTNERSHIPS (/api/partners/)
   - External partner management
   - Institution collaboration
   - Partner information tracking

📢 COMMUNICATIONS (/api/communications/)
   - Announcement system
   - Message broadcasting
   - Notification management

📋 OPERATIONS
   - Absence management (/api/absence/)
   - System configuration (/api/config/)
   - Core utilities (/api/core/)

🔑 AUTHENTICATION & SECURITY
============================

The API uses JWT (JSON Web Token) authentication:

1. **Login Process:**
   POST /api/login
   - Send username/password
   - Receive JWT token + user info
   - Token expires after 1 hour

2. **Using Tokens:**
   - Include in Authorization header: `Bearer YOUR_JWT_TOKEN`
   - Required for all protected endpoints
   - Automatic user identification

3. **Token Management:**
   - POST /api/refresh-token - Get new token
   - POST /api/logout - Invalidate session
   - GET /api/profile - Check current user

4. **Password Reset:**
   - POST /api/forgot-password - Initiate reset
   - GET /api/verify-reset-token/{token} - Verify token
   - POST /api/reset-password - Complete reset

🎯 PUBLIC API USAGE
===================

For external developers building custom interfaces:

**Base URL:** `http://your-domain.com/api/`

**Content-Type:** `application/json` (for POST/PUT requests)

**Authentication:** Include JWT token in all requests:
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

**Example API Calls:**

```javascript
// Login to get token
const loginResponse = await fetch('/api/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: 'username=myuser&password=mypass'
});
const { token } = await loginResponse.json();

// Use token for authenticated requests
const userProfile = await fetch('/api/profile', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// Get all partners
const partners = await fetch('/api/partners', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

📊 RESPONSE FORMAT
==================

All endpoints return consistent JSON responses:

**Success Response (200/201):**
```json
{
  "id": 123,
  "name": "Example",
  "...": "other fields"
}
```

**Error Response (400/401/404):**
```json
{
  "message": "Detailed error description"
}
```

**List Response:**
```json
[
  {"id": 1, "name": "Item 1"},
  {"id": 2, "name": "Item 2"}
]
```

🎭 USER ROLES & PERMISSIONS
===========================

The system supports multiple user roles:

**Student (none):**
- View own profile
- Check own schedule and availability
- View announcements
- Access assigned radio sessions (9F students)

**Teacher Admin (teacher):**
- Manage filming sessions
- Access student information
- Create announcements
- Manage radio sessions

**System Admin (system_admin):**
- Full user management
- System configuration
- Academic year setup

**Developer Admin (developer):**
- Complete system access
- API debugging capabilities
- Advanced system configuration

📱 FRONTEND INTEGRATION
=======================

The API provides comprehensive data for frontend applications:

- **Permission System:** GET /api/permissions returns what UI elements to show
- **User Context:** GET /api/profile provides current user information  
- **Configuration Status:** GET /api/tanev-config-status for setup wizards
- **Real-time Data:** All endpoints provide fresh data without caching issues

🔧 DEVELOPMENT FEATURES
=======================

**Automatic Documentation:**
- Visit `/api/docs` for interactive API explorer
- OpenAPI/Swagger specification available
- Type-safe schemas for all endpoints

**Error Handling:**
- Detailed error messages in Hungarian
- Consistent error codes
- Validation error details

**Testing Endpoints:**
- GET /api/hello - Basic connectivity test
- GET /api/test-auth - Authentication status check

🚀 GETTING STARTED
==================

1. **Authentication:** Start by calling `/api/login` to get a JWT token
2. **User Context:** Call `/api/profile` to understand current user permissions
3. **Explore Data:** Use appropriate endpoints based on user role
4. **Handle Errors:** Implement proper error handling for all API calls

For detailed endpoint documentation, visit the interactive docs at `/api/docs`
when the server is running.

🎓 EDUCATIONAL CONTEXT
=====================

This system is specifically designed for educational institutions with media programs:

- **9F Students:** Special support for second-year radio program students
- **Equipment Management:** School media equipment tracking and booking
- **Academic Integration:** Seamless integration with school year systems
- **Multi-role Support:** Students, teachers, and administrators

The API enables building custom applications for specific educational workflows
while maintaining comprehensive functionality for all user types.
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
from .api_modules.absences import register_absence_management_endpoints  # New absence management
from .api_modules.assignments import register_assignment_endpoints  # New assignment management
from .api_modules.config import register_config_endpoints
from .api_modules.user_management import register_user_management_endpoints
from .api_modules.students import register_student_endpoints
from .api_modules.configuration_wizard import register_configuration_wizard_endpoints
from .api_modules.legacy import register_legacy_endpoints

# ============================================================================
# API Configuration
# ============================================================================

# Initialize the main API instance
api = NinjaAPI(
    title="FTV Backend API",
    description="Organized API for FTV backend application with modular structure",
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
register_student_endpoints(api)         # Student listing and reporter selection endpoints
register_academic_endpoints(api)        # School years and classes endpoints
register_equipment_endpoints(api)       # Equipment management endpoints
register_production_endpoints(api)      # Filming sessions and contact persons
register_communications_endpoints(api)  # Announcements and messaging
register_organization_endpoints(api)    # Stabs, roles, and assignments
register_absence_endpoints(api)         # Absence management endpoints (távollét)
register_absence_management_endpoints(api)  # School absence management (hiányzás)
register_assignment_endpoints(api)      # Filming assignment management (beosztás)
register_config_endpoints(api)          # System configuration endpoints
register_configuration_wizard_endpoints(api)  # Configuration wizard endpoints
register_legacy_endpoints(api)          # Legacy system endpoints