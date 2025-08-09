"""
Core API utilities and basic endpoints.
Contains general-purpose endpoints and utility functions.
"""

from datetime import datetime

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
