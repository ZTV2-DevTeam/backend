# FTV Sync API – Többnapos forgatások (Multi-day filming sessions) update

## Kinek szól ez a dokumentum?

Az **Igazoláskezelő** fejlesztőinek. Az FTV rendszerben bevezettük a többnapos
forgatások támogatását. Ez két helyen érinti a `/api/sync/` végpontok válaszát:
a forgatás (`forgatas_details`) és a hiányzás (`Absence` / `hianyzas`) adatokat.
Ez a dokumentum **kiegészíti**, nem váltja le a meglévő
`docs/SYNC_API_DOCUMENTATION.md` és `docs/SYNC_API_QUICK_START.md` anyagokat.

## 1. Mi változott?

### 1.1 Új mezők a `forgatas_details` objektumban

| Mező | Típus | Leírás |
|------|-------|--------|
| `end_date` | `"YYYY-MM-DD"` | A forgatás **befejezésének** dátuma. Egynapos forgatásnál megegyezik a `date` mezővel. |
| `is_multi_day` | `bool` | `true`, ha a forgatás több naptári napon átnyúlik (`end_date != date`). |

A meglévő `date`, `timeFrom`, `timeTo` mezők jelentése **nem változott**: `date` +
`timeFrom` a kezdés, és többnapos esetben `end_date` + `timeTo` adja meg a
pontos befejezést (nem a `date` napján!).

### 1.2 Új mezők a hiányzás (`Absence`) objektumban

| Mező | Típus | Leírás |
|------|-------|--------|
| `is_multi_day` | `bool` | `true`, ha a hiányzás egy többnapos forgatáshoz tartozik. |
| `can_be_corrected` | `bool` | `false`, ha a diák nem korrigálhatja (mindig `false`, ha `is_multi_day == true`). |

### 1.3 ⚠️ FONTOS viselkedésbeli változás: egy forgatáshoz több hiányzás tartozhat

Eddig **egy diákhoz és egy forgatáshoz pontosan egy** automatikusan generált
`Absence` rekord tartozott. **Ez mostantól nem igaz többnapos forgatásoknál**:

- Egynapos forgatás: változatlanul **1 db** `Absence` rekord / diák / forgatás.
- Többnapos forgatás: **1 db `Absence` rekord minden naptári napra**, amit a
  forgatás érint. Mindegyik ugyanazzal a `forgatas_id`-vel rendelkezik, de más
  `date` értékkel, és a napi időhatárokat tükrözi:
  - Az első nap: `timeFrom` = a forgatás tényleges kezdési ideje, `timeTo` =
    `23:59:59` (a nap vége).
  - A köztes napok (ha vannak): `timeFrom` = `00:00:00`, `timeTo` = `23:59:59`
    (egész napos).
  - Az utolsó nap: `timeFrom` = `00:00:00`, `timeTo` = a forgatás tényleges
    befejezési ideje.

**Integrációs teendő:** ha az Igazoláskezelő eddig `forgatas_id` alapján
egyedi kulcsként kezelte a hiányzásokat (pl. upsert `ftv_id` szerint), az
továbbra is működik, mivel minden napi rekordnak **külön `id`-je** van
(ez az egyedi kulcs, nem a `forgatas_id`!). Csak arra kell figyelni, hogy egy
adott diák egy adott `forgatas_id`-hez **több** hiányzás sort is kaphat – ha
eddig `.find()`/`first()` logikával csak egyet vártatok egy forgatáshoz, azt
listaként (`.filter()`) kell kezelni.

```javascript
// ELŐTTE (feltételezve: max 1 hiányzás / forgatás / diák)
const absence = absences.find(a => a.forgatas_id === forgatasId);

// UTÁNA (helyes, többnapos-kompatibilis kezelés)
const absencesForSession = absences.filter(a => a.forgatas_id === forgatasId);
// Ha szükséges, csoportosítható "egy igazolási periódusként":
const isMultiDayGroup = absencesForSession.some(a => a.is_multi_day);
```

### 1.4 Korrigálás (diák általi kiegészítés) letiltva többnapos hiányzásoknál

A diákok a saját hiányzásukhoz tartozó extra idő előtte/utána mezőket eddig
bármikor módosíthatták (`student_extra_time_before/after`,
`student_edit_note`). **Többnapos forgatáshoz tartozó hiányzásnál ez az FTV
oldalán le van tiltva** (a diák felületén a gomb nem jelenik meg, az API pedig
`400`-at ad vissza próbálkozás esetén). Ez azt jelenti, hogy ezeknél a
rekordoknál `student_extra_time_before`/`student_extra_time_after` mindig `0`,
`student_edited` mindig `false` marad – ezt figyelembe lehet venni riportoknál,
de API-szinten nincs teendő, csak a `can_be_corrected: false` mező jelzi
explicit módon.

## 2. Példa válasz (többnapos forgatás, 3 nap)

```json
[
  {
    "id": 501,
    "diak_email": "kovacs.janos@szlg.info",
    "forgatas_id": 78,
    "date": "2026-10-12",
    "timeFrom": "14:00:00",
    "timeTo": "23:59:59",
    "is_multi_day": true,
    "can_be_corrected": false,
    "forgatas_details": {
      "name": "Vidéki kiszállásos forgatás",
      "date": "2026-10-12",
      "timeFrom": "14:00:00",
      "end_date": "2026-10-14",
      "timeTo": "11:00:00",
      "is_multi_day": true
    }
  },
  {
    "id": 502,
    "diak_email": "kovacs.janos@szlg.info",
    "forgatas_id": 78,
    "date": "2026-10-13",
    "timeFrom": "00:00:00",
    "timeTo": "23:59:59",
    "is_multi_day": true,
    "can_be_corrected": false,
    "forgatas_details": { "...": "ugyanaz, mint fent" }
  },
  {
    "id": 503,
    "diak_email": "kovacs.janos@szlg.info",
    "forgatas_id": 78,
    "date": "2026-10-14",
    "timeFrom": "00:00:00",
    "timeTo": "11:00:00",
    "is_multi_day": true,
    "can_be_corrected": false,
    "forgatas_details": { "...": "ugyanaz, mint fent" }
  }
]
```

## 3. Ki hozhat létre többnapos forgatást?

Csak adminisztrátorok és gyártásvezetők – ez FTV-oldali jogosultsági
korlátozás, az Igazoláskezelő oldalán nincs teendő vele kapcsolatban, csak
tájékoztatásul: a többnapos forgatások száma várhatóan alacsony marad.

## 4. Teendők összefoglalva

- [ ] A `forgatas_details.end_date` / `is_multi_day` mezők feldolgozása (ha a
      megjelenítésnél a pontos időtartamot szeretnétek mutatni).
- [ ] Ha eddig `forgatas_id` alapján egyedi hiányzást kerestetek, állítsátok át
      lista-alapú kezelésre (lásd 1.3).
- [ ] Nem kötelező, de ajánlott: a `can_be_corrected: false` rekordoknál ne
      ajánljatok fel "korrigálás kérése" opciót a felületeteken, mert az FTV
      úgyis elutasítja.
- [ ] Migráció/backfill **nem szükséges**: a régi, egynapos hiányzások
      formátuma és `id`-i nem változtak, csak az új mezők jelentek meg rajtuk
      (`is_multi_day: false`, `can_be_corrected: true`).

## 5. Kapcsolat

Kérdés esetén keressétek az FTV fejlesztőcsapatot a szokásos csatornán, vagy
nézzétek meg a `docs/SYNC_API_DOCUMENTATION.md` teljes referenciát.
