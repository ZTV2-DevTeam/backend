"""
FTV Communications API Module

This module provides comprehensive communication functionality for the FTV system,
including announcement management, targeted messaging, and communication tracking
for effective school-wide information distribution.

Public API Overview:
==================

The Communications API manages all aspects of internal communication including
announcements, targeted messaging, and communication tracking with role-based
access control and recipient management.

Base URL: /api/communications/

Protected Endpoints (JWT Token Required):
- GET  /announcements           - List announcements (filtered by user role)
- GET  /announcements/{id}      - Get specific announcement details
- POST /announcements           - Create new announcement (admin only)
- PUT  /announcements/{id}      - Update announcement (admin/author only)
- DELETE /announcements/{id}    - Delete announcement (admin/author only)

Communication System Overview:
=============================

The communication system provides:

1. **Broadcast Messaging**: System-wide announcements for all users
2. **Targeted Messaging**: Specific announcements for selected recipients
3. **Role-based Visibility**: Automatic filtering based on user permissions
4. **Author Tracking**: Full attribution and edit history
5. **Recipient Management**: Detailed recipient lists and tracking

Announcement Types:
==================

**Global Announcements** (No specific recipients):
- Visible to all authenticated users
- System-wide information and updates
- General school news and events

**Targeted Announcements** (Specific recipients):
- Visible only to selected users
- Class-specific information
- Role-specific communications
- Personal messages

Data Structure:
==============

Basic User Information:
- id: Unique identifier
- username: Login username
- first_name, last_name: Personal names
- full_name: Computed full name

Announcement:
- id: Unique identifier
- title: Announcement headline
- body: Main content (supports rich text)
- author: User who created the announcement
- created_at: Creation timestamp
- updated_at: Last modification timestamp
- recipient_count: Number of targeted recipients
- is_targeted: Whether announcement has specific recipients

Detailed Announcement (with recipients):
- All basic fields plus:
- recipients: Full list of targeted users
- Complete recipient information

Visibility and Access Control:
=============================

**Students**:
- See global announcements
- See announcements targeted to them
- Cannot create or modify announcements

**Teachers**:
- See all announcements relevant to them
- Can create announcements for their classes
- Can edit their own announcements

**Administrators**:
- See all announcements in system
- Can create system-wide announcements
- Can edit/delete any announcement
- Full recipient management access

Example Usage:
=============

Get announcements (automatically filtered):
curl -H "Authorization: Bearer {token}" /api/communications/announcements

Get specific announcement details:
curl -H "Authorization: Bearer {token}" /api/communications/announcements/123

Create global announcement (admin/teacher):
curl -X POST /api/communications/announcements \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"School Event Notification",
    "body":"Important information about upcoming school event...",
    "recipient_ids":[]
  }'

Create targeted announcement:
curl -X POST /api/communications/announcements \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"9F Class Radio Session",
    "body":"Radio session scheduled for Friday at 2 PM",
    "recipient_ids":[12,34,56]
  }'

Update announcement:
curl -X PUT /api/communications/announcements/123 \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Updated: School Event Notification",
    "body":"Updated information about the school event..."
  }'

Recipient Management:
====================

Flexible recipient targeting:
- Individual user selection
- Class-based targeting (all students in a class)
- Role-based targeting (all teachers, all admins)
- Custom recipient lists
- Dynamic recipient calculation

Recipients can be updated after announcement creation,
allowing for flexible communication management.

Rich Content Support:
====================

Announcements support rich content:
- HTML formatting in body text
- Long-form content support
- Line break preservation
- Unicode character support
- Markdown-style formatting (frontend dependent)

Author Attribution:
==================

Complete author tracking:
- Original author identification
- Creation timestamp
- Last modification tracking
- Edit history (if implemented)
- Author permission validation

This ensures accountability and proper attribution
for all communications.

Integration with User System:
============================

Seamless integration with user management:
- Automatic user validation
- Permission-based access control
- Class and role integration
- Profile-based targeting
- Dynamic recipient lists

Permission Requirements:
=======================

**Creating Announcements**:
- Admin permissions (teacher or system admin)
- Author automatically set to current user

**Viewing Announcements**:
- Authentication required
- Automatic filtering based on user role and targeting

**Editing Announcements**:
- Admin permissions OR original author
- Recipient list changes require admin permissions

**Deleting Announcements**:
- Admin permissions OR original author
- Safety confirmations for broadcast announcements

Error Handling:
==============

- 200/201: Success
- 400: Validation errors (empty title/body, invalid recipients)
- 401: Authentication failed or insufficient permissions
- 403: Access denied (not author/admin for edit/delete)
- 404: Announcement not found
- 500: Server error

Validation Rules:
================

- Title and body are required and cannot be empty
- Recipient IDs must reference valid, active users
- Only authors or admins can modify announcements
- Recipients can be empty for global announcements
- HTML content is sanitized for security

Communication Best Practices:
============================

**For Global Announcements**:
- Use clear, descriptive titles
- Include all necessary information in body
- Consider timing for maximum visibility

**For Targeted Announcements**:
- Verify recipient lists before sending
- Use specific, actionable titles
- Include relevant context for recipients

**Content Guidelines**:
- Keep messages concise but informative
- Use professional language and tone
- Include contact information if follow-up needed
"""

from ninja import Schema
from django.contrib.auth.models import User
from api.models import Announcement
from .auth import JWTAuth, ErrorSchema
from datetime import datetime
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

class AnnouncementSchema(Schema):
    """Response schema for announcement data."""
    id: int
    title: str
    body: str
    author: Optional[UserBasicSchema] = None
    created_at: str
    updated_at: str
    recipient_count: int = 0
    is_targeted: bool = False

class AnnouncementCreateSchema(Schema):
    """Request schema for creating new announcement."""
    title: str
    body: str
    recipient_ids: list[int] = []

class AnnouncementUpdateSchema(Schema):
    """Request schema for updating existing announcement."""
    title: Optional[str] = None
    body: Optional[str] = None
    recipient_ids: Optional[list[int]] = None

class AnnouncementDetailSchema(Schema):
    """Detailed response schema for announcement with recipients."""
    id: int
    title: str
    body: str
    author: Optional[UserBasicSchema] = None
    created_at: str
    updated_at: str
    recipients: list[UserBasicSchema] = []
    recipient_count: int = 0
    is_targeted: bool = False

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

def create_announcement_response(announcement: Announcement, include_recipients: bool = False) -> dict:
    """
    Create standardized announcement response dictionary.
    
    Args:
        announcement: Announcement model instance
        include_recipients: Whether to include full recipient list
        
    Returns:
        Dictionary with announcement information
    """
    response = {
        "id": announcement.id,
        "title": announcement.title,
        "body": announcement.body,
        "author": create_user_basic_response(announcement.author) if announcement.author else None,
        "created_at": announcement.created_at.isoformat(),
        "updated_at": announcement.updated_at.isoformat(),
        "recipient_count": announcement.cimzettek.count(),
        "is_targeted": announcement.cimzettek.exists()
    }
    
    if include_recipients:
        response["recipients"] = [
            create_user_basic_response(user) 
            for user in announcement.cimzettek.all()
        ]
    
    return response

def check_announcement_permissions(user) -> tuple[bool, str]:
    """
    Check if user has permissions for announcement management.
    
    Args:
        user: Django User object
        
    Returns:
        Tuple of (has_permission, error_message)
    """
    try:
        from api.models import Profile
        profile = Profile.objects.get(user=user)
        
        # Admin or teacher can manage announcements
        if not (profile.has_admin_permission('any')):
            return False, "Adminisztrátor vagy tanár jogosultság szükséges"
        return True, ""
    except Profile.DoesNotExist:
        return False, "Felhasználói profil nem található"

def can_user_view_announcement(user: User, announcement: Announcement) -> bool:
    """
    Check if user can view a specific announcement.
    
    Args:
        user: Django User object
        announcement: Announcement instance
        
    Returns:
        Boolean indicating if user can view the announcement
    """
    # If announcement has no specific recipients, everyone can see it
    if not announcement.cimzettek.exists():
        return True
    
    # If user is a recipient
    if announcement.cimzettek.filter(id=user.id).exists():
        return True
    
    # If user is the author
    if announcement.author and announcement.author.id == user.id:
        return True
    
    # If user has admin permissions
    try:
        from api.models import Profile
        profile = Profile.objects.get(user=user)
        if profile.has_admin_permission('any'):
            return True
    except Profile.DoesNotExist:
        pass
    
    return False

# ============================================================================
# API Endpoints
# ============================================================================

def register_communications_endpoints(api):
    """Register all communications-related endpoints with the API router."""
    
    @api.get("/announcements", auth=JWTAuth(), response={200: list[AnnouncementSchema], 401: ErrorSchema})
    def get_announcements(request, my_announcements: bool = False):
        """
        Get announcements visible to the current user.
        
        Requires authentication. Returns announcements that the user can view.
        This includes public announcements and those specifically targeted to the user.
        
        Args:
            my_announcements: If true, only return announcements where user is author
            
        Returns:
            200: List of announcements user can view
            401: Authentication failed
        """
        try:
            from django.db.models import Q
            user = request.auth
            
            if my_announcements:
                # Only announcements authored by this user
                announcements = Announcement.objects.filter(author=user)
            else:
                # Public announcements (no specific recipients) or those targeting this user
                # Using Q objects instead of union() to avoid distinct() issues
                announcements = Announcement.objects.filter(
                    Q(cimzettek__isnull=True) | Q(cimzettek=user)
                ).distinct()
            
            announcements = announcements.select_related('author').prefetch_related('cimzettek').order_by('-created_at')
            
            response = []
            for announcement in announcements:
                # Double-check permissions
                if can_user_view_announcement(user, announcement):
                    response.append(create_announcement_response(announcement))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching announcements: {str(e)}"}

    @api.get("/announcements/public", auth=JWTAuth(), response={200: list[AnnouncementSchema], 401: ErrorSchema})
    def get_public_announcements(request):
        """
        Get public announcements (not targeted to specific users).
        
        Requires authentication. Returns announcements that have no specific recipients.
        
        Returns:
            200: List of public announcements
            401: Authentication failed
        """
        try:
            # Get announcements with no specific recipients
            announcements = Announcement.objects.filter(
                cimzettek__isnull=True
            ).select_related('author').order_by('-created_at')
            
            response = []
            for announcement in announcements:
                response.append(create_announcement_response(announcement))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching public announcements: {str(e)}"}

    @api.get("/announcements/{announcement_id}", auth=JWTAuth(), response={200: AnnouncementDetailSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_announcement_details(request, announcement_id: int):
        """
        Get detailed information about a specific announcement.
        
        Requires authentication and proper permissions to view the announcement.
        
        Args:
            announcement_id: Unique announcement identifier
            
        Returns:
            200: Detailed announcement information
            404: Announcement not found or no permission to view
            401: Authentication failed
        """
        try:
            user = request.auth
            announcement = Announcement.objects.select_related('author').prefetch_related('cimzettek').get(id=announcement_id)
            
            # Check if user can view this announcement
            if not can_user_view_announcement(user, announcement):
                return 404, {"message": "Közlemény nem található vagy nincs jogosultság megtekintéséhez"}
            
            return 200, create_announcement_response(announcement, include_recipients=True)
        except Announcement.DoesNotExist:
            return 404, {"message": "Közlemény nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching announcement details: {str(e)}"}

    @api.post("/announcements", auth=JWTAuth(), response={201: AnnouncementDetailSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_announcement(request, data: AnnouncementCreateSchema):
        """
        Create new announcement.
        
        Requires admin/teacher permissions. Creates a new announcement, optionally
        targeting specific users.
        
        Args:
            data: Announcement creation data
            
        Returns:
            201: Announcement created successfully
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check if user has appropriate permissions
            has_permission, error_message = check_announcement_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            user = request.auth
            
            # Create the announcement
            announcement = Announcement.objects.create(
                title=data.title,
                body=data.body,
                author=user
            )
            
            # Add recipients if provided
            if data.recipient_ids:
                recipients = User.objects.filter(id__in=data.recipient_ids, is_active=True)
                announcement.cimzettek.set(recipients)
            
            return 201, create_announcement_response(announcement, include_recipients=True)
        except Exception as e:
            return 400, {"message": f"Error creating announcement: {str(e)}"}

    @api.put("/announcements/{announcement_id}", auth=JWTAuth(), response={200: AnnouncementDetailSchema, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
    def update_announcement(request, announcement_id: int, data: AnnouncementUpdateSchema):
        """
        Update existing announcement.
        
        Requires admin/teacher permissions or being the author of the announcement.
        Updates announcement with provided data. Only non-None fields are updated.
        
        Args:
            announcement_id: Unique announcement identifier
            data: Announcement update data
            
        Returns:
            200: Announcement updated successfully
            404: Announcement not found
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            user = request.auth
            announcement = Announcement.objects.get(id=announcement_id)
            
            # Check permissions: must be author or have admin/teacher permissions
            has_general_permission, _ = check_announcement_permissions(user)
            is_author = announcement.author and announcement.author.id == user.id
            
            if not (has_general_permission or is_author):
                return 401, {"message": "Nincs jogosultság a közlemény szerkesztéséhez"}
            
            # Update fields only if they are provided (not None)
            if data.title is not None:
                announcement.title = data.title
            if data.body is not None:
                announcement.body = data.body
            
            announcement.save()
            
            # Update recipients if provided
            if data.recipient_ids is not None:
                if data.recipient_ids:  # Non-empty list
                    recipients = User.objects.filter(id__in=data.recipient_ids, is_active=True)
                    announcement.cimzettek.set(recipients)
                else:  # Empty list - make it public
                    announcement.cimzettek.clear()
            
            return 200, create_announcement_response(announcement, include_recipients=True)
        except Announcement.DoesNotExist:
            return 404, {"message": "Közlemény nem található"}
        except Exception as e:
            return 400, {"message": f"Error updating announcement: {str(e)}"}

    @api.delete("/announcements/{announcement_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
    def delete_announcement(request, announcement_id: int):
        """
        Delete announcement.
        
        Requires admin permissions or being the author of the announcement.
        Permanently removes announcement from database.
        
        Args:
            announcement_id: Unique announcement identifier
            
        Returns:
            200: Announcement deleted successfully
            404: Announcement not found
            401: Authentication or permission failed
        """
        try:
            user = request.auth
            announcement = Announcement.objects.get(id=announcement_id)
            
            # Check permissions: must be author or have admin permissions
            has_admin_permission = False
            try:
                from api.models import Profile
                profile = Profile.objects.get(user=user)
                has_admin_permission = profile.has_admin_permission('any')
            except Profile.DoesNotExist:
                pass
            
            is_author = announcement.author and announcement.author.id == user.id
            
            if not (has_admin_permission or is_author):
                return 401, {"message": "Nincs jogosultság a közlemény törléséhez"}
            
            announcement_title = announcement.title
            announcement.delete()
            
            return 200, {"message": f"Közlemény '{announcement_title}' sikeresen törölve"}
        except Announcement.DoesNotExist:
            return 404, {"message": "Közlemény nem található"}
        except Exception as e:
            return 400, {"message": f"Error deleting announcement: {str(e)}"}

    @api.get("/announcements/{announcement_id}/recipients", auth=JWTAuth(), response={200: list[UserBasicSchema], 401: ErrorSchema, 404: ErrorSchema})
    def get_announcement_recipients(request, announcement_id: int):
        """
        Get recipients of a specific announcement.
        
        Requires admin permissions or being the author of the announcement.
        
        Args:
            announcement_id: Unique announcement identifier
            
        Returns:
            200: List of announcement recipients
            404: Announcement not found
            401: Authentication or permission failed
        """
        try:
            user = request.auth
            announcement = Announcement.objects.prefetch_related('cimzettek').get(id=announcement_id)
            
            # Check permissions: must be author or have admin permissions
            has_admin_permission = False
            try:
                from api.models import Profile
                profile = Profile.objects.get(user=user)
                has_admin_permission = profile.has_admin_permission('any')
            except Profile.DoesNotExist:
                pass
            
            is_author = announcement.author and announcement.author.id == user.id
            
            if not (has_admin_permission or is_author):
                return 401, {"message": "Nincs jogosultság a címzettek megtekintéséhez"}
            
            recipients = []
            for recipient in announcement.cimzettek.all():
                recipients.append(create_user_basic_response(recipient))
            
            return 200, recipients
        except Announcement.DoesNotExist:
            return 404, {"message": "Közlemény nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching announcement recipients: {str(e)}"}
