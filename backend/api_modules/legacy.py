"""
Legacy API Endpoints

GET /legacy/beosztasview/
Header: Auth

Only if the forgatas is in the future

Response if admin:
[
    {
        "id": forgatas.id,
        "name": forgatas.name,
        "description": forgatas.description,
        "date": forgatas.date.isoformat(),
        "time_from": forgatas.timeFrom.isoformat(),
        "time_to": forgatas.timeTo.isoformat(),
        "location": {
            "id": forgatas.location.id,
            "name": forgatas.location.name,
            "address": forgatas.location.address
        } if forgatas.location else None,
        "contact_person": create_contact_person_response(forgatas.contactPerson) if forgatas.contactPerson else None,
        "notes": forgatas.notes,
        "type": forgatas.forgTipus,
        "type_display": type_display,
        "related_kacsa": {
            "id": forgatas.relatedKaCsa.id,
            "name": forgatas.relatedKaCsa.name,
            "date": forgatas.relatedKaCsa.date.isoformat()
        } if forgatas.relatedKaCsa else None,
        "equipment_ids": list(forgatas.equipments.values_list('id', flat=True)),
        "equipment_count": forgatas.equipments.count(),
        "beosztas": beosztas.objects.filter(forgatas=forgatas) - serialized,
        "tanev": {
            "id": forgatas.tanev.id,
            "display_name": str(forgatas.tanev),
            "is_active": Tanev.get_active() and Tanev.get_active().id == forgatas.tanev.id
        } if forgatas.tanev else None
    }
]

POST /legacy/beosztas/

{
    "beosztas": 1,
    "forgatas": 1,
    "user": 3,
    "role": "Asszisztens"

}

"""

from ninja import Schema
from django.contrib.auth.models import User
from api.models import Announcement
from .auth import JWTAuth, ErrorSchema
from datetime import datetime
from typing import Optional
from api.models import Forgatas, Beosztas, Tanev, SzerepkorRelaciok, Szerepkor

def register_legacy_endpoints(api):
    def create_contact_person_response(contact_person):
        return {
            "id": contact_person.id,
            "name": contact_person.name,
            "email": contact_person.email,
            "phone": contact_person.phone,
        }

    @api.get("/legacy/beosztasview/", auth=JWTAuth())
    def get_legacy_beosztasview(request):
        user = request.auth
        now = datetime.now()
        forgatas_qs = Forgatas.objects.filter(date__gte=now)
        is_admin = user.is_superuser

        result = []
        for forgatas in forgatas_qs:
            type_display = getattr(forgatas, 'get_forgTipus_display', lambda: forgatas.forgTipus)()
            beosztas_qs = Beosztas.objects.filter(forgatas=forgatas)
            beosztas_serialized = []
            for b in beosztas_qs:
                for szerepkor_rel in b.szerepkor_relaciok.all():
                    beosztas_serialized.append({
                        "id": b.id,
                        "user_id": szerepkor_rel.user.id,
                        "role": szerepkor_rel.szerepkor.name,
                    })
            result.append({
                "id": forgatas.id,
                "name": forgatas.name,
                "description": forgatas.description,
                "date": forgatas.date.isoformat() if forgatas.date else None,
                "time_from": forgatas.timeFrom.isoformat() if forgatas.timeFrom else None,
                "time_to": forgatas.timeTo.isoformat() if forgatas.timeTo else None,
                "location": {
                    "id": forgatas.location.id,
                    "name": forgatas.location.name,
                    "address": forgatas.location.address
                } if forgatas.location else None,
                "contact_person": create_contact_person_response(forgatas.contactPerson) if forgatas.contactPerson else None,
                "notes": forgatas.notes,
                "type": forgatas.forgTipus,
                "type_display": type_display,
                "related_kacsa": {
                    "id": forgatas.relatedKaCsa.id,
                    "name": forgatas.relatedKaCsa.name,
                    "date": forgatas.relatedKaCsa.date.isoformat()
                } if forgatas.relatedKaCsa else None,
                "equipment_ids": list(forgatas.equipments.values_list('id', flat=True)),
                "equipment_count": forgatas.equipments.count(),
                "beosztas": beosztas_serialized,
                "tanev": {
                    "id": forgatas.tanev.id,
                    "display_name": str(forgatas.tanev),
                    "is_active": Tanev.get_active() and Tanev.get_active().id == forgatas.tanev.id
                } if forgatas.tanev else None
            })
        return result

    class BeosztasCreateSchema(Schema):
        beosztas: int
        forgatas: int
        user: int
        role: str

    @api.post("/legacy/beosztas/", response={200: dict, 400: ErrorSchema}, auth=JWTAuth())
    def post_legacy_beosztas(request, payload: BeosztasCreateSchema):
        try:
            forgatas = Forgatas.objects.get(id=payload.forgatas)
            user = User.objects.get(id=payload.user)
            
            # Get or create the Szerepkor (role)
            szerepkor, created = Szerepkor.objects.get_or_create(name=payload.role)
            
            # Create a Beosztas object
            beosztas_obj = Beosztas.objects.create(forgatas=forgatas)
            
            # Create SzerepkorRelaciok to link user and szerepkor
            szerepkor_rel = SzerepkorRelaciok.objects.create(
                user=user,
                szerepkor=szerepkor
            )
            
            # Add the relation to the beosztas
            beosztas_obj.szerepkor_relaciok.add(szerepkor_rel)
            
            return {
                "id": beosztas_obj.id,
                "forgatas": beosztas_obj.forgatas.id,
                "user": user.id,
                "role": szerepkor.name
            }
        except Forgatas.DoesNotExist:
            return 400, {"error": "Forgatas not found"}
        except User.DoesNotExist:
            return 400, {"error": "User not found"}
        except Exception as e:
            return 400, {"error": str(e)}