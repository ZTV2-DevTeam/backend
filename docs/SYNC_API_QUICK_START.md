# FTV Sync API - Quick Start Guide

## For Igazoláskezelő Developers

This guide helps you quickly integrate the FTV Sync API into Igazoláskezelő.

---

## 1. Get Your Access Token

Contact the FTV admin to get your external access token. It will look like:
```
your-secure-token-here-change-in-production
```

⚠️ **Keep this token secret!** It grants full read access to the FTV system.

---

## 2. Base Configuration

```javascript
const FTV_CONFIG = {
  baseUrl: 'https://ftvapi.szlg.info/api/sync',  // Production
  // baseUrl: 'http://localhost:8000/api/sync',  // Development
  token: 'YOUR_EXTERNAL_ACCESS_TOKEN'
};

const headers = {
  'Authorization': `Bearer ${FTV_CONFIG.token}`,
  'Content-Type': 'application/json'
};
```

---

## 3. Common Integration Patterns

### Pattern 1: Find User by Email

```javascript
async function findFTVUser(email) {
  try {
    const response = await fetch(
      `${FTV_CONFIG.baseUrl}/profile/${encodeURIComponent(email)}`,
      { headers }
    );
    
    if (!response.ok) {
      if (response.status === 404) {
        console.log(`User not found in FTV: ${email}`);
        return null;
      }
      throw new Error(`API Error: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error finding FTV user:', error);
    return null;
  }
}

// Usage
const user = await findFTVUser('kovacs.janos@szlg.info');
if (user) {
  console.log(`Found: ${user.full_name} (ID: ${user.user_id})`);
}
```

### Pattern 2: Sync User Absences

```javascript
async function syncUserAbsences(email) {
  // 1. Find user in FTV
  const ftvUser = await findFTVUser(email);
  if (!ftvUser) {
    return { success: false, message: 'User not found in FTV' };
  }
  
  // 2. Get all absences for this user
  const response = await fetch(
    `${FTV_CONFIG.baseUrl}/hianyzasok/user/${ftvUser.user_id}`,
    { headers }
  );
  
  if (!response.ok) {
    return { success: false, message: `API Error: ${response.status}` };
  }
  
  const absences = await response.json();
  
  // 3. Process each absence
  let syncedCount = 0;
  for (const absence of absences) {
    // Your logic to save/update in Igazoláskezelő database
    await saveAbsenceToDatabase(absence, email);
    syncedCount++;
  }
  
  return {
    success: true,
    syncedCount,
    totalAbsences: absences.length
  };
}

// Usage
const result = await syncUserAbsences('kovacs.janos@szlg.info');
console.log(`Synced ${result.syncedCount} absences`);
```

### Pattern 3: Sync Entire Class

```javascript
async function syncClassAbsences(osztaly_id) {
  const response = await fetch(
    `${FTV_CONFIG.baseUrl}/hianyzasok/osztaly/${osztaly_id}`,
    { headers }
  );
  
  if (!response.ok) {
    throw new Error(`Failed to get class absences: ${response.status}`);
  }
  
  const absences = await response.json();
  
  // Group by student email
  const byStudent = {};
  for (const absence of absences) {
    const email = absence.diak_email;
    if (!byStudent[email]) {
      byStudent[email] = [];
    }
    byStudent[email].push(absence);
  }
  
  // Sync each student
  const results = {
    total: Object.keys(byStudent).length,
    synced: 0,
    failed: 0
  };
  
  for (const [email, studentAbsences] of Object.entries(byStudent)) {
    try {
      // Your logic to save/update in database
      await saveStudentAbsences(email, studentAbsences);
      results.synced++;
    } catch (error) {
      console.error(`Failed to sync ${email}:`, error);
      results.failed++;
    }
  }
  
  return results;
}

// Usage
const result = await syncClassAbsences(1);  // Sync class ID 1
console.log(`Synced ${result.synced}/${result.total} students`);
```

---

## 4. Understanding Absence Data

### Key Fields

```javascript
const absence = {
  // Student info (use email as common key)
  diak_email: "kovacs.janos@szlg.info",  // ⭐ PRIMARY KEY
  diak_full_name: "Kovács János",
  
  // Absence timing
  date: "2024-10-30",
  timeFrom: "10:00:00",
  timeTo: "12:00:00",
  
  // Status
  excused: false,        // Igazolt
  unexcused: false,      // Igazolatlan
  
  // Extra time (student-submitted)
  student_extra_time_before: 15,  // Minutes before
  student_extra_time_after: 30,   // Minutes after
  student_edit_note: "Preparation and post-work needed",
  
  // Affected class periods
  affected_classes: [3, 4],  // 3rd and 4th period
  
  // Related filming session
  forgatas_details: {
    name: "Iskolai KaCsa forgatás",
    location_name: "SZLG Stúdió"
  }
};
```

### Affected Classes Mapping

```javascript
const CLASS_PERIODS = {
  0: { start: '07:30', end: '08:15', name: '0. óra' },
  1: { start: '08:25', end: '09:10', name: '1. óra' },
  2: { start: '09:20', end: '10:05', name: '2. óra' },
  3: { start: '10:20', end: '11:05', name: '3. óra' },
  4: { start: '11:15', end: '12:00', name: '4. óra' },
  5: { start: '12:20', end: '13:05', name: '5. óra' },
  6: { start: '13:25', end: '14:10', name: '6. óra' },
  7: { start: '14:20', end: '15:05', name: '7. óra' },
  8: { start: '15:15', end: '16:00', name: '8. óra' }
};

function formatAffectedClasses(affected_classes) {
  return affected_classes
    .map(period => CLASS_PERIODS[period].name)
    .join(', ');
}
```

---

## 5. Error Handling Best Practices

```javascript
async function safeFTVRequest(endpoint) {
  const maxRetries = 3;
  let lastError;
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(
        `${FTV_CONFIG.baseUrl}${endpoint}`,
        {
          headers,
          timeout: 10000  // 10 second timeout
        }
      );
      
      // Handle specific status codes
      if (response.status === 401) {
        throw new Error('Invalid access token - contact FTV admin');
      }
      
      if (response.status === 404) {
        return null;  // Resource not found
      }
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      return await response.json();
      
    } catch (error) {
      lastError = error;
      console.warn(`Attempt ${attempt}/${maxRetries} failed:`, error.message);
      
      if (attempt < maxRetries) {
        // Wait before retry (exponential backoff)
        await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
      }
    }
  }
  
  throw new Error(`Failed after ${maxRetries} attempts: ${lastError.message}`);
}

// Usage
try {
  const data = await safeFTVRequest('/osztalyok');
  console.log(`Got ${data.length} classes`);
} catch (error) {
  console.error('Fatal error:', error);
  // Handle error appropriately in your app
}
```

---

## 6. Caching Strategy

```javascript
class FTVCache {
  constructor(ttlMinutes = 60) {
    this.cache = new Map();
    this.ttl = ttlMinutes * 60 * 1000;  // Convert to ms
  }
  
  get(key) {
    const item = this.cache.get(key);
    if (!item) return null;
    
    if (Date.now() > item.expiry) {
      this.cache.delete(key);
      return null;
    }
    
    return item.data;
  }
  
  set(key, data) {
    this.cache.set(key, {
      data,
      expiry: Date.now() + this.ttl
    });
  }
  
  clear() {
    this.cache.clear();
  }
}

// Usage
const ftvCache = new FTVCache(60);  // 60 minute TTL

async function getCachedProfile(email) {
  const cacheKey = `profile:${email}`;
  
  // Check cache first
  let profile = ftvCache.get(cacheKey);
  if (profile) {
    console.log('Cache hit:', email);
    return profile;
  }
  
  // Fetch from API
  console.log('Cache miss, fetching:', email);
  profile = await findFTVUser(email);
  
  // Cache the result
  if (profile) {
    ftvCache.set(cacheKey, profile);
  }
  
  return profile;
}
```

---

## 7. Complete Integration Example

```javascript
class IgazolaskezeroFTVSync {
  constructor(config) {
    this.config = config;
    this.cache = new FTVCache(60);
  }
  
  async syncUser(email) {
    console.log(`[FTV Sync] Starting sync for ${email}`);
    
    try {
      // 1. Get FTV user profile
      const profile = await this.getFTVProfile(email);
      if (!profile) {
        return {
          success: false,
          message: 'User not found in FTV system'
        };
      }
      
      // 2. Get user absences from FTV
      const absences = await this.getFTVAbsences(profile.user_id);
      
      // 3. Sync to local database
      await this.saveToLocalDB(email, profile, absences);
      
      console.log(`[FTV Sync] Success: ${absences.length} absences synced`);
      
      return {
        success: true,
        profile,
        absenceCount: absences.length
      };
      
    } catch (error) {
      console.error(`[FTV Sync] Error:`, error);
      return {
        success: false,
        message: error.message
      };
    }
  }
  
  async getFTVProfile(email) {
    const cacheKey = `profile:${email}`;
    let profile = this.cache.get(cacheKey);
    
    if (!profile) {
      const response = await fetch(
        `${this.config.baseUrl}/profile/${encodeURIComponent(email)}`,
        { headers: this.getHeaders() }
      );
      
      if (response.status === 404) return null;
      if (!response.ok) throw new Error(`API Error: ${response.status}`);
      
      profile = await response.json();
      this.cache.set(cacheKey, profile);
    }
    
    return profile;
  }
  
  async getFTVAbsences(userId) {
    const response = await fetch(
      `${this.config.baseUrl}/hianyzasok/user/${userId}`,
      { headers: this.getHeaders() }
    );
    
    if (!response.ok) {
      throw new Error(`Failed to get absences: ${response.status}`);
    }
    
    return await response.json();
  }
  
  async saveToLocalDB(email, profile, absences) {
    // Your implementation here
    // Save profile and absences to Igazoláskezelő database
    
    // Example structure:
    for (const absence of absences) {
      await db.absences.upsert({
        where: {
          ftv_id: absence.id
        },
        data: {
          user_email: email,
          date: absence.date,
          time_from: absence.timeFrom,
          time_to: absence.timeTo,
          excused: absence.excused,
          affected_periods: absence.affected_classes,
          ftv_id: absence.id,
          last_synced: new Date()
        }
      });
    }
  }
  
  getHeaders() {
    return {
      'Authorization': `Bearer ${this.config.token}`,
      'Content-Type': 'application/json'
    };
  }
}

// Initialize
const ftvSync = new IgazolaskezeroFTVSync({
  baseUrl: 'https://ftvapi.szlg.info/api/sync',
  token: 'YOUR_EXTERNAL_ACCESS_TOKEN'
});

// Use it
const result = await ftvSync.syncUser('kovacs.janos@szlg.info');
if (result.success) {
  console.log(`Synced ${result.absenceCount} absences for ${result.profile.full_name}`);
} else {
  console.error(`Sync failed: ${result.message}`);
}
```

---

## 8. Testing Checklist

- [ ] Test with valid token
- [ ] Test with invalid token (should get 401)
- [ ] Test profile lookup with existing email
- [ ] Test profile lookup with non-existent email (should get 404)
- [ ] Test getting absences for user with absences
- [ ] Test getting absences for user without absences (should get empty array)
- [ ] Test getting absences for non-existent class (should get 404)
- [ ] Test network error handling (disconnect network)
- [ ] Test timeout handling (slow connection)
- [ ] Verify email matching works correctly
- [ ] Verify affected_classes array is correct
- [ ] Verify date/time formats are parsed correctly

---

## 9. Production Deployment

### Environment Configuration

```javascript
// config/production.js
module.exports = {
  ftv: {
    baseUrl: process.env.FTV_API_URL || 'https://ftvapi.szlg.info/api/sync',
    token: process.env.FTV_ACCESS_TOKEN,  // ⚠️ Never commit this!
    cacheTTL: 60,  // minutes
    timeout: 10000,  // ms
    maxRetries: 3
  }
};
```

### Security Checklist

- [ ] Token stored in environment variables (not in code)
- [ ] Token never logged or exposed in error messages
- [ ] HTTPS used in production
- [ ] Request timeout configured
- [ ] Rate limiting implemented (if needed)
- [ ] Error messages don't leak sensitive info
- [ ] API calls logged for audit trail

---

## 10. Support

### Getting Help

1. **Check the full documentation**: `SYNC_API_DOCUMENTATION.md`
2. **Test in browser**: Visit `https://ftvapi.szlg.info/api/docs`
3. **Check logs**: Look for API errors in console
4. **Contact FTV team**: For token issues or API problems

### Common Issues

**Issue**: 401 Unauthorized  
**Solution**: Check your token is correct and matches local_settings.py

**Issue**: 404 Not Found  
**Solution**: User/resource doesn't exist in FTV, handle gracefully

**Issue**: Connection timeout  
**Solution**: Check network, increase timeout, implement retry logic

**Issue**: Email not found  
**Solution**: User might not exist in FTV, verify email is correct

---

**Quick Start Version**: 1.0  
**Last Updated**: October 29, 2024
