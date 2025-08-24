# FTV User Import CSV API Reference

## Overview

The FTV User Import API provides endpoints for bulk user import from CSV files with comprehensive validation and preview capabilities. The system supports Hungarian character encoding and provides detailed model previews before actual data creation.

**Base URL:** `/api/user-import/`

**Authentication:** JWT Token required for all endpoints

## CSV Format Specification

### Important: Encoding Requirements

⚠️ **Critical:** Your CSV file must be saved with **## Supported Formats

- **File Types:** `.csv`
- **Encodings:** UTF-8, UTF-8 with BOM
- **Delimiters:** Semicolon (`;`), Comma (`,`), Tab (`\t`)
- **Boolean Values:** `Igen`/`Nem`, `igen`/`nem`, `true`/`false`, or empty
- **Multiple Values:** Semicolon-separated (e.g., `9.A;9.B;10.C`)

---

## Troubleshooting

### Problem: Garbled Hungarian Characters

**Symptoms:** You see `Vezet�kn�v` instead of `Vezetéknév`

**Solution:**
1. **Excel Users:**
   - File → Save As → CSV UTF-8 (Comma delimited) *.csv
   - **NOT** "CSV (Comma delimited)" - this uses incorrect encoding

2. **Notepad++ Users:**
   - Encoding → Convert to UTF-8
   - Save the file

3. **LibreOffice Calc:**
   - File → Save As → Text CSV
   - Character set: Unicode (UTF-8)
   - Field delimiter: Semicolon

### Problem: Semicolon vs Comma Delimiters

Your CSV uses semicolons (`;`) which is correct for Hungarian locale. The API automatically detects delimiters, so both work:

✅ **Semicolon (Hungarian standard):** `Nagy;Imre;+36301234567`  
✅ **Comma (English standard):** `Nagy,Imre,+36301234567`

### Problem: Empty Fields

**Correct way to handle empty fields:**
```csv
Vezetéknév;Keresztnév;Telefonszám;E-mail cím;Stáb;Kezdés éve;Tagozat;Rádió;Gyártásvezető?;Médiatanár;Osztályfőnök;Osztályai
Nagy;Imre;+36301234567;nagy.imre@szlgbp.hu;B stáb;2025;F;;;;;
Csanádi;Ágnes;;csanadi.agnes@szlgbp.hu;;;;;;Igen;2023F
```

- Leave empty cells for optional fields
- Don't use "NULL", "N/A", or "-"
- Empty string is interpreted as `false` for boolean fields

### Problem: Multiple Classes Format

**Correct format for multiple classes:**
```csv
Osztályai
2023F;2024F;2025F
9.A;9.B;10.C
```

**Incorrect formats:**
- ❌ `2023F,2024F` (comma instead of semicolon)
- ❌ `2023F | 2024F` (pipe separator)
- ❌ `2023F and 2024F` (text)

### Problem: Boolean Field Values

**Accepted values for `Igen`/`Nem` fields:**

✅ **For True:** `Igen`, `igen`, `Yes`, `yes`, `True`, `true`, `1`  
✅ **For False:** `Nem`, `nem`, `No`, `no`, `False`, `false`, `0`, `` (empty)

**Examples:**
```csv
Gyártásvezető?;Médiatanár;Osztályfőnök
Igen;Nem;
igen;;Igen
Yes;No;True
```

### API Testing with cURL

**Test with your actual file:**
```bash
curl -X POST "http://localhost:8000/api/user-import/import-csv-preview" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@path/to/your/file.csv"
```

**Expected success response status:** `200 OK`  
**Expected error response status:** `400 Bad Request`

### Common Validation Errors

1. **Duplicate emails:** Each email must be unique
2. **Invalid email format:** Must contain `@` and valid domain
3. **Missing required fields:** `Vezetéknév`, `Keresztnév`, `E-mail cím` are mandatory
4. **Username conflicts:** Generated from email prefix (before @)

### File Size Limits

- **Maximum file size:** 10MB
- **Maximum rows:** 1000 users per import
- **Processing time:** Usually < 30 seconds for 1000 users

### Getting Help

If you encounter issues:

1. **Check encoding:** Save as UTF-8
2. **Validate structure:** Use the template from `/import-template` endpoint
3. **Test small batch:** Try with 2-3 users first
4. **Check logs:** Error messages provide specific line numbers

**Contact:** System administrator for authentication issues or server errors.ncoding** to properly display Hungarian characters. If you see garbled characters like `Vezet�kn�v` instead of `Vezetéknév`, your file has encoding issues.

**How to fix encoding issues:**
1. Open your CSV in a text editor (like Notepad++)
2. Save as UTF-8 encoding
3. Or use Excel: File → Save As → CSV UTF-8 (Comma delimited)

### Expected Column Headers

The CSV file should contain the following columns (Hungarian headers supported):

| English Name | Hungarian Name | Required | Description |
|--------------|----------------|----------|-------------|
| `vezetekNev` | `Vezetéknév` | ✅ | Last name |
| `keresztNev` | `Keresztnév` | ✅ | First name |
| `email` | `E-mail cím` | ✅ | Email address |
| `password` | `Jelszó` | ❌ | Password (will be auto-generated if empty) |
| `telefonszam` | `Telefonszám` | ❌ | Phone number |
| `stab` | `Stáb` | ❌ | Radio stab assignment |
| `kezdesEve` | `Kezdés éve` | ❌ | Starting year |
| `tagozat` | `Tagozat` | ❌ | Department/Track |
| `radio` | `Rádió` | ❌ | Radio stab name |
| `gyartasvezeto` | `Gyártásvezető?` | ❌ | Production manager (Igen/Nem) |
| `mediatana` | `Médiatanár` | ❌ | Media teacher (Igen/Nem) |
| `osztalyfonok` | `Osztályfőnök` | ❌ | Class teacher (Igen/Nem) |
| `osztalyai` | `Osztályai` | ❌ | Classes (semicolon separated) |

### CSV File Requirements

- **Encoding:** UTF-8 (with or without BOM) **← CRITICAL**
- **Delimiters:** Semicolon (`;`), comma (`,`), or tab supported
- **File Extension:** `.csv`
- **Multiple Classes:** Separate with semicolon (e.g., `9.A;9.B;10.C`)
- **Boolean Values:** `Igen`/`Nem`, `igen`/`nem`, or leave empty
- **Empty Values:** Leave cells empty for optional fields

### Example CSV Content (Properly Encoded)

```csv
Vezetéknév;Keresztnév;Telefonszám;E-mail cím;Stáb;Kezdés éve;Tagozat;Rádió;Gyártásvezető?;Médiatanár;Osztályfőnök;Osztályai
Nagy;Imre;+36301234567;nagy.imre.25f@szlgbp.hu;B stáb;2025;F;;;;;
Kis;Péter;+36301234568;kis.peter.25f@szlgbp.hu;A stáb;2025;F;;;;;
Kovács;Anna;+36301234569;kovacs.anna.24f@szlgbp.hu;B stáb;2024;F;B3;;;;
Tóth;János;+36301234570;toth.janos.24f@szlgbp.hu;A stáb;2024;F;;Igen;;;
Horváth;Bence;+36301234575;horvath.bence@szlgbp.hu;;;;;;Igen;Igen;2025F
Csanádi;Ágnes;;csanadi.agnes@szlgbp.hu;;;;;;Igen;2024F
```

### Real-world Example from Your File Format

Based on your sample file, here's how it should look with proper UTF-8 encoding:

```csv
Vezetéknév;Keresztnév;Telefonszám;E-mail cím;Stáb;Kezdés éve;Tagozat;Rádió;Gyártásvezető?;Médiatanár;Osztályfőnök;Osztályai
Nagy;Imre;+36301234567;nagy.imre.25f@szlgbp.hu;B stáb;2025;F;;;;;
Varga;Iván;+36301234567;varga.ivan.24f@szlgbp.hu;B stáb;2024;F;;;;;
Minta;Katalin;+36301234567;minta.katalin.23f@szlgbp.hu;B stáb;2023;F;;Igen;;;
Márton;Jenő;+36301234567;marton.jeno.22f@szlgbp.hu;B stáb;2022;F;B3;;;;
Csanádi;Ágnes;;csanadi.agnes@szlgbp.hu;;;;;;Igen;2023F
Horváth;Bence;+36301234567;horvath.bence@szlgbp.hu;;;;;;Igen;Igen;2022F
```

---

## API Endpoints

### 1. CSV Preview and Validation

#### `POST /api/user-import/import-csv-preview`

Upload and preview CSV file content without creating any database records.

**Purpose:** Allows frontend to display what would be imported and validate data before actual import.

**Request:**
- **Content-Type:** `multipart/form-data`
- **Body:** CSV file upload

**Response Schema:**
```json
{
  "success": true,
  "message": "CSV successfully parsed",
  "parsed_users": [
    {
      "vezetek_nev": "Nagy",
      "kereszt_nev": "Imre",
      "email": "nagy.imre.25f@szlgbp.hu",
      "telefonszam": "+36301234567",
      "stab": "B stáb",
      "kezdes_eve": 2025,
      "tagozat": "F",
      "radio": null,
      "gyartasvezeto": false,
      "mediatana": false,
      "osztalyfonok": false,
      "osztalyai": []
    },
    {
      "vezetek_nev": "Csanádi",
      "kereszt_nev": "Ágnes",
      "email": "csanadi.agnes@szlgbp.hu",
      "telefonszam": null,
      "stab": null,
      "kezdes_eve": null,
      "tagozat": null,
      "radio": null,
      "gyartasvezeto": false,
      "mediatana": true,
      "osztalyfonok": false,
      "osztalyai": ["2023F"]
    }
  ],
  "summary": {
    "total_users": 17,
    "users_with_stab": 13,
    "users_with_radio": 4,
    "users_with_classes": 4,
    "production_managers": 3,
    "media_teachers": 4,
    "class_teachers": 3
  },
  "model_preview": {
    "users_to_create": [
      "Nagy Imre (nagy.imre.25f@szlgbp.hu)",
      "Kis Imre (kis.imre.25f@szlgbp.hu)",
      "Varga Iván (varga.ivan.24f@szlgbp.hu)",
      "Csanádi Ágnes (csanadi.agnes@szlgbp.hu)"
    ],
    "stabs_to_create": [
      "A stáb",
      "B stáb"
    ],
    "radio_stabs_to_create": [
      "B3 (Radio)",
      "B4 (Radio)",
      "A1 (Radio)"
    ],
    "classes_to_create": [
      "2023F",
      "2022F"
    ],
    "class_teacher_assignments": [
      "Csanádi Ágnes → 2023F",
      "Horváth Bence → 2022F"
    ]
  },
  "errors": [],
  "warnings": [
    "Csanádi Ágnes: Nincs telefonszám megadva",
    "Tóth Dóra: Nincs telefonszám megadva"
  ]
}
```

**Common Error Cases:**

**Encoding Error Response:**
```json
{
  "success": false,
  "message": "CSV parsing failed",
  "errors": [
    "Karakterkódolási hiba: A fájl nem UTF-8 formátumban van mentve. Kérjük mentse el UTF-8 kódolással."
  ]
}
```

**Missing Required Columns:**
```json
{
  "success": false,
  "message": "CSV parsing failed", 
  "errors": [
    "Hiányzó kötelező oszlopok: email (elfogadott nevek: email, E-mail cím, Email, e_mail)"
  ]
}
```

**Error Responses:**
- `400` - Invalid file format, parsing errors
- `401` - Authentication failed or insufficient permissions

---

### 2. Import Validated Data

#### `POST /api/user-import/import-validated-data`

Create users and related models from validated import data.

**Purpose:** Actually creates database records after user has reviewed the preview.

**Request Schema:**
```json
{
  "users": [
    {
      "vezetek_nev": "Nagy",
      "kereszt_nev": "Imre",
      "email": "nagy.imre.25f@szlgbp.hu",
      "telefonszam": "+36301234567",
      "stab": "B stáb",
      "kezdes_eve": 2025,
      "tagozat": "F",
      "radio": null,
      "gyartasvezeto": false,
      "mediatana": false,
      "osztalyfonok": false,
      "osztalyai": []
    }
  ]
}
```

**Response Schema:**
```json
{
  "success": true,
  "message": "12 felhasználó sikeresen importálva",
  "summary": {
    "users_created": 12,
    "stabs_created": 2,
    "radio_stabs_created": 2,
    "classes_created": 3,
    "class_teachers_assigned": 3
  },
  "created_models": {
    "users": [
      {
        "id": 101,
        "username": "nagy.imre.25f",
        "email": "nagy.imre.25f@szlgbp.hu",
        "first_name": "Imre",
        "last_name": "Nagy"
      }
    ],
    "stabs": [
      {
        "id": 15,
        "nev": "A stáb"
      },
      {
        "id": 16,
        "nev": "B stáb"
      }
    ],
    "radio_stabs": [
      {
        "id": 8,
        "nev": "B3"
      }
    ],
    "classes": [
      {
        "id": 25,
        "nev": "2025F",
        "tanev": "2024/2025"
      }
    ]
  },
  "errors": [],
  "warnings": []
}
```

---

### 3. Import Template

#### `GET /api/user-import/import-template`

Get template structure and example data for user import.

**Response Schema:**
```json
{
  "description": "FTV felhasználó import sablon",
  "required_fields": [
    "vezetekNev", "keresztNev", "email"
  ],
  "optional_fields": [
    "telefonszam", "stab", "kezdesEve", "tagozat", "radio",
    "gyartasvezeto", "mediatana", "osztalyfonok", "osztalyai"
  ],
  "supported_column_names": {
    "vezetekNev": ["vezetekNev", "Vezetéknév", "last_name"],
    "keresztNev": ["keresztNev", "Keresztnév", "first_name"],
    "email": ["email", "E-mail cím", "Email", "e_mail"],
    "telefonszam": ["telefonszam", "Telefonszám", "phone", "telefon"],
    "stab": ["stab", "Stáb"],
    "kezdesEve": ["kezdesEve", "Kezdés éve", "starting_year"],
    "tagozat": ["tagozat", "Tagozat", "department"],
    "radio": ["radio", "Rádió", "radio_stab"],
    "gyartasvezeto": ["gyartasvezeto", "Gyártásvezető?", "production_manager"],
    "mediatana": ["mediatana", "Médiatanár", "media_teacher"],
    "osztalyfonok": ["osztalyfonok", "Osztályfőnök", "class_teacher"],
    "osztalyai": ["osztalyai", "Osztályai", "classes"]
  },
  "example_csv": "Vezetéknév,Keresztnév,E-mail cím,Telefonszám,Stáb,Kezdés éve,Tagozat,Rádió,Gyártásvezető?,Médiatanár,Osztályfőnök,Osztályai\nNagy,Imre,nagy.imre@example.com,+36301234567,A stáb,2025,F,,,,,\nKis,Péter,kis.peter@example.com,,B stáb,2024,M,B3,,,,\nKovács,Anna,kovacs.anna@example.com,+36309876543,,,,,Igen,Igen,2025F"
}
```

---

## Admin Status Endpoints

### 4. System Overview

#### `GET /api/user-import/system-overview`

Get comprehensive system statistics.

**Response Schema:**
```json
{
  "total_users": 156,
  "total_profiles": 156,
  "total_stabs": 12,
  "total_radio_stabs": 8,
  "total_classes": 24,
  "users_by_role": {
    "students": 120,
    "teachers": 25,
    "production_managers": 6,
    "media_teachers": 8,
    "class_teachers": 12
  },
  "recent_activity": {
    "users_created_today": 0,
    "users_created_this_week": 12,
    "users_created_this_month": 45
  }
}
```

### 5. User Statistics

#### `GET /api/user-import/users-status`

Get detailed user statistics and breakdowns.

**Response Schema:**
```json
{
  "total_users": 156,
  "active_users": 142,
  "users_by_admin_type": {
    "system_admin": 2,
    "stab_admin": 8,
    "regular": 146
  },
  "users_by_starting_year": {
    "2021": 35,
    "2022": 38,
    "2023": 42,
    "2024": 28,
    "2025": 13
  },
  "users_with_radio": 45,
  "production_managers": 6,
  "media_teachers": 8
}
```

### 6. Class Statistics

#### `GET /api/user-import/classes-status`

Get class-related statistics.

**Response Schema:**
```json
{
  "total_classes": 24,
  "classes_by_year": {
    "2021F": 6,
    "2022F": 6,
    "2023F": 6,
    "2024F": 6
  },
  "classes_with_teachers": 18,
  "classes_without_teachers": 6,
  "total_class_teachers": 12
}
```

### 7. Stab Statistics

#### `GET /api/user-import/stabs-status`

Get stab-related statistics.

**Response Schema:**
```json
{
  "total_stabs": 12,
  "total_radio_stabs": 8,
  "stab_membership": {
    "A stáb": 25,
    "B stáb": 28,
    "C stáb": 22,
    "grafikus": 18,
    "hangstab": 15
  },
  "radio_stab_membership": {
    "A1": 8,
    "A2": 6,
    "B3": 7,
    "B4": 9
  },
  "users_without_stab": 15
}
```

---

## Error Handling

### Common Error Responses

**400 Bad Request:**
```json
{
  "message": "Csak CSV (.csv) fájlok támogatottak"
}
```

**401 Unauthorized:**
```json
{
  "message": "Nincs jogosultság a művelet végrehajtásához. Csak rendszergazdák használhatják ezt a funkciót."
}
```

### Validation Errors

When CSV parsing fails, detailed error information is provided:

```json
{
  "success": false,
  "message": "CSV parsing failed",
  "errors": [
    "2. sor: Email cím hiányzik",
    "5. sor: Érvénytelen email formátum: 'invalid-email'",
    "8. sor: Ismeretlen stáb: 'Unknown Stab'"
  ],
  "warnings": [
    "3. sor: Telefonszám hiányzik",
    "6. sor: Kezdés éve nincs megadva, alapértelmezett: 2024"
  ]
}
```

---

## Usage Examples

### Complete Import Workflow

1. **Upload CSV for preview:**
```bash
curl -X POST "http://localhost:8000/api/user-import/import-csv-preview" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@users.csv"
```

2. **Review the response and validate data**

3. **Import validated data:**
```bash
curl -X POST "http://localhost:8000/api/user-import/import-validated-data" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "users": [
      {
        "vezetek_nev": "Nagy",
        "kereszt_nev": "Imre",
        "email": "nagy.imre.25f@szlgbp.hu",
        "telefonszam": "+36301234567",
        "stab": "B stáb",
        "kezdes_eve": 2025,
        "tagozat": "F",
        "radio": null,
        "gyartasvezeto": false,
        "mediatana": false,
        "osztalyfonok": false,
        "osztalyai": []
      }
    ]
  }'
```

### Get System Status

```bash
curl -X GET "http://localhost:8000/api/user-import/system-overview" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Notes

- All endpoints require JWT authentication
- Only system administrators can access these endpoints
- CSV files are processed with UTF-8 encoding support
- Hungarian characters are fully supported
- Multiple delimiters are automatically detected
- Detailed validation prevents data corruption
- Model preview shows exactly what will be created before import

## Supported Formats

- **File Types:** `.csv`
- **Encodings:** UTF-8, UTF-8 with BOM
- **Delimiters:** Comma (`,`), Semicolon (`;`), Tab (`\t`)
- **Boolean Values:** `Igen`/`Nem`, `igen`/`nem`, `true`/`false`, or empty
- **Multiple Values:** Semicolon-separated (e.g., `9.A;9.B;10.C`)
