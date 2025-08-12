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
- GET  /filming-assignments           - Lista beosztásokról
- GET  /filming-assignments/{id}     - Konkrét beosztás részletei
- POST /filming-assignments          - Új beosztás létrehozása (admin/tanár)
- PUT  /filming-assignments/{id}     - Beosztás frissítése
- DELETE /filming-assignments/{id}   - Beosztás törlése
- POST /filming-assignments/{id}/finalize - Beosztás véglegesítése

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
from api.models import Beosztas, SzerepkorRelaciok, Szerepkor, Forgatas, Absence, Profile
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

class BeosztasCreateSchema(Schema):
    """Request schema for creating new assignment."""
    forgatas_id: int
    student_role_pairs: List[dict]  # [{"user_id": 1, "szerepkor_id": 2}, ...]

class BeosztasUpdateSchema(Schema):
    """Request schema for updating assignment."""
    student_role_pairs: Optional[List[dict]] = None
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
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.get_full_name()
    }

def create_szerepkor_response(szerepkor: Szerepkor) -> dict:
    """Create role information response."""
    return {
        "id": szerepkor.id,
        "name": szerepkor.name,
        "ev": szerepkor.ev
    }

def create_szerepkor_relacio_response(relacio: SzerepkorRelaciok) -> dict:
    """Create role relation response."""
    return {
        "id": relacio.id,
        "user": create_user_basic_response(relacio.user),
        "szerepkor": create_szerepkor_response(relacio.szerepkor)
    }

def create_forgatas_basic_response(forgatas: Forgatas) -> dict:
    """Create basic forgatas information response."""
    return {
        "id": forgatas.id,
        "name": forgatas.name,
        "description": forgatas.description,
        "date": forgatas.date.isoformat(),
        "time_from": forgatas.timeFrom.isoformat(),
        "time_to": forgatas.timeTo.isoformat(),
        "type": forgatas.forgTipus
    }

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
    
    @api.get("/filming-assignments", auth=JWTAuth(), response={200: List[BeosztasSchema], 401: ErrorSchema})
    def get_filming_assignments(request, forgatas_id: int = None, kesz: bool = None, 
                               start_date: str = None, end_date: str = None):
        """
        Get filming assignments with optional filtering.
        
        Requires authentication. Returns assignments based on user permissions.
        
        Args:
            forgatas_id: Optional filter by filming session ID
            kesz: Optional filter by completion status
            start_date: Optional start date filter for associated filming sessions
            end_date: Optional end date filter for associated filming sessions
            
        Returns:
            200: List of assignments
            401: Authentication failed
        """
        try:
            requesting_user = request.auth
            
            # Build queryset
            assignments = Beosztas.objects.select_related(
                'forgatas', 'author'
            ).prefetch_related(
                'szerepkor_relaciok__user',
                'szerepkor_relaciok__szerepkor'
            ).all()
            
            # Apply filters
            if forgatas_id:
                assignments = assignments.filter(forgatas_id=forgatas_id)
            
            if kesz is not None:
                assignments = assignments.filter(kesz=kesz)
            
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
            return 401, {"message": f"Error fetching assignments: {str(e)}"}

    @api.get("/filming-assignments/{assignment_id}", auth=JWTAuth(), response={200: BeosztasSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_filming_assignment_details(request, assignment_id: int):
        """
        Get detailed information about a specific assignment.
        
        Requires authentication.
        
        Args:
            assignment_id: Unique assignment identifier
            
        Returns:
            200: Detailed assignment information
            404: Assignment not found
            401: Authentication failed
        """
        try:
            assignment = Beosztas.objects.select_related(
                'forgatas', 'author'
            ).prefetch_related(
                'szerepkor_relaciok__user',
                'szerepkor_relaciok__szerepkor'
            ).get(id=assignment_id)
            
            return 200, create_beosztas_response(assignment)
        except Beosztas.DoesNotExist:
            return 404, {"message": "Beosztás nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching assignment details: {str(e)}"}

    @api.post("/filming-assignments", auth=JWTAuth(), response={201: BeosztasSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_filming_assignment(request, data: BeosztasCreateSchema):
        """
        Create new filming assignment.
        
        Requires admin/teacher permissions. Creates assignment and role relations.
        
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
            
            # Check if assignment already exists for this forgatas
            existing = Beosztas.objects.filter(forgatas=forgatas).first()
            if existing:
                return 400, {"message": f"Ehhez a forgatáshoz már létezik beosztás (ID: {existing.id})"}
            
            # Validate student-role pairs
            if not data.student_role_pairs:
                return 400, {"message": "Legalább egy diák-szerepkör párosítás szükséges"}
            
            with transaction.atomic():
                # Create assignment
                beosztas = Beosztas.objects.create(
                    forgatas=forgatas,
                    author=requesting_user,
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
                        
                    except (User.DoesNotExist, Szerepkor.DoesNotExist):
                        continue  # Skip invalid pairs
                
                if not created_relations:
                    return 400, {"message": "Egyetlen érvényes diák-szerepkör párosítás sem található"}
            
            return 201, create_beosztas_response(beosztas)
        except Exception as e:
            return 400, {"message": f"Error creating assignment: {str(e)}"}

    @api.put("/filming-assignments/{assignment_id}", auth=JWTAuth(), response={200: BeosztasSchema, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
    def update_filming_assignment(request, assignment_id: int, data: BeosztasUpdateSchema):
        """
        Update existing filming assignment.
        
        Requires proper permissions. Can update student-role relations and completion status.
        
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
            
            # Check permissions
            if not can_user_manage_beosztas(requesting_user, beosztas):
                return 401, {"message": "Nincs jogosultság a beosztás szerkesztéséhez"}
            
            # Cannot update finalized assignments (except for re-finalizing)
            if beosztas.kesz and data.kesz != True:
                return 400, {"message": "Véglegesített beosztást nem lehet módosítani"}
            
            with transaction.atomic():
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
                            
                        except (User.DoesNotExist, Szerepkor.DoesNotExist):
                            continue  # Skip invalid pairs
                
                # Update completion status
                if data.kesz is not None:
                    beosztas.kesz = data.kesz
                    beosztas.save()
                    
                    # If finalizing, create absences
                    if data.kesz:
                        auto_create_absences_for_beosztas(beosztas)
            
            return 200, create_beosztas_response(beosztas)
        except Beosztas.DoesNotExist:
            return 404, {"message": "Beosztás nem található"}
        except Exception as e:
            return 400, {"message": f"Error updating assignment: {str(e)}"}

    @api.post("/filming-assignments/{assignment_id}/finalize", auth=JWTAuth(), response={200: BeosztasSchema, 401: ErrorSchema, 404: ErrorSchema})
    def finalize_filming_assignment(request, assignment_id: int):
        """
        Finalize filming assignment and create absences.
        
        Marks the assignment as completed (kesz=True) and automatically creates
        Absence records for all assigned students.
        
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
            
            with transaction.atomic():
                beosztas.kesz = True
                beosztas.save()
                
                # Create absences for all assigned students
                auto_create_absences_for_beosztas(beosztas)
            
            return 200, create_beosztas_response(beosztas)
        except Beosztas.DoesNotExist:
            return 404, {"message": "Beosztás nem található"}
        except Exception as e:
            return 400, {"message": f"Error finalizing assignment: {str(e)}"}

    @api.delete("/filming-assignments/{assignment_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
    def delete_filming_assignment(request, assignment_id: int):
        """
        Delete filming assignment.
        
        Requires proper permissions. Also deletes associated role relations and
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
            
            # Check permissions
            if not can_user_manage_beosztas(requesting_user, beosztas):
                return 401, {"message": "Nincs jogosultság a beosztás törléséhez"}
            
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

    @api.get("/roles", auth=JWTAuth(), response={200: List[SzerepkorSchema], 401: ErrorSchema})
    def get_available_roles(request):
        """
        Get all available roles for assignments.
        
        Returns all roles that can be assigned to students in filming sessions.
        
        Returns:
            200: List of available roles
            401: Authentication failed
        """
        try:
            roles = Szerepkor.objects.all().order_by('name')
            
            response = []
            for role in roles:
                response.append(create_szerepkor_response(role))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching roles: {str(e)}"}

    @api.get("/filming-assignments/{assignment_id}/absences", auth=JWTAuth(), response={200: List[dict], 401: ErrorSchema, 404: ErrorSchema})
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
