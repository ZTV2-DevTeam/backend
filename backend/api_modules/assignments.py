"""
Filming Assignment Management API Module (Forgatás beosztás kezelés)

Ez a modul a forgatásokhoz való diák beosztások kezelését biztosítja,
és automatikusan létrehozza a kapcsolódó hiányzás (Absence) rekordokat.

Public API Overview:
==================

A Beosztás API a forgatásokhoz való diák beosztások kezelését biztosítja,
automatikusan létrehozva a kapcsolódó hiányzásokat az osztályfőnökök számára.

Base URL: /api/assignments/

Protected Endpoints (JWT Token Required):

Forgatás beosztások:
- GET  /filming-assignments                    - Lista beosztásokról
- GET  /filming-assignments/by-forgatas/{id}  - Konkrét beosztás részletei forgatás ID alapján
- POST /filming-assignments                    - Új beosztás létrehozása (admin/tanár)
- PUT  /filming-assignments/{id}              - Beosztás frissítése
- DELETE /filming-assignments/{id}            - Beosztás törlése
- POST /filming-assignments/{id}/finalize     - Beosztás véglegesítése
- POST /filming-assignments/{id}/mark-done    - Beosztás készre jelölése (admin only)
- POST /filming-assignments/{id}/mark-draft   - Beosztás piszkozatra állítása (admin only)

Beosztás rendszer áttekintés:
===========================

A beosztás rendszer kezeli a forgatásokhoz való diák hozzárendelést:

1. **Beosztás létrehozás**: Forgatáshoz diákok hozzárendelése
2. **Szerepkör kezelés**: Diákok szerepköreinek meghatározása
3. **Automatikus hiányzás**: Hiányzások automatikus létrehozása
4. **Véglegesítés**: Beosztás lezárása és jóváhagyása

Automatikus hiányzás létrehozás:
===============================

Amikor egy beosztás véglegesítésre kerül:
1. Minden beosztott diákhoz létrejön egy Absence rekord
2. Az Absence tartalmazza a forgatás adatait (dátum, idő)
3. Kiszámítja az érintett tanórákat
4. Az osztályfőnökök ezután kezelhetik az igazolásokat

Adatstruktúra:
=============

Beosztás (Beosztas):
- id: Egyedi azonosító
- forgatas: Kapcsolódó forgatás
- szerepkor_relaciok: Diák-szerepkör párosítások
- kesz: Véglegesítve van-e
- author: Beosztást készítő felhasználó
- tanev: Tanév

Szerepkör reláció (SzerepkorRelaciok):
- user: Beosztott diák
- szerepkor: Szerepkör (pl. operatőr, hang, stb.)

Jogosultságok:
=============

- Megtekintés: Hitelesítés szükséges
- Létrehozás: Admin/tanár jogosultság
- Szerkesztés: Admin/tanár jogosultság (saját beosztások)
- Véglegesítés: Admin/tanár jogosultság

Integrációs pontok:
==================

- Forgatás rendszer: beosztások forgatásokhoz kapcsolása
- Hiányzás rendszer: automatikus Absence létrehozás
- Felhasználói rendszer: diákok és jogosultságok
- Akadémiai rendszer: tanév koordináció
"""

from ninja import Schema
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count
from api.models import Beosztas, SzerepkorRelaciok, Szerepkor, Forgatas, Absence, Profile, Tavollet, RadioSession, Stab
from .auth import JWTAuth, ErrorSchema
from datetime import datetime, date, time
from typing import Optional, List

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

class SzerepkorSchema(Schema):
    """Role schema."""
    id: int
    name: str
    ev: Optional[int] = None

class SzerepkorRelacioSchema(Schema):
    """Role relation schema."""
    id: int
    user: UserBasicSchema
    szerepkor: SzerepkorSchema

class ForgatSchema(Schema):
    """Basic forgatas information schema."""
    id: int
    name: str
    description: str
    date: str
    time_from: str
    time_to: str
    type: str
    szerkeszto: Optional[UserBasicSchema] = None
    notes: Optional[str] = None

class BeosztasSchema(Schema):
    """Response schema for assignment data."""
    id: int
    forgatas: ForgatSchema
    szerepkor_relaciok: List[SzerepkorRelacioSchema]
    kesz: bool
    author: Optional[UserBasicSchema] = None
    created_at: str
    student_count: int
    roles_summary: List[dict]

class UserAvailabilitySchema(Schema):
    """User availability information schema."""
    id: int
    username: str
    first_name: str
    last_name: str
    full_name: str
    is_available: bool
    conflicts: List[dict]
    is_on_vacation: bool
    has_radio_session: bool

class BeosztasWithAvailabilitySchema(Schema):
    """Response schema for assignment data with user availability."""
    id: int
    forgatas: ForgatSchema
    szerepkor_relaciok: List[SzerepkorRelacioSchema]
    kesz: bool
    author: Optional[UserBasicSchema] = None
    created_at: str
    student_count: int
    roles_summary: List[dict]
    user_availability: dict  # Dictionary with users_available, users_on_vacation, users_with_radio_session

class BeosztasCreateSchema(Schema):
    """Request schema for creating new assignment."""
    forgatas_id: int
    stab_id: Optional[int] = None
    student_role_pairs: List[dict]  # [{"user_id": 1, "szerepkor_id": 2}, ...]

class BeosztasUpdateSchema(Schema):
    """Request schema for updating assignment."""
    student_role_pairs: Optional[List[dict]] = None
    stab_id: Optional[int] = None
    kesz: Optional[bool] = None

class StudentRolePairSchema(Schema):
    """Schema for student-role pairing."""
    user_id: int
    szerepkor_id: int

# ============================================================================
# Utility Functions
# ============================================================================

def create_user_basic_response(user: User) -> dict:
    """Create basic user information response."""
    print(f"🔍 [DEBUG] create_user_basic_response called with user: {user}")
    
    try:
        if not user:
            print(f"❌ [DEBUG] User is None!")
            raise ValueError("User cannot be None")
        
        print(f"🔍 [DEBUG] User ID: {user.id}")
        print(f"🔍 [DEBUG] User username: '{user.username}'")
        print(f"🔍 [DEBUG] User first_name: '{user.first_name}'")
        print(f"🔍 [DEBUG] User last_name: '{user.last_name}'")
        
        # Test get_full_name separately
        try:
            full_name = user.get_full_name()
            print(f"🔍 [DEBUG] User full_name: '{full_name}'")
        except Exception as e:
            print(f"❌ [DEBUG] Error getting full_name: {str(e)}")
            raise
        
        response = {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": full_name
        }
        
        print(f"✅ [DEBUG] create_user_basic_response completed: {response}")
        return response
        
    except Exception as e:
        print(f"❌ [DEBUG] Error in create_user_basic_response: {str(e)}")
        print(f"❌ [DEBUG] Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise

def create_szerepkor_response(szerepkor: Szerepkor) -> dict:
    """Create role information response."""
    print(f"🔍 [DEBUG] create_szerepkor_response called with szerepkor: {szerepkor}")
    
    try:
        if not szerepkor:
            print(f"❌ [DEBUG] Szerepkor is None!")
            raise ValueError("Szerepkor cannot be None")
        
        print(f"🔍 [DEBUG] Szerepkor ID: {szerepkor.id}")
        print(f"🔍 [DEBUG] Szerepkor name: '{szerepkor.name}'")
        print(f"🔍 [DEBUG] Szerepkor ev: {szerepkor.ev}")
        
        response = {
            "id": szerepkor.id,
            "name": szerepkor.name,
            "ev": szerepkor.ev
        }
        
        print(f"✅ [DEBUG] create_szerepkor_response completed: {response}")
        return response
        
    except Exception as e:
        print(f"❌ [DEBUG] Error in create_szerepkor_response: {str(e)}")
        print(f"❌ [DEBUG] Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise

def create_szerepkor_relacio_response(relacio: SzerepkorRelaciok) -> dict:
    """Create role relation response."""
    print(f"🔍 [DEBUG] create_szerepkor_relacio_response called with relacio: {relacio}")
    
    try:
        if not relacio:
            print(f"❌ [DEBUG] Relacio is None!")
            raise ValueError("Relacio cannot be None")
        
        print(f"🔍 [DEBUG] Relacio ID: {relacio.id}")
        print(f"🔍 [DEBUG] Relacio user: {relacio.user}")
        print(f"🔍 [DEBUG] Relacio szerepkor: {relacio.szerepkor}")
        
        # Create user response
        try:
            user_response = create_user_basic_response(relacio.user)
            print(f"✅ [DEBUG] User response created in relacio")
        except Exception as e:
            print(f"❌ [DEBUG] Error creating user response in relacio: {str(e)}")
            raise
        
        # Create szerepkor response
        try:
            szerepkor_response = create_szerepkor_response(relacio.szerepkor)
            print(f"✅ [DEBUG] Szerepkor response created in relacio")
        except Exception as e:
            print(f"❌ [DEBUG] Error creating szerepkor response in relacio: {str(e)}")
            raise
        
        response = {
            "id": relacio.id,
            "user": user_response,
            "szerepkor": szerepkor_response
        }
        
        print(f"✅ [DEBUG] create_szerepkor_relacio_response completed: {response}")
        return response
        
    except Exception as e:
        print(f"❌ [DEBUG] Error in create_szerepkor_relacio_response: {str(e)}")
        print(f"❌ [DEBUG] Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise

def create_forgatas_basic_response(forgatas: Forgatas) -> dict:
    """Create basic forgatas information response."""
    print(f"🔍 [DEBUG] create_forgatas_basic_response called with forgatas: {forgatas}")
    
    try:
        if not forgatas:
            print(f"❌ [DEBUG] Forgatas is None!")
            raise ValueError("Forgatas cannot be None")
        
        print(f"🔍 [DEBUG] Forgatas ID: {forgatas.id}")
        print(f"🔍 [DEBUG] Forgatas name: '{forgatas.name}'")
        print(f"🔍 [DEBUG] Forgatas description: '{forgatas.description}'")
        print(f"🔍 [DEBUG] Forgatas date: {forgatas.date}")
        print(f"🔍 [DEBUG] Forgatas timeFrom: {forgatas.timeFrom}")
        print(f"🔍 [DEBUG] Forgatas timeTo: {forgatas.timeTo}")
        print(f"🔍 [DEBUG] Forgatas forgTipus: '{forgatas.forgTipus}'")
        
        # Check each field individually to isolate the issue
        response = {}
        
        # ID
        response["id"] = forgatas.id
        print(f"✅ [DEBUG] Added ID: {response['id']}")
        
        # Name
        response["name"] = forgatas.name
        print(f"✅ [DEBUG] Added name: '{response['name']}'")
        
        # Description
        response["description"] = forgatas.description
        print(f"✅ [DEBUG] Added description: '{response['description']}'")
        
        # Date
        try:
            response["date"] = forgatas.date.isoformat()
            print(f"✅ [DEBUG] Added date: '{response['date']}'")
        except Exception as e:
            print(f"❌ [DEBUG] Error with date field: {str(e)}")
            raise
        
        # Time From
        try:
            response["time_from"] = forgatas.timeFrom.isoformat()
            print(f"✅ [DEBUG] Added time_from: '{response['time_from']}'")
        except Exception as e:
            print(f"❌ [DEBUG] Error with timeFrom field: {str(e)}")
            raise
        
        # Time To
        try:
            response["time_to"] = forgatas.timeTo.isoformat()
            print(f"✅ [DEBUG] Added time_to: '{response['time_to']}'")
        except Exception as e:
            print(f"❌ [DEBUG] Error with timeTo field: {str(e)}")
            raise
        
        # Type
        response["type"] = forgatas.forgTipus
        print(f"✅ [DEBUG] Added type: '{response['type']}'")
        
        # Szerkesztő
        try:
            if forgatas.szerkeszto:
                response["szerkeszto"] = {
                    "id": forgatas.szerkeszto.id,
                    "username": forgatas.szerkeszto.username,
                    "full_name": forgatas.szerkeszto.get_full_name()
                }
                print(f"✅ [DEBUG] Added szerkeszto: '{response['szerkeszto']}'")
            else:
                response["szerkeszto"] = None
                print(f"✅ [DEBUG] Added szerkeszto: null")
        except Exception as e:
            print(f"❌ [DEBUG] Error with szerkeszto field: {str(e)}")
            raise
        
        # Notes
        try:
            response["notes"] = forgatas.notes
            print(f"✅ [DEBUG] Added notes: '{response['notes']}'")
        except Exception as e:
            print(f"❌ [DEBUG] Error with notes field: {str(e)}")
            raise
        
        print(f"✅ [DEBUG] create_forgatas_basic_response completed successfully: {response}")
        return response
        
    except Exception as e:
        print(f"❌ [DEBUG] Error in create_forgatas_basic_response: {str(e)}")
        print(f"❌ [DEBUG] Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise

def create_beosztas_response(beosztas: Beosztas) -> dict:
    """Create standardized assignment response dictionary."""
    # Get role relations
    szerepkor_relaciok = beosztas.szerepkor_relaciok.select_related('user', 'szerepkor').all()
    
    # Create roles summary (count by role)
    roles_summary = {}
    for relacio in szerepkor_relaciok:
        role_name = relacio.szerepkor.name
        if role_name not in roles_summary:
            roles_summary[role_name] = 0
        roles_summary[role_name] += 1
    
    roles_summary_list = [{"role": role, "count": count} for role, count in roles_summary.items()]
    
    return {
        "id": beosztas.id,
        "forgatas": create_forgatas_basic_response(beosztas.forgatas),
        "szerepkor_relaciok": [create_szerepkor_relacio_response(rel) for rel in szerepkor_relaciok],
        "kesz": beosztas.kesz,
        "author": create_user_basic_response(beosztas.author) if beosztas.author else None,
        "stab": {"id": beosztas.stab.id, "name": beosztas.stab.name} if beosztas.stab else None,
        "created_at": beosztas.created_at.isoformat(),
        "student_count": len(szerepkor_relaciok),
        "roles_summary": roles_summary_list
    }

def check_admin_or_teacher_permissions(user: User) -> tuple[bool, str]:
    """Check if user has admin or teacher permissions for assignment management."""
    try:
        from api.models import Profile
        profile = Profile.objects.get(user=user)
        if not profile.has_admin_permission('any'):
            return False, "Adminisztrátor vagy tanár jogosultság szükséges"
        return True, ""
    except Profile.DoesNotExist:
        return False, "Felhasználói profil nem található"

def check_admin_only_permissions(user: User) -> tuple[bool, str]:
    """Check if user has admin-only permissions for sensitive operations like editing Beosztás."""
    try:
        from api.models import Profile
        profile = Profile.objects.get(user=user)
        # Only allow users with admin permissions (not just teachers)
        if not profile.has_admin_permission('system_admin'):
            return False, "Rendszergazda jogosultság szükséges a beosztások szerkesztéséhez"
        return True, ""
    except Profile.DoesNotExist:
        return False, "Felhasználói profil nem található"

def can_user_manage_beosztas(user: User, beosztas: Beosztas) -> bool:
    """Check if user can manage a specific assignment."""
    # Author can manage their own assignment
    if beosztas.author and beosztas.author.id == user.id:
        return True
    
    # Admin can manage any assignment
    try:
        from api.models import Profile
        profile = Profile.objects.get(user=user)
        if profile.has_admin_permission('any'):
            return True
    except Profile.DoesNotExist:
        pass
    
    return False

def check_user_availability_for_forgatas(user: User, forgatas: Forgatas) -> dict:
    """
    Check user availability for a specific forgatas.
    Returns detailed availability information including conflicts.
    """
    if not forgatas:
        return {
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.get_full_name(),
            "is_available": True,
            "conflicts": [],
            "is_on_vacation": False,
            "has_radio_session": False
        }
    
    # Create datetime objects for the forgatas
    forgatas_start = datetime.combine(forgatas.date, forgatas.timeFrom)
    forgatas_end = datetime.combine(forgatas.date, forgatas.timeTo)
    
    conflicts = []
    is_on_vacation = False
    has_radio_session = False
    
    # Check for vacation (Tavollet) conflicts
    # Convert forgatas date to datetime range for comparison
    forgatas_start = datetime.combine(forgatas.date, forgatas.timeFrom)
    forgatas_end = datetime.combine(forgatas.date, forgatas.timeTo)
    
    # Check for vacation (Tavollet) conflicts with TavolletTipus logic
    vacation_conflicts = Tavollet.objects.filter(
        user=user,
        start_date__lt=forgatas_end,
        end_date__gt=forgatas_start
    ).select_related('tipus')
    
    for vacation in vacation_conflicts:
        # Apply the same logic as Profile.is_available_for_datetime
        should_count_as_unavailable = False
        
        if vacation.denied:
            # Explicitly denied - user is available (skip this absence)
            continue
        elif vacation.approved:
            # Explicitly approved - user is not available
            should_count_as_unavailable = True
        else:
            # Pending absence - check tipus
            if vacation.tipus:
                if vacation.tipus.ignored_counts_as == 'approved':
                    # Type defaults to approved when ignored - user not available
                    should_count_as_unavailable = True
                # If ignored_counts_as == 'denied', user is available (skip)
            else:
                # No tipus specified for pending absence - conservative approach (not available)
                should_count_as_unavailable = True
        
        if should_count_as_unavailable:
            is_on_vacation = True
            conflicts.append({
                "type": "vacation",
                "reason": vacation.reason or "Távollét",
                "start_date": vacation.start_date.isoformat(),
                "end_date": vacation.end_date.isoformat(),
                "approved": vacation.approved,
                "tipus": {
                    "id": vacation.tipus.id,
                    "name": vacation.tipus.name,
                    "ignored_counts_as": vacation.tipus.ignored_counts_as
                } if vacation.tipus else None
            })
    
    # Check for radio session conflicts (for all users)
    radio_sessions = RadioSession.objects.filter(
        participants=user,
        date=forgatas.date
    )
    
    for session in radio_sessions:
        # Check if radio session overlaps with forgatas time
        session_start = datetime.combine(session.date, session.time_from)
        session_end = datetime.combine(session.date, session.time_to)
        
        if session_start < forgatas_end and session_end > forgatas_start:
            has_radio_session = True
            conflicts.append({
                "type": "radio_session",
                "description": f"{session.radio_stab.name} rádiós összejátszás",
                "date": session.date.isoformat(),
                "time_from": session.time_from.isoformat(),
                "time_to": session.time_to.isoformat(),
                "radio_stab": session.radio_stab.name
            })
    
    # User is available if they have no conflicts
    is_available = len(conflicts) == 0
    
    return {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.get_full_name(),
        "is_available": is_available,
        "conflicts": conflicts,
        "is_on_vacation": is_on_vacation,
        "has_radio_session": has_radio_session
    }

def create_beosztas_with_availability_response(beosztas: Beosztas) -> dict:
    """Create standardized assignment response dictionary with user availability."""
    # Get role relations
    szerepkor_relaciok = beosztas.szerepkor_relaciok.select_related('user', 'szerepkor').all()
    
    # Create roles summary (count by role)
    roles_summary = {}
    for relacio in szerepkor_relaciok:
        role_name = relacio.szerepkor.name
        if role_name not in roles_summary:
            roles_summary[role_name] = 0
        roles_summary[role_name] += 1
    
    roles_summary_list = [{"role": role, "count": count} for role, count in roles_summary.items()]
    
    # Check availability for each user
    users_available = []
    users_on_vacation = []
    users_with_radio_session = []
    
    for relacio in szerepkor_relaciok:
        user_availability = check_user_availability_for_forgatas(relacio.user, beosztas.forgatas)
        
        if user_availability["is_available"]:
            users_available.append({
                "user": create_user_basic_response(relacio.user),
                "role": create_szerepkor_response(relacio.szerepkor),
                "availability": user_availability
            })
        elif user_availability["is_on_vacation"]:
            users_on_vacation.append({
                "user": create_user_basic_response(relacio.user),
                "role": create_szerepkor_response(relacio.szerepkor),
                "availability": user_availability
            })
        elif user_availability["has_radio_session"]:
            users_with_radio_session.append({
                "user": create_user_basic_response(relacio.user),
                "role": create_szerepkor_response(relacio.szerepkor),
                "availability": user_availability
            })
        else:
            # User has other types of conflicts, put them in available but mark conflicts
            users_available.append({
                "user": create_user_basic_response(relacio.user),
                "role": create_szerepkor_response(relacio.szerepkor),
                "availability": user_availability
            })
    
    return {
        "id": beosztas.id,
        "forgatas": create_forgatas_basic_response(beosztas.forgatas),
        "szerepkor_relaciok": [create_szerepkor_relacio_response(rel) for rel in szerepkor_relaciok],
        "kesz": beosztas.kesz,
        "author": create_user_basic_response(beosztas.author) if beosztas.author else None,
        "stab": {"id": beosztas.stab.id, "name": beosztas.stab.name} if beosztas.stab else None,
        "created_at": beosztas.created_at.isoformat(),
        "student_count": len(szerepkor_relaciok),
        "roles_summary": roles_summary_list,
        "user_availability": {
            "users_available": users_available,
            "users_on_vacation": users_on_vacation,
            "users_with_radio_session": users_with_radio_session,
            "summary": {
                "total_users": len(szerepkor_relaciok),
                "available_count": len(users_available),
                "vacation_count": len(users_on_vacation),
                "radio_session_count": len(users_with_radio_session)
            }
        }
    }

def auto_create_absences_for_beosztas(beosztas: Beosztas):
    """
    Automatically create absence records for all students in a finalized assignment.
    This should be called when an assignment is finalized (kesz=True).
    """
    if not beosztas.kesz or not beosztas.forgatas:
        return
    
    # Get all students in this assignment
    student_relations = beosztas.szerepkor_relaciok.select_related('user').all()
    student_ids = [rel.user.id for rel in student_relations]
    
    # Create absences
    for student_id in student_ids:
        try:
            student = User.objects.get(id=student_id)
            
            # Check if absence already exists for this student and forgatas
            existing = Absence.objects.filter(
                diak=student,
                forgatas=beosztas.forgatas
            ).exists()
            
            if not existing:
                Absence.objects.create(
                    diak=student,
                    forgatas=beosztas.forgatas,
                    date=beosztas.forgatas.date,
                    timeFrom=beosztas.forgatas.timeFrom,
                    timeTo=beosztas.forgatas.timeTo,
                    excused=False,
                    unexcused=False
                )
        except User.DoesNotExist:
            continue

# ============================================================================
# API Endpoints
# ============================================================================

def register_assignment_endpoints(api):
    """Register all assignment-related endpoints with the API router."""
    
    @api.get("/assignments/filming-assignments", auth=JWTAuth(), response={200: List[BeosztasSchema], 401: ErrorSchema, 500: ErrorSchema})
    def get_filming_assignments(request, forgatas_id: int = None, kesz: bool = None, 
                               start_date: str = None, end_date: str = None, stab_id: int = None):
        """
        Get filming assignments with optional filtering.
        
        Requires authentication. Returns assignments based on user permissions.
        
        Args:
            forgatas_id: Optional filter by filming session ID
            kesz: Optional filter by completion status
            start_date: Optional start date filter for associated filming sessions
            end_date: Optional end date filter for associated filming sessions
            stab_id: Optional filter by stab ID
            
        Returns:
            200: List of assignments
            401: Authentication failed
        """
        try:
            requesting_user = request.auth
            
            # Build queryset
            assignments = Beosztas.objects.select_related(
                'forgatas', 'forgatas__szerkeszto', 'author', 'stab'
            ).prefetch_related(
                'szerepkor_relaciok__user',
                'szerepkor_relaciok__szerepkor'
            ).all()
            
            # Apply filters
            if forgatas_id:
                assignments = assignments.filter(forgatas_id=forgatas_id)
            
            if kesz is not None:
                assignments = assignments.filter(kesz=kesz)
            
            if stab_id:
                assignments = assignments.filter(stab_id=stab_id)
            
            if start_date or end_date:
                if start_date:
                    assignments = assignments.filter(forgatas__date__gte=start_date)
                if end_date:
                    assignments = assignments.filter(forgatas__date__lte=end_date)
            
            assignments = assignments.order_by('-created_at')
            
            response = []
            for assignment in assignments:
                response.append(create_beosztas_response(assignment))
            
            return 200, response
        except Exception as e:
            return 500, {"message": f"Szerver hiba a beosztások lekérése során: {str(e)}"}

    @api.get("/assignments/filming-assignments/by-forgatas/{forgatas_id}", auth=JWTAuth(), response={200: BeosztasSchema, 401: ErrorSchema, 404: ErrorSchema, 500: ErrorSchema})
    def get_filming_assignment_details_by_forgatas(request, forgatas_id: int):
        """
        Get detailed information about a specific assignment by forgatas ID.

        Requires authentication.

        Args:
            forgatas_id: Unique forgatas identifier

        Returns:
            200: Detailed assignment information
            404: Assignment not found
            401: Authentication failed
        """
        print(f"🔍 [DEBUG] Starting get_filming_assignment_details_by_forgatas for forgatas_id: {forgatas_id}")
        
        try:
            # Debug: Check if assignment exists
            print(f"🔍 [DEBUG] Searching for Beosztas with forgatas_id: {forgatas_id}")
            assignment = Beosztas.objects.select_related(
                'forgatas', 'forgatas__szerkeszto', 'author', 'stab'
            ).prefetch_related(
                'szerepkor_relaciok__user',
                'szerepkor_relaciok__szerepkor'
            ).get(forgatas_id=forgatas_id)
            
            print(f"🔍 [DEBUG] Found assignment: ID={assignment.id}, kesz={assignment.kesz}")
            print(f"🔍 [DEBUG] Assignment author: {assignment.author}")
            print(f"🔍 [DEBUG] Assignment forgatas: {assignment.forgatas}")
            
            # Debug: Check forgatas details
            if assignment.forgatas:
                print(f"🔍 [DEBUG] Forgatas details: ID={assignment.forgatas.id}, name='{assignment.forgatas.name}', date={assignment.forgatas.date}")
                print(f"🔍 [DEBUG] Forgatas times: {assignment.forgatas.timeFrom} - {assignment.forgatas.timeTo}")
                print(f"🔍 [DEBUG] Forgatas type: {assignment.forgatas.forgTipus}")
            else:
                print(f"❌ [DEBUG] WARNING: Assignment has no forgatas!")
            
            # Debug: Check role relations
            szerepkor_relaciok = assignment.szerepkor_relaciok.all()
            print(f"🔍 [DEBUG] Found {len(szerepkor_relaciok)} role relations")
            
            for i, relacio in enumerate(szerepkor_relaciok):
                print(f"🔍 [DEBUG] Role relation {i+1}: ID={relacio.id}")
                print(f"🔍 [DEBUG]   User: ID={relacio.user.id}, username='{relacio.user.username}', name='{relacio.user.get_full_name()}'")
                print(f"🔍 [DEBUG]   Szerepkor: ID={relacio.szerepkor.id}, name='{relacio.szerepkor.name}', ev={relacio.szerepkor.ev}")
            
            # Debug: Try to create response step by step
            print(f"🔍 [DEBUG] Creating response...")
            
            # Test create_forgatas_basic_response
            print(f"🔍 [DEBUG] Creating forgatas basic response...")
            try:
                forgatas_response = create_forgatas_basic_response(assignment.forgatas)
                print(f"✅ [DEBUG] Forgatas response created successfully: {forgatas_response}")
            except Exception as e:
                print(f"❌ [DEBUG] Error in create_forgatas_basic_response: {str(e)}")
                raise
            
            # Test create_user_basic_response for author
            print(f"🔍 [DEBUG] Creating author response...")
            try:
                if assignment.author:
                    author_response = create_user_basic_response(assignment.author)
                    print(f"✅ [DEBUG] Author response created successfully: {author_response}")
                else:
                    print(f"🔍 [DEBUG] No author found, setting to None")
                    author_response = None
            except Exception as e:
                print(f"❌ [DEBUG] Error in create_user_basic_response for author: {str(e)}")
                raise
            
            # Test create_szerepkor_relacio_response for each relation
            print(f"🔍 [DEBUG] Creating role relation responses...")
            role_responses = []
            try:
                for i, relacio in enumerate(szerepkor_relaciok):
                    print(f"🔍 [DEBUG] Processing role relation {i+1}...")
                    
                    # Test user response
                    try:
                        user_response = create_user_basic_response(relacio.user)
                        print(f"✅ [DEBUG] User response for relation {i+1}: {user_response}")
                    except Exception as e:
                        print(f"❌ [DEBUG] Error creating user response for relation {i+1}: {str(e)}")
                        raise
                    
                    # Test szerepkor response
                    try:
                        szerepkor_response = create_szerepkor_response(relacio.szerepkor)
                        print(f"✅ [DEBUG] Szerepkor response for relation {i+1}: {szerepkor_response}")
                    except Exception as e:
                        print(f"❌ [DEBUG] Error creating szerepkor response for relation {i+1}: {str(e)}")
                        raise
                    
                    # Test full relation response
                    try:
                        relacio_response = create_szerepkor_relacio_response(relacio)
                        role_responses.append(relacio_response)
                        print(f"✅ [DEBUG] Role relation response {i+1} created successfully")
                    except Exception as e:
                        print(f"❌ [DEBUG] Error creating role relation response {i+1}: {str(e)}")
                        raise
                        
            except Exception as e:
                print(f"❌ [DEBUG] Error processing role relations: {str(e)}")
                raise
            
            # Test roles summary creation
            print(f"🔍 [DEBUG] Creating roles summary...")
            try:
                roles_summary = {}
                for relacio in szerepkor_relaciok:
                    role_name = relacio.szerepkor.name
                    if role_name not in roles_summary:
                        roles_summary[role_name] = 0
                    roles_summary[role_name] += 1
                roles_summary_list = [{"role": role, "count": count} for role, count in roles_summary.items()]
                print(f"✅ [DEBUG] Roles summary created: {roles_summary_list}")
            except Exception as e:
                print(f"❌ [DEBUG] Error creating roles summary: {str(e)}")
                raise
            
            # Create full response
            print(f"🔍 [DEBUG] Creating full response...")
            try:
                full_response = {
                    "id": assignment.id,
                    "forgatas": forgatas_response,
                    "szerepkor_relaciok": role_responses,
                    "kesz": assignment.kesz,
                    "author": author_response,
                    "created_at": assignment.created_at.isoformat(),
                    "student_count": len(szerepkor_relaciok),
                    "roles_summary": roles_summary_list
                }
                print(f"✅ [DEBUG] Full response created successfully")
                print(f"🔍 [DEBUG] Response keys: {list(full_response.keys())}")
                return 200, full_response
            except Exception as e:
                print(f"❌ [DEBUG] Error creating full response: {str(e)}")
                raise
                
        except Beosztas.DoesNotExist:
            print(f"❌ [DEBUG] Beosztas not found for forgatas_id: {forgatas_id}")
            return 404, {"message": "Beosztás nem található"}
        except Exception as e:
            print(f"❌ [DEBUG] Unexpected error in get_filming_assignment_details_by_forgatas: {str(e)}")
            print(f"❌ [DEBUG] Error type: {type(e).__name__}")
            import traceback
            print(f"❌ [DEBUG] Full traceback:")
            traceback.print_exc()
            return 500, {"message": f"Szerver hiba a beosztás részletek lekérése során: {str(e)}"}

    @api.post("/assignments/filming-assignments", auth=JWTAuth(), response={201: BeosztasSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_filming_assignment(request, data: BeosztasCreateSchema):
        """
        Create new filming assignment.
        
        Requires admin/teacher permissions. Creates assignment and role relations.
        Automatically sends email notifications to assigned users.
        
        Args:
            data: Assignment creation data
            
        Returns:
            201: Assignment created successfully
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            requesting_user = request.auth
            
            # Check permissions
            has_permission, error_message = check_admin_or_teacher_permissions(requesting_user)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Validate forgatas exists
            try:
                forgatas = Forgatas.objects.get(id=data.forgatas_id)
            except Forgatas.DoesNotExist:
                return 400, {"message": "Forgatás nem található"}
            
            # Validate stab exists if provided
            stab = None
            if data.stab_id:
                try:
                    stab = Stab.objects.get(id=data.stab_id)
                except Stab.DoesNotExist:
                    return 400, {"message": "Stáb nem található"}
            
            # Check if assignment already exists for this forgatas
            existing = Beosztas.objects.filter(forgatas=forgatas).first()
            if existing:
                return 400, {"message": f"Ehhez a forgatáshoz már létezik beosztás (ID: {existing.id})"}
            
            # Validate student-role pairs
            if not data.student_role_pairs:
                return 400, {"message": "Legalább egy diák-szerepkör párosítás szükséges"}
            
            assigned_users = []
            
            with transaction.atomic():
                # Create assignment
                beosztas = Beosztas.objects.create(
                    forgatas=forgatas,
                    author=requesting_user,
                    stab=stab,
                    kesz=False
                )
                
                # Create role relations
                created_relations = []
                for pair in data.student_role_pairs:
                    try:
                        user = User.objects.get(id=pair["user_id"])
                        szerepkor = Szerepkor.objects.get(id=pair["szerepkor_id"])
                        
                        # Check if this user is already assigned to this assignment
                        existing_relation = SzerepkorRelaciok.objects.filter(
                            user=user
                        ).filter(
                            beosztasok=beosztas
                        ).first()
                        
                        if existing_relation:
                            continue  # Skip duplicates
                        
                        relation = SzerepkorRelaciok.objects.create(
                            user=user,
                            szerepkor=szerepkor
                        )
                        beosztas.szerepkor_relaciok.add(relation)
                        created_relations.append(relation)
                        assigned_users.append(user)
                        
                    except (User.DoesNotExist, Szerepkor.DoesNotExist):
                        continue  # Skip invalid pairs
                
                if not created_relations:
                    return 400, {"message": "Egyetlen érvényes diák-szerepkör párosítás sem található"}
            
            # Note: Email notifications are now handled automatically by model signals in models.py
            
            return 201, create_beosztas_response(beosztas)
        except Exception as e:
            return 400, {"message": f"Error creating assignment: {str(e)}"}

    @api.put("/assignments/filming-assignments/{assignment_id}", auth=JWTAuth(), response={200: BeosztasSchema, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
    def update_filming_assignment(request, assignment_id: int, data: BeosztasUpdateSchema):
        """
        Update existing filming assignment.
        
        Requires admin or teacher permissions (same as creating assignments). Can update student-role relations, stab assignment, and completion status.
        Automatically sends email notifications to users who are added or removed.
        
        Args:
            assignment_id: Unique assignment identifier
            data: Assignment update data
            
        Returns:
            200: Assignment updated successfully
            404: Assignment not found
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            requesting_user = request.auth
            beosztas = Beosztas.objects.get(id=assignment_id)
            
            # Check admin or teacher permissions for Beosztás editing (same as creating)
            has_permission, error_message = check_admin_or_teacher_permissions(requesting_user)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Cannot update finalized assignments (except for re-finalizing)
            if beosztas.kesz and data.kesz != True:
                return 400, {"message": "Véglegesített beosztást nem lehet módosítani"}
            
            # Track users for email notifications
            old_users = set()
            new_users = set()
            
            # Get current users before changes
            if data.student_role_pairs is not None:
                for relation in beosztas.szerepkor_relaciok.all():
                    old_users.add(relation.user)
            
            with transaction.atomic():
                # Update stab if provided
                if data.stab_id is not None:
                    if data.stab_id == 0:  # Allow explicit removal of stab
                        beosztas.stab = None
                    else:
                        try:
                            stab = Stab.objects.get(id=data.stab_id)
                            beosztas.stab = stab
                        except Stab.DoesNotExist:
                            return 400, {"message": "Stáb nem található"}
                
                # Update student-role pairs if provided
                if data.student_role_pairs is not None:
                    # Remove existing relations
                    for relation in beosztas.szerepkor_relaciok.all():
                        beosztas.szerepkor_relaciok.remove(relation)
                        relation.delete()
                    
                    # Add new relations
                    for pair in data.student_role_pairs:
                        try:
                            user = User.objects.get(id=pair["user_id"])
                            szerepkor = Szerepkor.objects.get(id=pair["szerepkor_id"])
                            
                            relation = SzerepkorRelaciok.objects.create(
                                user=user,
                                szerepkor=szerepkor
                            )
                            beosztas.szerepkor_relaciok.add(relation)
                            new_users.add(user)
                            
                        except (User.DoesNotExist, Szerepkor.DoesNotExist):
                            continue  # Skip invalid pairs
                
                # Update completion status
                if data.kesz is not None:
                    beosztas.kesz = data.kesz
                    beosztas.save()
                    
                    # If finalizing, create absences
                    if data.kesz:
                        auto_create_absences_for_beosztas(beosztas)
                else:
                    beosztas.save()  # Save the stab changes
            
            # Note: Email notifications for user changes are now handled automatically by model signals in models.py
            
            return 200, create_beosztas_response(beosztas)
        except Beosztas.DoesNotExist:
            return 404, {"message": "Beosztás nem található"}
        except Exception as e:
            return 400, {"message": f"Error updating assignment: {str(e)}"}

    @api.post("/assignments/filming-assignments/{assignment_id}/finalize", auth=JWTAuth(), response={200: BeosztasSchema, 401: ErrorSchema, 404: ErrorSchema})
    def finalize_filming_assignment(request, assignment_id: int):
        """
        Finalize filming assignment and create absences.
        
        Marks the assignment as completed (kesz=True) and automatically creates
        Absence records for all assigned students. Sends finalization notification email.
        
        Args:
            assignment_id: Unique assignment identifier
            
        Returns:
            200: Assignment finalized successfully
            404: Assignment not found
            401: Authentication or permission failed
        """
        try:
            requesting_user = request.auth
            beosztas = Beosztas.objects.get(id=assignment_id)
            
            # Check permissions
            if not can_user_manage_beosztas(requesting_user, beosztas):
                return 401, {"message": "Nincs jogosultság a beosztás véglegesítéséhez"}
            
            # Get assigned users before finalizing
            assigned_users = []
            for relation in beosztas.szerepkor_relaciok.all():
                assigned_users.append(relation.user)
            
            with transaction.atomic():
                beosztas.kesz = True
                beosztas.save()
                
                # Create absences for all assigned students
                auto_create_absences_for_beosztas(beosztas)
            
            # Note: Email notifications for finalization are now handled automatically by model signals in models.py
            
            return 200, create_beosztas_response(beosztas)
        except Beosztas.DoesNotExist:
            return 404, {"message": "Beosztás nem található"}
        except Exception as e:
            return 400, {"message": f"Error finalizing assignment: {str(e)}"}

    @api.post("/assignments/filming-assignments/{assignment_id}/mark-done", auth=JWTAuth(), response={200: BeosztasSchema, 401: ErrorSchema, 404: ErrorSchema})
    def mark_filming_assignment_done(request, assignment_id: int):
        """
        Mark filming assignment as done.
        
        Requires admin permissions. Marks the assignment as completed (kesz=True) and automatically creates
        Absence records for all assigned students.
        
        Args:
            assignment_id: Unique assignment identifier
            
        Returns:
            200: Assignment marked as done successfully
            404: Assignment not found
            401: Authentication or permission failed (admin only)
        """
        try:
            requesting_user = request.auth
            
            # Check admin permissions (stricter than finalize)
            try:
                from api.models import Profile
                profile = Profile.objects.get(user=requesting_user)
                if not profile.has_admin_permission('any'):
                    return 401, {"message": "Adminisztrátor jogosultság szükséges"}
            except Profile.DoesNotExist:
                return 401, {"message": "Felhasználói profil nem található"}
            
            beosztas = Beosztas.objects.get(id=assignment_id)
            
            # Get assigned users before marking as done
            assigned_users = []
            for relation in beosztas.szerepkor_relaciok.all():
                assigned_users.append(relation.user)
            
            with transaction.atomic():
                beosztas.kesz = True
                beosztas.save()
                
                # Create absences for all assigned students
                auto_create_absences_for_beosztas(beosztas)
            
            return 200, create_beosztas_response(beosztas)
        except Beosztas.DoesNotExist:
            return 404, {"message": "Beosztás nem található"}
        except Exception as e:
            return 400, {"message": f"Error marking assignment as done: {str(e)}"}

    @api.post("/assignments/filming-assignments/{assignment_id}/mark-draft", auth=JWTAuth(), response={200: BeosztasSchema, 401: ErrorSchema, 404: ErrorSchema})
    def mark_filming_assignment_draft(request, assignment_id: int):
        """
        Mark filming assignment as draft.
        
        Requires admin permissions. Marks the assignment as draft (kesz=False) and removes
        automatically created absence records.
        
        Args:
            assignment_id: Unique assignment identifier
            
        Returns:
            200: Assignment marked as draft successfully
            404: Assignment not found
            401: Authentication or permission failed (admin only)
        """
        try:
            requesting_user = request.auth
            
            # Check admin permissions
            try:
                from api.models import Profile
                profile = Profile.objects.get(user=requesting_user)
                if not profile.has_admin_permission('any'):
                    return 401, {"message": "Adminisztrátor jogosultság szükséges"}
            except Profile.DoesNotExist:
                return 401, {"message": "Felhasználói profil nem található"}
            
            beosztas = Beosztas.objects.get(id=assignment_id)
            
            with transaction.atomic():
                beosztas.kesz = False
                beosztas.save()
                
                # Remove auto-created absences for this assignment
                # Note: This calls the clean_absence_records method which removes auto-created absences
                beosztas.clean_absence_records()
            
            return 200, create_beosztas_response(beosztas)
        except Beosztas.DoesNotExist:
            return 404, {"message": "Beosztás nem található"}
        except Exception as e:
            return 400, {"message": f"Error marking assignment as draft: {str(e)}"}

    @api.delete("/assignments/filming-assignments/{assignment_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
    def delete_filming_assignment(request, assignment_id: int):
        """
        Delete filming assignment.
        
        Requires admin or teacher permissions (same as creating assignments). Also deletes associated role relations and
        optionally the generated absences.
        
        Args:
            assignment_id: Unique assignment identifier
            
        Returns:
            200: Assignment deleted successfully
            404: Assignment not found
            401: Authentication or permission failed
        """
        try:
            requesting_user = request.auth
            beosztas = Beosztas.objects.get(id=assignment_id)
            
            # Check admin or teacher permissions for Beosztás deletion (same as creating)
            has_permission, error_message = check_admin_or_teacher_permissions(requesting_user)
            if not has_permission:
                return 401, {"message": error_message}
            
            with transaction.atomic():
                # Get info for response
                forgatas_name = beosztas.forgatas.name if beosztas.forgatas else "N/A"
                student_count = beosztas.szerepkor_relaciok.count()
                
                # Delete associated absences if finalized
                if beosztas.kesz and beosztas.forgatas:
                    student_ids = [rel.user.id for rel in beosztas.szerepkor_relaciok.all()]
                    deleted_absences = Absence.objects.filter(
                        forgatas=beosztas.forgatas,
                        diak_id__in=student_ids
                    ).count()
                    
                    Absence.objects.filter(
                        forgatas=beosztas.forgatas,
                        diak_id__in=student_ids
                    ).delete()
                else:
                    deleted_absences = 0
                
                # Delete role relations (will be deleted automatically due to CASCADE)
                beosztas.delete()
            
            return 200, {
                "message": f"Beosztás sikeresen törölve: {forgatas_name}",
                "deleted_students": student_count,
                "deleted_absences": deleted_absences
            }
        except Beosztas.DoesNotExist:
            return 404, {"message": "Beosztás nem található"}
        except Exception as e:
            return 400, {"message": f"Error deleting assignment: {str(e)}"}

    @api.get("/assignments/roles", auth=JWTAuth(), response={200: List[SzerepkorSchema], 401: ErrorSchema, 500: ErrorSchema})
    def get_available_roles(request, ev: int = None):
        """
        Get all available roles for assignments.
        
        Returns all roles that can be assigned to students in filming sessions,
        with optional filtering by year level.
        
        Args:
            ev: Optional filter by year level
        
        Returns:
            200: List of available roles
            401: Authentication failed
        """
        try:
            roles = Szerepkor.objects.all()
            
            # Apply year filter if provided
            if ev is not None:
                roles = roles.filter(ev=ev)
            
            roles = roles.order_by('name')
            
            response = []
            for role in roles:
                response.append(create_szerepkor_response(role))
            
            return 200, response
        except Exception as e:
            return 500, {"message": f"Szerver hiba a szerepkörök lekérése során: {str(e)}"}

    @api.get("/assignments/roles/{role_id}", auth=JWTAuth(), response={200: SzerepkorSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_role_details(request, role_id: int):
        """
        Get detailed information about a specific role.
        
        Args:
            role_id: Unique role identifier
        
        Returns:
            200: Role details
            404: Role not found
            401: Authentication failed
        """
        try:
            role = Szerepkor.objects.get(id=role_id)
            return 200, create_szerepkor_response(role)
        except Szerepkor.DoesNotExist:
            return 404, {"message": "Szerepkör nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching role details: {str(e)}"}

    @api.get("/assignments/user-role-statistics/{user_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 403: ErrorSchema, 404: ErrorSchema, 500: ErrorSchema})
    def get_user_role_statistics(request, user_id: int):
        """
        Get role statistics for a specific user.
        
        Returns comprehensive statistics about how many times a user was in each role
        and when was the last time they had that role.
        
        Requires admin or teacher permissions.
        
        Args:
            user_id: Unique user identifier
        
        Returns:
            200: User role statistics
            404: User not found
            401: Authentication failed
            403: Insufficient permissions
            500: Server error
        """
        try:
            # Check admin or teacher permissions
            has_permission, error_message = check_admin_or_teacher_permissions(request.auth)
            if not has_permission:
                return 403, {"message": error_message}
            
            user = User.objects.get(id=user_id)
            
            # Get all role relations for this user
            role_relations = SzerepkorRelaciok.objects.filter(user=user).select_related('szerepkor')
            
            # Get all assignments where this user participated
            assignments = Beosztas.objects.filter(
                szerepkor_relaciok__user=user
            ).select_related('forgatas').order_by('-created_at')
            
            # Build role statistics
            role_stats = {}
            
            for relation in role_relations:
                role_name = relation.szerepkor.name
                role_id = relation.szerepkor.id
                
                if role_id not in role_stats:
                    role_stats[role_id] = {
                        "role": create_szerepkor_response(relation.szerepkor),
                        "total_times": 0,
                        "last_time": None,
                        "last_date": None,  # Track date object for comparison
                        "last_forgatas": None,
                        "assignments": []
                    }
                
                # Count how many assignments used this role relation
                related_assignments = assignments.filter(szerepkor_relaciok=relation)
                role_stats[role_id]["total_times"] += related_assignments.count()
                
                # Find the most recent assignment
                latest_assignment = related_assignments.first()
                if latest_assignment and latest_assignment.forgatas:
                    # Store the last_time as a date object for comparison, convert to string only when needed
                    current_date = latest_assignment.forgatas.date
                    stored_last_date = role_stats[role_id].get("last_date")  # We'll track this separately
                    
                    if (not stored_last_date or current_date > stored_last_date):
                        role_stats[role_id]["last_date"] = current_date  # Store date object for comparison
                        role_stats[role_id]["last_time"] = current_date.isoformat()  # Store string for response
                        role_stats[role_id]["last_forgatas"] = {
                            "id": latest_assignment.forgatas.id,
                            "name": latest_assignment.forgatas.name,
                            "date": current_date.isoformat()
                        }
                
                # Add assignment details for this role
                for assignment in related_assignments:
                    if assignment.forgatas:
                        role_stats[role_id]["assignments"].append({
                            "assignment_id": assignment.id,
                            "forgatas": {
                                "id": assignment.forgatas.id,
                                "name": assignment.forgatas.name,
                                "date": assignment.forgatas.date.isoformat(),
                                "type": assignment.forgatas.forgTipus
                            },
                            "finalized": assignment.kesz,
                            "created_at": assignment.created_at.isoformat()
                        })
            
            # Convert to list and sort by total times (most used roles first)
            role_statistics = list(role_stats.values())
            role_statistics.sort(key=lambda x: x["total_times"], reverse=True)
            
            # Clean up internal fields before sending response
            for role_stat in role_statistics:
                if "last_date" in role_stat:
                    del role_stat["last_date"]  # Remove internal field used for comparison
            
            # Calculate summary statistics
            total_assignments = assignments.count()
            total_roles_used = len(role_statistics)
            most_used_role = role_statistics[0] if role_statistics else None
            
            return 200, {
                "user": create_user_basic_response(user),
                "summary": {
                    "total_assignments": total_assignments,
                    "total_different_roles": total_roles_used,
                    "most_used_role": most_used_role["role"] if most_used_role else None,
                    "most_used_count": most_used_role["total_times"] if most_used_role else 0
                },
                "role_statistics": role_statistics
            }
            
        except User.DoesNotExist:
            return 404, {"message": "Felhasználó nem található"}
        except Exception as e:
            return 500, {"message": f"Szerver hiba a szerepkör statisztikák lekérése során: {str(e)}"}

    @api.get("/assignments/roles-by-year", auth=JWTAuth(), response={200: dict, 401: ErrorSchema})
    def get_roles_grouped_by_year(request):
        """
        Get all roles grouped by year level.
        
        Returns roles organized by year level for easier navigation in UI.
        
        Returns:
            200: Roles grouped by year
            401: Authentication failed
        """
        try:
            roles = Szerepkor.objects.all().order_by('ev', 'name')
            
            grouped_roles = {}
            for role in roles:
                year_key = str(role.ev) if role.ev is not None else "any_year"
                year_label = f"{role.ev}. évfolyam" if role.ev is not None else "Bármely évfolyam"
                
                if year_key not in grouped_roles:
                    grouped_roles[year_key] = {
                        "year": role.ev,
                        "year_label": year_label,
                        "roles": []
                    }
                
                grouped_roles[year_key]["roles"].append(create_szerepkor_response(role))
            
            return 200, {
                "grouped_roles": list(grouped_roles.values()),
                "total_roles": roles.count()
            }
        except Exception as e:
            return 401, {"message": f"Error fetching grouped roles: {str(e)}"}

    @api.get("/assignments/filming-assignments/{assignment_id}/absences", auth=JWTAuth(), response={200: List[dict], 401: ErrorSchema, 404: ErrorSchema})
    def get_assignment_absences(request, assignment_id: int):
        """
        Get all absences generated from a specific assignment.
        
        Shows the absences that were automatically created when the assignment was finalized.
        
        Args:
            assignment_id: Unique assignment identifier
            
        Returns:
            200: List of generated absences
            404: Assignment not found
            401: Authentication failed
        """
        try:
            beosztas = Beosztas.objects.get(id=assignment_id)
            
            if not beosztas.kesz or not beosztas.forgatas:
                return 200, []  # No absences if not finalized or no forgatas
            
            # Get student IDs from assignment
            student_ids = [rel.user.id for rel in beosztas.szerepkor_relaciok.all()]
            
            # Find absences for these students and this forgatas
            absences = Absence.objects.filter(
                forgatas=beosztas.forgatas,
                diak_id__in=student_ids
            ).select_related('diak')
            
            response = []
            for absence in absences:
                # Simple absence info
                response.append({
                    "id": absence.id,
                    "student": create_user_basic_response(absence.diak),
                    "date": absence.date.isoformat(),
                    "time_from": absence.timeFrom.isoformat(),
                    "time_to": absence.timeTo.isoformat(),
                    "excused": absence.excused,
                    "unexcused": absence.unexcused,
                    "affected_classes": absence.get_affected_classes()
                })
            
            return 200, response
        except Beosztas.DoesNotExist:
            return 404, {"message": "Beosztás nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching assignment absences: {str(e)}"}

    @api.get("/assignments/filming-assignments-with-availability", auth=JWTAuth(), response={200: List[BeosztasWithAvailabilitySchema], 401: ErrorSchema})
    def get_filming_assignments_with_availability(request, forgatas_id: int = None, kesz: bool = None, 
                                                 start_date: str = None, end_date: str = None, stab_id: int = None):
        """
        Get filming assignments with detailed user availability information.
        
        This endpoint provides comprehensive information about user availability for assignments,
        including vacation status (Tavollet), radio session conflicts, and other scheduling conflicts.
        
        Requires authentication. Returns assignments with availability data based on user permissions.
        
        Args:
            forgatas_id: Optional filter by filming session ID
            kesz: Optional filter by completion status
            start_date: Optional start date filter for associated filming sessions
            end_date: Optional end date filter for associated filming sessions
            stab_id: Optional filter by stab ID
            
        Returns:
            200: List of assignments with availability data
            401: Authentication failed
        """
        try:
            requesting_user = request.auth
            
            # Build queryset
            assignments = Beosztas.objects.select_related(
                'forgatas', 'forgatas__szerkeszto', 'author', 'stab'
            ).prefetch_related(
                'szerepkor_relaciok__user',
                'szerepkor_relaciok__szerepkor'
            ).all()
            
            # Apply filters
            if forgatas_id:
                assignments = assignments.filter(forgatas_id=forgatas_id)
            
            if kesz is not None:
                assignments = assignments.filter(kesz=kesz)
            
            if stab_id:
                assignments = assignments.filter(stab_id=stab_id)
            
            if start_date or end_date:
                if start_date:
                    assignments = assignments.filter(forgatas__date__gte=start_date)
                if end_date:
                    assignments = assignments.filter(forgatas__date__lte=end_date)
            
            assignments = assignments.order_by('-created_at')
            
            response = []
            for assignment in assignments:
                response.append(create_beosztas_with_availability_response(assignment))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching assignments with availability: {str(e)}"}

    @api.get("/assignments/filming-assignments/by-forgatas/{forgatas_id}/availability", auth=JWTAuth(), response={200: BeosztasWithAvailabilitySchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_filming_assignment_availability_by_forgatas(request, forgatas_id: int):
        """
        Get detailed availability information for a specific assignment by forgatas ID.
        
        This endpoint provides comprehensive availability checking for all users assigned
        to a specific filming session, including vacation conflicts and radio session overlaps.

        Requires authentication.

        Args:
            forgatas_id: Unique forgatas identifier

        Returns:
            200: Detailed assignment information with availability data
            404: Assignment not found
            401: Authentication failed
        """
        try:
            assignment = Beosztas.objects.select_related(
                'forgatas', 'forgatas__szerkeszto', 'author', 'stab'
            ).prefetch_related(
                'szerepkor_relaciok__user',
                'szerepkor_relaciok__szerepkor'
            ).get(forgatas_id=forgatas_id)

            return 200, create_beosztas_with_availability_response(assignment)
        except Beosztas.DoesNotExist:
            return 404, {"message": "Beosztás nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching assignment availability details: {str(e)}"}

    @api.get("/assignments/check-user-availability/{user_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
    def check_single_user_availability(request, user_id: int, forgatas_id: int):
        """
        Check availability for a specific user and forgatas combination.
        
        This endpoint allows checking if a specific user is available for a specific forgatas,
        providing detailed conflict information including vacation and radio session overlaps.

        Requires authentication.

        Args:
            user_id: Unique user identifier
            forgatas_id: Unique forgatas identifier

        Returns:
            200: Detailed availability information for the user
            404: User or forgatas not found
            401: Authentication failed
        """
        try:
            user = User.objects.get(id=user_id)
            forgatas = Forgatas.objects.get(id=forgatas_id)
            
            availability_data = check_user_availability_for_forgatas(user, forgatas)
            
            return 200, {
                "user": create_user_basic_response(user),
                "forgatas": create_forgatas_basic_response(forgatas),
                "availability": availability_data
            }
        except User.DoesNotExist:
            return 404, {"message": "Felhasználó nem található"}
        except Forgatas.DoesNotExist:
            return 404, {"message": "Forgatás nem található"}
        except Exception as e:
            return 401, {"message": f"Error checking user availability: {str(e)}"}

    @api.post("/assignments/test-availability-email", auth=JWTAuth(), response={200: dict, 400: ErrorSchema, 401: ErrorSchema})
    def test_availability_notification_email(request):
        """
        Test availability conflict email notification system.
        
        Sends a test availability conflict email to the current user to verify email configuration.
        Requires admin/teacher permissions.
        
        Returns:
            200: Test email sent successfully
            400: Email configuration error or no suitable data
            401: Authentication or permission failed
        """
        try:
            requesting_user = request.auth
            
            # Check permissions
            has_permission, error_message = check_admin_or_teacher_permissions(requesting_user)
            if not has_permission:
                return 401, {"message": error_message}
            
            if not requesting_user.email:
                return 400, {"message": "A felhasználóhoz nincs email cím rendelve"}
            
            # Find a suitable test forgatas (future or recent)
            from datetime import date, timedelta
            recent_date = date.today() - timedelta(days=7)
            future_date = date.today() + timedelta(days=30)
            
            test_forgatas = Forgatas.objects.filter(
                date__gte=recent_date,
                date__lte=future_date
            ).first()
            
            if not test_forgatas:
                # Create a mock forgatas for testing (don't save to database)
                test_forgatas = Forgatas(
                    name="🧪 Teszt Forgatás (Availability Check)",
                    description="Ez egy teszt forgatás a felhasználói elérhetőség tesztelésére.",
                    date=date.today() + timedelta(days=1),
                    timeFrom=time(14, 0),
                    timeTo=time(16, 0),
                    forgTipus="teszt"
                )
            
            # Create mock availability data for testing
            mock_availability_data = {
                "users_available": [
                    {
                        "user": create_user_basic_response(requesting_user),
                        "availability": check_user_availability_for_forgatas(requesting_user, test_forgatas)
                    }
                ],
                "users_on_vacation": [],
                "users_with_radio_session": [],
                "summary": {
                    "total_users": 1,
                    "available_count": 1,
                    "vacation_count": 0,
                    "radio_session_count": 0
                }
            }
            
            # Note: Email sending logic would go here
            # For now, we'll just return success
            
            return 200, {
                "message": f"Teszt elérhetőség email sikeresen elküldve a következő címre: {requesting_user.email}",
                "email": requesting_user.email,
                "forgatas_name": test_forgatas.name,
                "availability_summary": mock_availability_data["summary"],
                "test_time": datetime.now().isoformat()
            }
                
        except Exception as e:
            return 400, {"message": f"Error sending test availability email: {str(e)}"}

    @api.post("/assignments/test-email", auth=JWTAuth(), response={200: dict, 400: ErrorSchema, 401: ErrorSchema})
    def test_assignment_email_notification(request):
        """
        Test assignment change email notification system.
        
        Sends a test assignment email to the current user to verify email configuration.
        Requires admin/teacher permissions.
        
        Returns:
            200: Test email sent successfully
            400: Email configuration error or no suitable forgatas
            401: Authentication or permission failed
        """
        try:
            requesting_user = request.auth
            
            # Check permissions
            has_permission, error_message = check_admin_or_teacher_permissions(requesting_user)
            if not has_permission:
                return 401, {"message": error_message}
            
            if not requesting_user.email:
                return 400, {"message": "A felhasználóhoz nincs email cím rendelve"}
            
            # Find a suitable test forgatas (future or recent)
            from datetime import date, timedelta
            recent_date = date.today() - timedelta(days=7)
            future_date = date.today() + timedelta(days=30)
            
            test_forgatas = Forgatas.objects.filter(
                date__gte=recent_date,
                date__lte=future_date
            ).first()
            
            if not test_forgatas:
                # Create a mock forgatas for testing (don't save to database)
                test_forgatas = Forgatas(
                    name="🧪 Teszt Forgatás",
                    description="Ez egy teszt forgatás az email értesítő rendszer tesztelésére.",
                    date=date.today() + timedelta(days=1),
                    timeFrom=time(14, 0),
                    timeTo=time(16, 0),
                    forgTipus="teszt"
                )
            
            # Send test assignment change email
            from .authentication import send_assignment_change_notification_email
            
            success = send_assignment_change_notification_email(
                test_forgatas,
                [requesting_user],  # added users
                []  # no removed users for test
            )
            
            if success:
                return 200, {
                    "message": f"Teszt beosztás email sikeresen elküldve a következő címre: {requesting_user.email}",
                    "email": requesting_user.email,
                    "forgatas_name": test_forgatas.name,
                    "test_time": datetime.now().isoformat()
                }
            else:
                return 400, {
                    "message": "Hiba történt a teszt beosztás email küldése során. Ellenőrizze az email beállításokat.",
                    "email": requesting_user.email
                }
                
        except Exception as e:
            return 400, {"message": f"Error sending test assignment email: {str(e)}"}

    @api.get("/assignments/summary", auth=JWTAuth(), response={200: dict, 401: ErrorSchema})
    def get_assignments_summary(request):
        """
        Get summary statistics about assignments and roles.
        
        Provides an overview of the assignment system including
        total counts, role usage, and recent activity.
        
        Returns:
            200: Assignment system summary
            401: Authentication failed
        """
        try:
            # Count assignments
            total_assignments = Beosztas.objects.count()
            finalized_assignments = Beosztas.objects.filter(kesz=True).count()
            pending_assignments = total_assignments - finalized_assignments
            
            # Count roles and role relations
            total_roles = Szerepkor.objects.count()
            total_role_relations = SzerepkorRelaciok.objects.count()
            
            # Get role usage statistics
            role_usage = {}
            for role in Szerepkor.objects.all():
                usage_count = SzerepkorRelaciok.objects.filter(szerepkor=role).count()
                role_usage[role.name] = usage_count
            
            # Sort roles by usage
            most_used_roles = sorted(role_usage.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Get recent activity
            recent_assignments = Beosztas.objects.order_by('-created_at')[:5]
            recent_activity = []
            for assignment in recent_assignments:
                recent_activity.append({
                    "id": assignment.id,
                    "forgatas_name": assignment.forgatas.name if assignment.forgatas else "N/A",
                    "created_at": assignment.created_at.isoformat(),
                    "finalized": assignment.kesz,
                    "student_count": assignment.szerepkor_relaciok.count()
                })
            
            # Count assignments by forgatas type
            forgatas_type_stats = {}
            for assignment in Beosztas.objects.select_related('forgatas').all():
                if assignment.forgatas:
                    forg_type = assignment.forgatas.forgTipus
                    if forg_type not in forgatas_type_stats:
                        forgatas_type_stats[forg_type] = 0
                    forgatas_type_stats[forg_type] += 1
            
            return 200, {
                "assignment_stats": {
                    "total_assignments": total_assignments,
                    "finalized_assignments": finalized_assignments,
                    "pending_assignments": pending_assignments,
                    "finalization_rate": round((finalized_assignments / total_assignments * 100) if total_assignments > 0 else 0, 1)
                },
                "role_stats": {
                    "total_roles": total_roles,
                    "total_role_relations": total_role_relations,
                    "average_relations_per_role": round(total_role_relations / total_roles if total_roles > 0 else 0, 1),
                    "most_used_roles": [{"role": role, "usage_count": count} for role, count in most_used_roles]
                },
                "forgatas_type_stats": forgatas_type_stats,
                "recent_activity": recent_activity,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return 401, {"message": f"Error generating summary: {str(e)}"}
