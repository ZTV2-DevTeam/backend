# FTV Equipment Management API Guide

## Áttekintés

Az FTV rendszer equipment (felszerelés) kezelő API-ja kibővített funkcionalitással rendelkezik a felszerelések forgatásokhoz történő hozzárendelése és elérhetőségük nyomon követése érdekében.

## Új API Endpointok

### 1. Equipment Elérhetőség Ellenőrzés

**Endpoint:** `GET /api/equipment/{equipment_id}/availability`

**Paraméterek:**
- `equipment_id`: Az eszköz egyedi azonosítója
- `start_date`: Kezdő dátum (YYYY-MM-DD formátum)
- `start_time`: Kezdő időpont (HH:MM formátum) 
- `end_date`: Befejező dátum (opcionális, alapból start_date)
- `end_time`: Befejező időpont (opcionális, alapból start_time + 1 óra)

**Példa kérés:**
```
GET /api/equipment/1/availability?start_date=2024-03-15&start_time=14:00&end_date=2024-03-15&end_time=16:00
Authorization: Bearer {jwt_token}
```

**Válasz:**
```json
{
  "equipment_id": 1,
  "available": false,
  "conflicts": [
    {
      "type": "filming_session",
      "forgatas_id": 5,
      "forgatas_name": "Reggeli műsor felvétel",
      "date": "2024-03-15",
      "time_from": "13:30",
      "time_to": "15:00",
      "location": "Stúdió A",
      "type_display": "Rendes"
    }
  ]
}
```

### 2. Equipment Ütemterv

**Endpoint:** `GET /api/equipment/{equipment_id}/schedule`

**Paraméterek:**
- `equipment_id`: Az eszköz egyedi azonosítója
- `start_date`: Kezdő dátum (YYYY-MM-DD)
- `end_date`: Befejező dátum (opcionális)

**Példa kérés:**
```
GET /api/equipment/1/schedule?start_date=2024-03-15&end_date=2024-03-22
Authorization: Bearer {jwt_token}
```

**Válasz:**
```json
{
  "equipment_id": 1,
  "equipment_name": "Főkamera",
  "schedule": [
    {
      "date": "2024-03-15",
      "time_from": "13:30",
      "time_to": "15:00",
      "forgatas_name": "Reggeli műsor felvétel",
      "forgatas_id": 5,
      "forgatas_type": "rendes",
      "location": "Stúdió A",
      "available": false
    },
    {
      "date": "2024-03-16",
      "time_from": "10:00",
      "time_to": "12:00",
      "forgatas_name": "KaCsa epizód",
      "forgatas_id": 7,
      "forgatas_type": "kacsa",
      "location": "Külső helyszín",
      "available": false
    }
  ]
}
```

### 3. Equipment Használati Statisztika

**Endpoint:** `GET /api/equipment/{equipment_id}/usage`

**Paraméterek:**
- `equipment_id`: Az eszköz egyedi azonosítója
- `days_back`: Visszatekintési napok száma (alapból 30)

**Példa kérés:**
```
GET /api/equipment/1/usage?days_back=60
Authorization: Bearer {jwt_token}
```

**Válasz:**
```json
{
  "equipment_id": 1,
  "equipment_name": "Főkamera",
  "total_bookings": 12,
  "upcoming_bookings": 3,
  "usage_hours": 48.5,
  "most_recent_use": "2024-03-10",
  "next_booking": {
    "forgatas_id": 15,
    "forgatas_name": "Következő forgatás",
    "date": "2024-03-18",
    "time_from": "09:00",
    "time_to": "11:00",
    "location": "Stúdió B"
  }
}
```

### 4. Napi Elérhetőségi Áttekintés

**Endpoint:** `GET /api/equipment/availability-overview`

**Paraméterek:**
- `date`: Ellenőrzendő dátum (YYYY-MM-DD)
- `type_id`: Eszköz típus szűrő (opcionális)

**Példa kérés:**
```
GET /api/equipment/availability-overview?date=2024-03-15&type_id=1
Authorization: Bearer {jwt_token}
```

**Válasz:**
```json
[
  {
    "equipment_id": 1,
    "equipment_name": "Főkamera",
    "equipment_type": "Kamera",
    "functional": true,
    "available_periods": false,
    "bookings": [
      {
        "forgatas_id": 5,
        "forgatas_name": "Reggeli műsor",
        "time_from": "13:30",
        "time_to": "15:00",
        "type": "rendes",
        "location": "Stúdió A"
      }
    ],
    "booking_count": 1
  },
  {
    "equipment_id": 2,
    "equipment_name": "Mikrofon 1",
    "equipment_type": "Audio",
    "functional": true,
    "available_periods": true,
    "bookings": [],
    "booking_count": 0
  }
]
```

## Forgatás Equipment Kezelés

A forgatásokban az equipment kezelés az alábbi endpontokon keresztül történik:

### Production API Integráció

**Forgatás létrehozás equipment-tel:**
```json
POST /api/production/filming-sessions
{
  "name": "Új forgatás",
  "description": "Forgatás leírás",
  "date": "2024-03-20",
  "time_from": "14:00",
  "time_to": "16:00",
  "type": "rendes",
  "equipment_ids": [1, 2, 3],
  "location_id": 1,
  "contact_person_id": 1
}
```

**Forgatás módosítás equipment-tel:**
```json
PUT /api/production/filming-sessions/{id}
{
  "equipment_ids": [1, 2, 4]
}
```

## Frontend Integráció

### JavaScript/TypeScript Példa

```javascript
class EquipmentManager {
  constructor(baseUrl, jwtToken) {
    this.baseUrl = baseUrl;
    this.token = jwtToken;
    this.headers = {
      'Authorization': `Bearer ${this.token}`,
      'Content-Type': 'application/json'
    };
  }

  // Equipment elérhetőség ellenőrzés
  async checkEquipmentAvailability(equipmentId, startDate, startTime, endDate = null, endTime = null) {
    const params = new URLSearchParams({
      start_date: startDate,
      start_time: startTime
    });
    
    if (endDate) params.append('end_date', endDate);
    if (endTime) params.append('end_time', endTime);
    
    const response = await fetch(
      `${this.baseUrl}/api/equipment/${equipmentId}/availability?${params}`,
      { headers: this.headers }
    );
    
    return await response.json();
  }

  // Equipment ütemterv lekérés
  async getEquipmentSchedule(equipmentId, startDate, endDate = null) {
    const params = new URLSearchParams({ start_date: startDate });
    if (endDate) params.append('end_date', endDate);
    
    const response = await fetch(
      `${this.baseUrl}/api/equipment/${equipmentId}/schedule?${params}`,
      { headers: this.headers }
    );
    
    return await response.json();
  }

  // Használati statisztika
  async getEquipmentUsage(equipmentId, daysBack = 30) {
    const response = await fetch(
      `${this.baseUrl}/api/equipment/${equipmentId}/usage?days_back=${daysBack}`,
      { headers: this.headers }
    );
    
    return await response.json();
  }

  // Napi áttekintés
  async getDailyOverview(date, typeId = null) {
    const params = new URLSearchParams({ date });
    if (typeId) params.append('type_id', typeId);
    
    const response = await fetch(
      `${this.baseUrl}/api/equipment/availability-overview?${params}`,
      { headers: this.headers }
    );
    
    return await response.json();
  }

  // Forgatás létrehozása equipment-tel
  async createFilmingSessionWithEquipment(sessionData) {
    const response = await fetch(
      `${this.baseUrl}/api/production/filming-sessions`,
      {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify(sessionData)
      }
    );
    
    return await response.json();
  }

  // Equipment elérhetőségi validáció forgatás előtt
  async validateEquipmentForSession(equipmentIds, date, timeFrom, timeTo) {
    const validationResults = [];
    
    for (const equipmentId of equipmentIds) {
      const availability = await this.checkEquipmentAvailability(
        equipmentId, 
        date, 
        timeFrom, 
        date, 
        timeTo
      );
      
      validationResults.push({
        equipmentId,
        available: availability.available,
        conflicts: availability.conflicts
      });
    }
    
    return validationResults;
  }
}

// Használat:
const equipmentManager = new EquipmentManager('http://your-backend-url', 'your-jwt-token');

// Equipment elérhetőség ellenőrzés
const availability = await equipmentManager.checkEquipmentAvailability(
  1, '2024-03-15', '14:00', '2024-03-15', '16:00'
);

// Napi áttekintés
const dailyOverview = await equipmentManager.getDailyOverview('2024-03-15');

// Forgatás létrehozás validációval
const sessionData = {
  name: "Új forgatás",
  description: "Teszt forgatás",
  date: "2024-03-20", 
  time_from: "14:00",
  time_to: "16:00",
  type: "rendes",
  equipment_ids: [1, 2, 3]
};

// Első ellenőrizzük az equipment elérhetőségét
const validation = await equipmentManager.validateEquipmentForSession(
  sessionData.equipment_ids,
  sessionData.date,
  sessionData.time_from,
  sessionData.time_to
);

const hasConflicts = validation.some(result => !result.available);
if (hasConflicts) {
  console.log('Equipment conflict detected:', validation);
  // Kezelje a konfliktust
} else {
  // Létrehozhatja a forgatást
  const result = await equipmentManager.createFilmingSessionWithEquipment(sessionData);
}
```

### React Hook Példa

```javascript
import { useState, useEffect } from 'react';

export const useEquipmentAvailability = (equipmentId, date) => {
  const [availability, setAvailability] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!equipmentId || !date) return;

    const checkAvailability = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(
          `/api/equipment/${equipmentId}/schedule?start_date=${date}&end_date=${date}`,
          {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`
            }
          }
        );
        
        if (!response.ok) throw new Error('Failed to fetch availability');
        
        const data = await response.json();
        setAvailability(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    checkAvailability();
  }, [equipmentId, date]);

  return { availability, loading, error };
};

// Használat komponensben:
function EquipmentSchedule({ equipmentId, date }) {
  const { availability, loading, error } = useEquipmentAvailability(equipmentId, date);

  if (loading) return <div>Betöltés...</div>;
  if (error) return <div>Hiba: {error}</div>;
  if (!availability) return <div>Nincs adat</div>;

  return (
    <div>
      <h3>{availability.equipment_name} - {date}</h3>
      {availability.schedule.length === 0 ? (
        <p>Az eszköz egész nap elérhető</p>
      ) : (
        <ul>
          {availability.schedule.map((booking, index) => (
            <li key={index}>
              {booking.time_from} - {booking.time_to}: {booking.forgatas_name}
              ({booking.location || 'Nincs helyszín'})
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

## Hibakezelés

Az API konzisztens hibakezelést biztosít:

- **200/201**: Sikeres műveletek
- **400**: Validációs hibák (hibás dátum formátum, stb.)
- **401**: Authentikáció szükséges vagy sikertelen
- **404**: Eszköz nem található
- **500**: Szerver hiba

Minden hiba esetén a válasz tartalmaz egy `message` mezőt magyar nyelvű hibaüzenettel.

## Összefoglalás

Ez az API lehetővé teszi:

1. **Equipment elérhetőség valós idejű ellenőrzését** forgatás tervezésnél
2. **Részletes ütemterv megtekintését** equipment-enkénti bontásban
3. **Használati statisztikák követését** decision support-hoz
4. **Napi áttekintést** az összes equipment állapotáról
5. **Automatikus ütközés detektálást** forgatás létrehozásnál

Az API teljes mértékben integrált a meglévő forgatás és equipment kezelő rendszerrel, és lehetővé teszi a frontend fejlesztők számára, hogy komplex equipment kezelő felületeket építsenek.
