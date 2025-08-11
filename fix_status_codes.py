#!/usr/bin/env python3
"""
Quick script to fix incorrect HTTP status codes in API endpoints.
This script will replace 401 errors that should be 403 (permission) or 500 (server error).
"""

import os
import re
from pathlib import Path

def fix_status_codes_in_file(file_path):
    """Fix status codes in a single file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Fix permission errors: change 401 to 403 when checking permissions
    pattern1 = r'if not has_permission:\s+return 401, {"message": error_message}'
    replacement1 = 'if not has_permission:\n                return 403, {"message": error_message}'
    content = re.sub(pattern1, replacement1, content)
    
    # Fix server errors: change 401 to 500 for Exception handling
    pattern2 = r'except Exception as e:\s+return 401, {"message": f"Error ([^"]+): {str\(e\)}"}'
    replacement2 = r'except Exception as e:\n            return 500, {"message": f"Error \1: {str(e)}"}'
    content = re.sub(pattern2, replacement2, content)
    
    # Fix response declarations to include proper status codes
    pattern3 = r'response=\{([^}]*), 401: ErrorSchema\}'
    def replace_response(match):
        existing = match.group(1)
        if '403: ErrorSchema' not in existing:
            existing += ', 403: ErrorSchema'
        if '500: ErrorSchema' not in existing:
            existing += ', 500: ErrorSchema'
        return f'response={{{existing}}}'
    
    content = re.sub(pattern3, replace_response, content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed: {file_path}")
        return True
    return False

def main():
    """Main function to fix all API module files."""
    api_modules_dir = Path("backend/api_modules")
    
    if not api_modules_dir.exists():
        print("API modules directory not found!")
        return
    
    fixed_files = 0
    for py_file in api_modules_dir.glob("*.py"):
        if fix_status_codes_in_file(py_file):
            fixed_files += 1
    
    print(f"\n✅ Fixed {fixed_files} files with incorrect status codes!")
    print("🔧 Key changes made:")
    print("   - Permission errors: 401 → 403")
    print("   - Server errors: 401 → 500")
    print("   - Updated response schemas")

if __name__ == "__main__":
    main()
