"""
Absence Management API Module (Hiányzás kezelés)

Ez a modul az iskolai hiányzások kezelését biztosítja, amelyek automatikusan 
generálódnak forgatások alapján és az osztályfőnökök által kezelhetők.

FONTOS MEGKÜLÖNBÖZTETÉS:
- TÁVOLLÉT (Tavollet): Előre bejelentett távollét, amit a médiatanároknak jeleznek
- HIÁNYZÁS (Absence): Forgatások alapján automatikusan generált hiányzás, amit az osztályfőnökök kezelnek

Public API Overview:
==================

A Hiányzás API az osztályfőnökök számára biztosítja az iskolai hiányzások kezelését,
amelyek automatikusan létrejönnek, amikor egy diák forgatásra van beosztva.

Base URL: /api/absences/

Protected Endpoints (JWT Token Required):

Hiányzások (osztályfőnökök számára):
- GET  /school-absences         - Lista hiányzásokról (csak osztályfőnökök)
- GET  /school-absences/{id}    - Konkrét hiányzás részletei
- PUT  /school-absences/{id}    - Hiányzás státusz frissítése (igazolt/igazolatlan)
- GET  /school-absences/class/{class_id}  - Osztály hiányzásai

Hiányzás rendszer áttekintés:
===========================

A hiányzás rendszer automatikusan kezeli a forgatások miatti hiányzásokat:

1. **Automatikus generálás**: Minden forgatás beosztáskor automatikusan létrejön
2. **Tanóra érintettség**: Kiszámolja, mely tanórákba lóg bele a forgatás
3. **Osztályfőnöki kezelés**: Az osztályfőnökök igazolják/igazolatlanná teszik
4. **Státusz követés**: Nyomon követi az igazolások állapotát

Érintett tanórák számítása:
=========================

A rendszer kiszámolja, mely tanórák érintettek a forgatás ideje alatt:

Csengetési rend:
- 0. óra: 7:30-8:15
- 1. óra: 8:25-9:10
- 2. óra: 9:20-10:05
- 3. óra: 10:20-11:05
- 4. óra: 11:15-12:00
- 5. óra: 12:20-13:05
- 6. óra: 13:25-14:10
- 7. óra: 14:20-15:05
- 8. óra: 15:15-16:00

Adatstruktúra:
=============

Hiányzás (Absence):
- id: Egyedi azonosító
- diak: Diák (User)
- forgatas: Kapcsolódó forgatás
- date: Hiányzás dátuma
- time_from: Kezdési idő
- time_to: Befejezési idő
- excused: Igazolt hiányzás
- unexcused: Igazolatlan hiányzás
- affected_classes: Érintett tanórák listája

Jogosultságok:
=============

- Megtekintés: Osztályfőnökök (saját osztályuk)
- Igazolás: Osztályfőnökök (saját osztályuk hiányzásai)
- Létrehozás: Automatikus (forgatás beosztáskor)

Hiányzás státuszok:
==================

- Nincs döntés: sem igazolt, sem igazolatlan
- Igazolt: excused = True, unexcused = False  
- Igazolatlan: excused = False, unexcused = True

Integrációs pontok:
==================

- Forgatás rendszer: automatikus hiányzás létrehozás
- Felhasználói rendszer: diák és osztályfőnök kapcsolatok
- Akadémiai rendszer: tanév és osztály koordináció
"""

from ninja import Schema
from django.contrib.auth.models import User
from django.db.models import Q
from api.models import Absence, Forgatas, Osztaly, Profile
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

class ForgatSchema(Schema):
    """Basic forgatas information schema."""
    id: int
    name: str
    date: str
    time_from: str
    time_to: str
    type: str

class OsztalySchema(Schema):
    """Basic osztaly information schema."""
    id: int
    name: str
    szekcio: str
    start_year: int

class AbsenceSchema(Schema):
    """Response schema for absence data."""
    id: int
    diak: UserBasicSchema
    forgatas: ForgatSchema
    date: str
    time_from: str
    time_to: str
    excused: bool
    unexcused: bool
    status: str
    affected_classes: List[int]
    affected_classes_with_student_time: List[int]
    osztaly: Optional[OsztalySchema] = None
    student_extra_time_before: int
    student_extra_time_after: int
    student_edited: bool
    student_edit_timestamp: Optional[str] = None
    student_edit_note: Optional[str] = None
    effective_time_from: str
    effective_time_to: str

class AbsenceUpdateSchema(Schema):
    """Request schema for updating absence status."""
    excused: Optional[bool] = None
    unexcused: Optional[bool] = None

class AbsenceBulkUpdateSchema(Schema):
    """Request schema for bulk updating multiple absences."""
    absence_ids: List[int]
    excused: Optional[bool] = None
    unexcused: Optional[bool] = None

class StudentAbsenceUpdateSchema(Schema):
    """Request schema for student updating their own absence extra time."""
    extra_time_before: Optional[int] = None
    extra_time_after: Optional[int] = None
    note: Optional[str] = None

# ============================================================================
# Utility Functions
# ============================================================================

def create_user_basic_response(user: User) -> dict:
    """Create basic user information response."""
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.get_full_name()
    }

def create_forgatas_basic_response(forgatas: Forgatas) -> dict:
    """Create basic forgatas information response."""
    return {
        "id": forgatas.id,
        "name": forgatas.name,
        "date": forgatas.date.isoformat(),
        "time_from": forgatas.timeFrom.isoformat(),
        "time_to": forgatas.timeTo.isoformat(),
        "type": forgatas.forgTipus
    }

def create_osztaly_response(osztaly: Osztaly) -> dict:
    """Create osztaly information response."""
    return {
        "id": osztaly.id,
        "name": str(osztaly),
        "szekcio": osztaly.szekcio,
        "start_year": osztaly.startYear
    }

def create_absence_response(absence: Absence) -> dict:
    """Create standardized absence response dictionary."""
    # Determine status
    if absence.excused and not absence.unexcused:
        status = "igazolt"
    elif absence.unexcused and not absence.excused:
        status = "igazolatlan"
    else:
        status = "nincs_dontes"
    
    # Get student's osztaly
    osztaly_data = None
    try:
        profile = Profile.objects.get(user=absence.diak)
        if profile.osztaly:
            osztaly_data = create_osztaly_response(profile.osztaly)
    except Profile.DoesNotExist:
        pass
    
    return {
        "id": absence.id,
        "diak": create_user_basic_response(absence.diak),
        "forgatas": create_forgatas_basic_response(absence.forgatas),
        "date": absence.date.isoformat(),
        "time_from": absence.timeFrom.isoformat(),
        "time_to": absence.timeTo.isoformat(),
        "excused": absence.excused,
        "unexcused": absence.unexcused,
        "status": status,
        "affected_classes": absence.get_affected_classes(),
        "affected_classes_with_student_time": absence.get_affected_classes_with_student_time(),
        "osztaly": osztaly_data,
        "student_extra_time_before": absence.student_extra_time_before,
        "student_extra_time_after": absence.student_extra_time_after,
        "student_edited": absence.student_edited,
        "student_edit_timestamp": absence.student_edit_timestamp.isoformat() if absence.student_edit_timestamp else None,
        "student_edit_note": absence.student_edit_note,
        "effective_time_from": absence.get_effective_time_from().isoformat(),
        "effective_time_to": absence.get_effective_time_to().isoformat()
    }

def check_class_teacher_permissions(user: User, target_absence: Absence = None) -> tuple[bool, str]:
    """
    Check if user is a class teacher (osztályfőnök) and can manage absences.
    If target_absence is provided, also checks if they can manage that specific student's absence.
    """
    try:
        profile = Profile.objects.get(user=user)
        
        # Check if user is marked as osztályfőnök
        if not profile.is_osztaly_fonok:
            return False, "Osztályfőnök jogosultság szükséges"
        
        # If specific absence is provided, check if they can manage this student
        if target_absence:
            try:
                student_profile = Profile.objects.get(user=target_absence.diak)
                if not student_profile.osztaly:
                    return False, "A diáknak nincs hozzárendelt osztálya"
                
                # Check if current user is teacher of student's class
                if not student_profile.osztaly.is_user_osztaly_fonok(user):
                    return False, "Csak a saját osztály hiányzásait kezelheti"
                    
            except Profile.DoesNotExist:
                return False, "Diák profil nem található"
        
        return True, ""
    except Profile.DoesNotExist:
        return False, "Felhasználói profil nem található"

def get_managed_classes(user: User) -> List[Osztaly]:
    """Get all classes managed by the user as osztályfőnök."""
    try:
        profile = Profile.objects.get(user=user)
        if profile.is_osztaly_fonok:
            return profile.get_owned_osztalyok()
        return []
    except Profile.DoesNotExist:
        return []

def auto_create_absences_for_forgatas(forgatas: Forgatas, student_ids: List[int]):
    """
    Automatically create absence records for students assigned to a forgatas.
    This should be called when students are assigned to a filming session.
    """
    for student_id in student_ids:
        try:
            student = User.objects.get(id=student_id)
            
            # Check if absence already exists for this student and forgatas
            existing = Absence.objects.filter(
                diak=student,
                forgatas=forgatas
            ).exists()
            
            if not existing:
                Absence.objects.create(
                    diak=student,
                    forgatas=forgatas,
                    date=forgatas.date,
                    timeFrom=forgatas.timeFrom,
                    timeTo=forgatas.timeTo,
                    excused=False,
                    unexcused=False
                )
        except User.DoesNotExist:
            continue

# ============================================================================
# API Endpoints
# ============================================================================

def register_absence_management_endpoints(api):
    """Register all absence management endpoints with the API router."""
    
    @api.get("/school-absences", auth=JWTAuth(), response={200: List[AbsenceSchema], 401: ErrorSchema})
    def get_school_absences(request, class_id: int = None, student_id: int = None, 
                           start_date: str = None, end_date: str = None, 
                           status: str = None):
        """
        Get school absences for class teachers.
        
        Class teachers can only see absences from their own classes.
        
        Args:
            class_id: Optional filter by class ID
            student_id: Optional filter by student ID  
            start_date: Optional start date filter (ISO format)
            end_date: Optional end date filter (ISO format)
            status: Optional status filter (igazolt/igazolatlan/nincs_dontes)
            
        Returns:
            200: List of absences
            401: Authentication or permission failed
        """
        try:
            requesting_user = request.auth
            
            # Check if user is osztályfőnök
            has_permission, error_message = check_class_teacher_permissions(requesting_user)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Get classes managed by this teacher
            managed_classes = get_managed_classes(requesting_user)
            if not managed_classes:
                return 200, []  # No classes managed, return empty list
            
            # Build queryset - only absences from managed classes
            managed_class_ids = [cls.id for cls in managed_classes]
            
            # Get students from managed classes
            student_profiles = Profile.objects.filter(
                osztaly_id__in=managed_class_ids
            ).select_related('user')
            managed_student_ids = [p.user.id for p in student_profiles]
            
            absences = Absence.objects.filter(
                diak_id__in=managed_student_ids
            ).select_related('diak', 'forgatas')
            
            # Apply filters
            if class_id and class_id in managed_class_ids:
                # Filter by specific class
                class_student_profiles = Profile.objects.filter(
                    osztaly_id=class_id
                ).select_related('user')
                class_student_ids = [p.user.id for p in class_student_profiles]
                absences = absences.filter(diak_id__in=class_student_ids)
            
            if student_id:
                absences = absences.filter(diak_id=student_id)
            
            if start_date:
                absences = absences.filter(date__gte=start_date)
            
            if end_date:
                absences = absences.filter(date__lte=end_date)
            
            if status:
                if status == "igazolt":
                    absences = absences.filter(excused=True, unexcused=False)
                elif status == "igazolatlan":
                    absences = absences.filter(excused=False, unexcused=True)
                elif status == "nincs_dontes":
                    absences = absences.filter(excused=False, unexcused=False)
            
            absences = absences.order_by('-date', 'diak__last_name', 'diak__first_name')
            
            response = []
            for absence in absences:
                response.append(create_absence_response(absence))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching school absences: {str(e)}"}

    @api.get("/school-absences/{absence_id}", auth=JWTAuth(), response={200: AbsenceSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_school_absence_details(request, absence_id: int):
        """
        Get detailed information about a specific school absence.
        
        Class teachers can only view absences from their own classes.
        
        Args:
            absence_id: Unique absence identifier
            
        Returns:
            200: Detailed absence information
            404: Absence not found or no permission
            401: Authentication failed
        """
        try:
            requesting_user = request.auth
            absence = Absence.objects.select_related('diak', 'forgatas').get(id=absence_id)
            
            # Check if user can manage this absence
            has_permission, error_message = check_class_teacher_permissions(requesting_user, absence)
            if not has_permission:
                return 404, {"message": "Hiányzás nem található vagy nincs jogosultság megtekintéséhez"}
            
            return 200, create_absence_response(absence)
        except Absence.DoesNotExist:
            return 404, {"message": "Hiányzás nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching absence details: {str(e)}"}

    @api.put("/school-absences/{absence_id}", auth=JWTAuth(), response={200: AbsenceSchema, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
    def update_school_absence(request, absence_id: int, data: AbsenceUpdateSchema):
        """
        Update school absence status (excuse/unexcuse).
        
        Class teachers can only update absences from their own classes.
        
        Args:
            absence_id: Unique absence identifier
            data: Absence update data (excused/unexcused status)
            
        Returns:
            200: Absence updated successfully
            404: Absence not found
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            requesting_user = request.auth
            absence = Absence.objects.get(id=absence_id)
            
            # Check permissions
            has_permission, error_message = check_class_teacher_permissions(requesting_user, absence)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Update status - ensure mutual exclusivity
            if data.excused is not None and data.unexcused is not None:
                # Both provided - ensure they're not both True
                if data.excused and data.unexcused:
                    return 400, {"message": "Hiányzás nem lehet egyszerre igazolt és igazolatlan"}
                absence.excused = data.excused
                absence.unexcused = data.unexcused
            elif data.excused is not None:
                absence.excused = data.excused
                if data.excused:
                    absence.unexcused = False  # If setting to excused, clear unexcused
            elif data.unexcused is not None:
                absence.unexcused = data.unexcused
                if data.unexcused:
                    absence.excused = False  # If setting to unexcused, clear excused
            
            absence.save()
            
            return 200, create_absence_response(absence)
        except Absence.DoesNotExist:
            return 404, {"message": "Hiányzás nem található"}
        except Exception as e:
            return 400, {"message": f"Error updating absence: {str(e)}"}

    @api.put("/school-absences/bulk-update", auth=JWTAuth(), response={200: dict, 400: ErrorSchema, 401: ErrorSchema})
    def bulk_update_school_absences(request, data: AbsenceBulkUpdateSchema):
        """
        Bulk update multiple school absences.
        
        Class teachers can only update absences from their own classes.
        
        Args:
            data: Bulk update data with absence IDs and new status
            
        Returns:
            200: Bulk update completed
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            requesting_user = request.auth
            
            # Check if user is osztályfőnök
            has_permission, error_message = check_class_teacher_permissions(requesting_user)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Get all absences to update
            absences = Absence.objects.filter(id__in=data.absence_ids)
            
            # Check permissions for each absence
            for absence in absences:
                has_permission, error_message = check_class_teacher_permissions(requesting_user, absence)
                if not has_permission:
                    return 401, {"message": f"Nincs jogosultság a hiányzás kezeléséhez: {absence.diak.get_full_name()}"} 
            
            # Validate status update
            if data.excused is not None and data.unexcused is not None:
                if data.excused and data.unexcused:
                    return 400, {"message": "Hiányzás nem lehet egyszerre igazolt és igazolatlan"}
            
            # Perform bulk update
            updated_count = 0
            for absence in absences:
                if data.excused is not None and data.unexcused is not None:
                    absence.excused = data.excused
                    absence.unexcused = data.unexcused
                elif data.excused is not None:
                    absence.excused = data.excused
                    if data.excused:
                        absence.unexcused = False
                elif data.unexcused is not None:
                    absence.unexcused = data.unexcused
                    if data.unexcused:
                        absence.excused = False
                
                absence.save()
                updated_count += 1
            
            return 200, {
                "message": f"{updated_count} hiányzás sikeresen frissítve",
                "updated_count": updated_count,
                "total_requested": len(data.absence_ids)
            }
            
        except Exception as e:
            return 400, {"message": f"Error in bulk update: {str(e)}"}

    @api.get("/school-absences/class/{class_id}", auth=JWTAuth(), response={200: List[AbsenceSchema], 401: ErrorSchema, 404: ErrorSchema})
    def get_class_absences(request, class_id: int, start_date: str = None, end_date: str = None):
        """
        Get all absences for a specific class.
        
        Class teachers can only view absences from their own classes.
        
        Args:
            class_id: Class ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            200: List of class absences
            404: Class not found or no permission
            401: Authentication failed
        """
        try:
            requesting_user = request.auth
            
            # Check if user manages this class
            managed_classes = get_managed_classes(requesting_user)
            if not any(cls.id == class_id for cls in managed_classes):
                return 404, {"message": "Osztály nem található vagy nincs jogosultság"}
            
            # Get students from this class
            student_profiles = Profile.objects.filter(
                osztaly_id=class_id
            ).select_related('user')
            student_ids = [p.user.id for p in student_profiles]
            
            absences = Absence.objects.filter(
                diak_id__in=student_ids
            ).select_related('diak', 'forgatas')
            
            # Apply date filters
            if start_date:
                absences = absences.filter(date__gte=start_date)
            if end_date:
                absences = absences.filter(date__lte=end_date)
            
            absences = absences.order_by('-date', 'diak__last_name', 'diak__first_name')
            
            response = []
            for absence in absences:
                response.append(create_absence_response(absence))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching class absences: {str(e)}"}

    @api.get("/school-absences/stats/class/{class_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
    def get_class_absence_statistics(request, class_id: int, start_date: str = None, end_date: str = None):
        """
        Get absence statistics for a class.
        
        Args:
            class_id: Class ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            200: Class absence statistics
            404: Class not found or no permission
            401: Authentication failed
        """
        try:
            requesting_user = request.auth
            
            # Check if user manages this class
            managed_classes = get_managed_classes(requesting_user)
            if not any(cls.id == class_id for cls in managed_classes):
                return 404, {"message": "Osztály nem található vagy nincs jogosultság"}
            
            # Get students from this class
            student_profiles = Profile.objects.filter(
                osztaly_id=class_id
            ).select_related('user')
            student_ids = [p.user.id for p in student_profiles]
            
            absences = Absence.objects.filter(diak_id__in=student_ids)
            
            # Apply date filters
            if start_date:
                absences = absences.filter(date__gte=start_date)
            if end_date:
                absences = absences.filter(date__lte=end_date)
            
            # Calculate statistics
            total_absences = absences.count()
            excused_absences = absences.filter(excused=True, unexcused=False).count()
            unexcused_absences = absences.filter(excused=False, unexcused=True).count()
            pending_absences = absences.filter(excused=False, unexcused=False).count()
            
            # Student-level statistics
            student_stats = []
            for profile in student_profiles:
                student_absences = absences.filter(diak=profile.user)
                student_total = student_absences.count()
                student_excused = student_absences.filter(excused=True, unexcused=False).count()
                student_unexcused = student_absences.filter(excused=False, unexcused=True).count()
                student_pending = student_absences.filter(excused=False, unexcused=False).count()
                
                if student_total > 0:  # Only include students with absences
                    student_stats.append({
                        "student": create_user_basic_response(profile.user),
                        "total_absences": student_total,
                        "excused": student_excused,
                        "unexcused": student_unexcused,
                        "pending": student_pending
                    })
            
            return 200, {
                "class_id": class_id,
                "total_students": len(student_profiles),
                "period": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "summary": {
                    "total_absences": total_absences,
                    "excused": excused_absences,
                    "unexcused": unexcused_absences,
                    "pending": pending_absences
                },
                "students": student_stats
            }
            
        except Exception as e:
            return 401, {"message": f"Error fetching absence statistics: {str(e)}"}

    # ============================================================================
    # Student Hiányzás Management Endpoints
    # ============================================================================

    @api.get("/my-absences", auth=JWTAuth(), response={200: List[AbsenceSchema], 401: ErrorSchema})
    def get_my_absences(request, start_date: str = None, end_date: str = None):
        """
        Get current user's own absences (hiányzások).
        
        Students can view their own absence records and see if they have submitted extra time.
        
        Args:
            start_date: Optional start date filter (ISO format)
            end_date: Optional end date filter (ISO format)
            
        Returns:
            200: List of student's absences
            401: Authentication failed
        """
        try:
            requesting_user = request.auth
            
            # Get absences for the current student
            absences = Absence.objects.filter(
                diak=requesting_user
            ).select_related('forgatas')
            
            # Apply date filters
            if start_date:
                absences = absences.filter(date__gte=start_date)
            if end_date:
                absences = absences.filter(date__lte=end_date)
            
            absences = absences.order_by('-date', 'timeFrom')
            
            response = []
            for absence in absences:
                response.append(create_absence_response(absence))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching student absences: {str(e)}"}

    @api.get("/my-absences/{absence_id}", auth=JWTAuth(), response={200: AbsenceSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_my_absence_details(request, absence_id: int):
        """
        Get detailed information about student's own absence.
        
        Students can only view their own absence records.
        
        Args:
            absence_id: Unique absence identifier
            
        Returns:
            200: Detailed absence information
            404: Absence not found or not owned by student
            401: Authentication failed
        """
        try:
            requesting_user = request.auth
            absence = Absence.objects.select_related('forgatas').get(
                id=absence_id, 
                diak=requesting_user
            )
            
            return 200, create_absence_response(absence)
        except Absence.DoesNotExist:
            return 404, {"message": "Hiányzás nem található vagy nem az Öné"}
        except Exception as e:
            return 401, {"message": f"Error fetching absence details: {str(e)}"}

    @api.put("/my-absences/{absence_id}/extra-time", auth=JWTAuth(), response={200: AbsenceSchema, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
    def update_my_absence_extra_time(request, absence_id: int, data: StudentAbsenceUpdateSchema):
        """
        Update extra time for student's own absence.
        
        Students can add extra time before or after their forgatás and provide a note explaining why.
        This allows them to indicate if they need to leave earlier or return later than the scheduled time.
        
        Args:
            absence_id: Unique absence identifier
            data: Extra time update data
            
        Returns:
            200: Absence updated successfully
            404: Absence not found or not owned by student
            400: Invalid data
            401: Authentication failed
        """
        try:
            requesting_user = request.auth
            absence = Absence.objects.select_related('forgatas').get(
                id=absence_id,
                diak=requesting_user
            )
            
            # Validate extra time values
            if data.extra_time_before is not None:
                if data.extra_time_before < 0 or data.extra_time_before > 480:  # Max 8 hours
                    return 400, {"message": "Az extra idő előtte 0 és 480 perc között lehet"}
                absence.student_extra_time_before = data.extra_time_before
            
            if data.extra_time_after is not None:
                if data.extra_time_after < 0 or data.extra_time_after > 480:  # Max 8 hours
                    return 400, {"message": "Az extra idő utána 0 és 480 perc között lehet"}
                absence.student_extra_time_after = data.extra_time_after
            
            if data.note is not None:
                if len(data.note) > 500:
                    return 400, {"message": "A megjegyzés maximum 500 karakter lehet"}
                absence.student_edit_note = data.note
            
            # Mark as student edited and set timestamp
            absence.student_edited = True
            absence.student_edit_timestamp = datetime.now()
            
            absence.save()
            
            return 200, create_absence_response(absence)
        except Absence.DoesNotExist:
            return 404, {"message": "Hiányzás nem található vagy nem az Öné"}
        except Exception as e:
            return 400, {"message": f"Error updating absence extra time: {str(e)}"}

    @api.delete("/my-absences/{absence_id}/extra-time", auth=JWTAuth(), response={200: AbsenceSchema, 401: ErrorSchema, 404: ErrorSchema})
    def reset_my_absence_extra_time(request, absence_id: int):
        """
        Reset extra time for student's own absence back to default (0 minutes before/after).
        
        Students can clear their previously submitted extra time.
        
        Args:
            absence_id: Unique absence identifier
            
        Returns:
            200: Extra time reset successfully
            404: Absence not found or not owned by student
            401: Authentication failed
        """
        try:
            requesting_user = request.auth
            absence = Absence.objects.get(
                id=absence_id,
                diak=requesting_user
            )
            
            # Reset student extra time fields
            absence.student_extra_time_before = 0
            absence.student_extra_time_after = 0
            absence.student_edit_note = None
            
            # Check if any student edits remain (if both are 0 and no note, mark as not edited)
            if absence.student_extra_time_before == 0 and absence.student_extra_time_after == 0 and not absence.student_edit_note:
                absence.student_edited = False
                absence.student_edit_timestamp = None
            else:
                # Still has some edits, update timestamp
                absence.student_edit_timestamp = datetime.now()
            
            absence.save()
            
            return 200, create_absence_response(absence)
        except Absence.DoesNotExist:
            return 404, {"message": "Hiányzás nem található vagy nem az Öné"}
        except Exception as e:
            return 401, {"message": f"Error resetting absence extra time: {str(e)}"}
    
    @api.get("/my-absences/upcoming", auth=JWTAuth(), response={200: List[AbsenceSchema], 401: ErrorSchema})
    def get_my_upcoming_absences(request):
        """
        Get student's upcoming absences (hiányzások) that haven't occurred yet.
        
        Students can view and potentially edit their future absences.
        
        Returns:
            200: List of upcoming absences
            401: Authentication failed
        """
        try:
            requesting_user = request.auth
            today = date.today()
            
            # Get future absences for the current student
            absences = Absence.objects.filter(
                diak=requesting_user,
                date__gte=today
            ).select_related('forgatas').order_by('date', 'timeFrom')
            
            response = []
            for absence in absences:
                response.append(create_absence_response(absence))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching upcoming absences: {str(e)}"}

    @api.get("/school-absences/student-edits", auth=JWTAuth(), response={200: List[AbsenceSchema], 401: ErrorSchema})
    def get_student_edited_absences(request, class_id: int = None, start_date: str = None, end_date: str = None):
        """
        Get absences that have been edited by students (for class teachers).
        
        Class teachers can see which students have submitted extra time or notes for their absences.
        This helps teachers review and validate student submissions.
        
        Args:
            class_id: Optional filter by class ID
            start_date: Optional start date filter (ISO format)
            end_date: Optional end date filter (ISO format)
            
        Returns:
            200: List of student-edited absences
            401: Authentication or permission failed
        """
        try:
            requesting_user = request.auth
            
            # Check if user is osztályfőnök
            has_permission, error_message = check_class_teacher_permissions(requesting_user)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Get classes managed by this teacher
            managed_classes = get_managed_classes(requesting_user)
            if not managed_classes:
                return 200, []  # No classes managed, return empty list
            
            # Build queryset - only student-edited absences from managed classes
            managed_class_ids = [cls.id for cls in managed_classes]
            
            # Get students from managed classes
            student_profiles = Profile.objects.filter(
                osztaly_id__in=managed_class_ids
            ).select_related('user')
            managed_student_ids = [p.user.id for p in student_profiles]
            
            # Filter for student-edited absences only
            absences = Absence.objects.filter(
                diak_id__in=managed_student_ids,
                student_edited=True
            ).select_related('diak', 'forgatas')
            
            # Apply filters
            if class_id and class_id in managed_class_ids:
                # Filter by specific class
                class_student_profiles = Profile.objects.filter(
                    osztaly_id=class_id
                ).select_related('user')
                class_student_ids = [p.user.id for p in class_student_profiles]
                absences = absences.filter(diak_id__in=class_student_ids)
            
            if start_date:
                absences = absences.filter(date__gte=start_date)
            
            if end_date:
                absences = absences.filter(date__lte=end_date)
            
            # Order by edit timestamp (most recent edits first)
            absences = absences.order_by('-student_edit_timestamp', 'date', 'diak__last_name')
            
            response = []
            for absence in absences:
                response.append(create_absence_response(absence))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching student-edited absences: {str(e)}"}

    @api.get("/school-absences/class/{class_id}/student-edits", auth=JWTAuth(), response={200: List[AbsenceSchema], 401: ErrorSchema, 404: ErrorSchema})
    def get_class_student_edited_absences(request, class_id: int, start_date: str = None, end_date: str = None):
        """
        Get student-edited absences for a specific class.
        
        Class teachers can see which students in their class have submitted extra time.
        
        Args:
            class_id: Class ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            200: List of student-edited absences for the class
            404: Class not found or no permission
            401: Authentication failed
        """
        try:
            requesting_user = request.auth
            
            # Check if user manages this class
            managed_classes = get_managed_classes(requesting_user)
            if not any(cls.id == class_id for cls in managed_classes):
                return 404, {"message": "Osztály nem található vagy nincs jogosultság"}
            
            # Get students from this class
            student_profiles = Profile.objects.filter(
                osztaly_id=class_id
            ).select_related('user')
            student_ids = [p.user.id for p in student_profiles]
            
            # Filter for student-edited absences only
            absences = Absence.objects.filter(
                diak_id__in=student_ids,
                student_edited=True
            ).select_related('diak', 'forgatas')
            
            # Apply date filters
            if start_date:
                absences = absences.filter(date__gte=start_date)
            if end_date:
                absences = absences.filter(date__lte=end_date)
            
            # Order by edit timestamp (most recent edits first)
            absences = absences.order_by('-student_edit_timestamp', 'date', 'diak__last_name')
            
            response = []
            for absence in absences:
                response.append(create_absence_response(absence))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching class student-edited absences: {str(e)}"}

    @api.get("/school-absences/stats/student-edits", auth=JWTAuth(), response={200: dict, 401: ErrorSchema})
    def get_student_edit_statistics(request, class_id: int = None, start_date: str = None, end_date: str = None):
        """
        Get statistics about student edits for class teachers.
        
        Shows how many students have submitted extra time and summary information.
        
        Args:
            class_id: Optional filter by class ID
            start_date: Optional start date filter (ISO format)
            end_date: Optional end date filter (ISO format)
            
        Returns:
            200: Student edit statistics
            401: Authentication or permission failed
        """
        try:
            requesting_user = request.auth
            
            # Check if user is osztályfőnök
            has_permission, error_message = check_class_teacher_permissions(requesting_user)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Get classes managed by this teacher
            managed_classes = get_managed_classes(requesting_user)
            if not managed_classes:
                return 200, {"message": "Nincs kezelt osztály", "stats": {}}
            
            managed_class_ids = [cls.id for cls in managed_classes]
            
            # Get students from managed classes
            if class_id and class_id in managed_class_ids:
                # Specific class
                student_profiles = Profile.objects.filter(
                    osztaly_id=class_id
                ).select_related('user')
                target_classes = [cls for cls in managed_classes if cls.id == class_id]
            else:
                # All managed classes
                student_profiles = Profile.objects.filter(
                    osztaly_id__in=managed_class_ids
                ).select_related('user')
                target_classes = managed_classes
            
            managed_student_ids = [p.user.id for p in student_profiles]
            
            # Get all absences for these students
            all_absences = Absence.objects.filter(diak_id__in=managed_student_ids)
            
            # Apply date filters
            if start_date:
                all_absences = all_absences.filter(date__gte=start_date)
            if end_date:
                all_absences = all_absences.filter(date__lte=end_date)
            
            # Calculate statistics
            total_absences = all_absences.count()
            student_edited_absences = all_absences.filter(student_edited=True).count()
            
            # Get unique students who have edited absences
            students_with_edits = all_absences.filter(
                student_edited=True
            ).values_list('diak_id', flat=True).distinct()
            
            # Class-by-class breakdown
            class_stats = []
            for osztaly in target_classes:
                class_profiles = student_profiles.filter(osztaly=osztaly)
                class_student_ids = [p.user.id for p in class_profiles]
                
                class_absences = all_absences.filter(diak_id__in=class_student_ids)
                class_edited_absences = class_absences.filter(student_edited=True)
                class_students_with_edits = class_edited_absences.values_list('diak_id', flat=True).distinct()
                
                class_stats.append({
                    "class_id": osztaly.id,
                    "class_name": str(osztaly),
                    "total_students": len(class_student_ids),
                    "total_absences": class_absences.count(),
                    "edited_absences": class_edited_absences.count(),
                    "students_with_edits": len(class_students_with_edits)
                })
            
            return 200, {
                "period": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "summary": {
                    "total_students": len(managed_student_ids),
                    "total_absences": total_absences,
                    "student_edited_absences": student_edited_absences,
                    "students_with_edits": len(students_with_edits),
                    "edit_percentage": round((student_edited_absences / total_absences * 100) if total_absences > 0 else 0, 1)
                },
                "classes": class_stats
            }
            
        except Exception as e:
            return 401, {"message": f"Error fetching student edit statistics: {str(e)}"}
