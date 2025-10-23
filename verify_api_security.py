#!/usr/bin/env python3.9
"""
API Security Verification Script
=================================

Run this script before pushing to GitHub to verify:
1. api_secrets.py exists and is configured
2. All imports work correctly
3. No hardcoded secrets remain in code
4. .gitignore is protecting sensitive files
"""

import sys
import os
import subprocess
from pathlib import Path


def check_api_secrets_exists():
    """Verify api_secrets.py file exists"""
    print("1️⃣  Checking if api_secrets.py exists...")
    
    if Path("api_secrets.py").exists():
        print("   ✅ api_secrets.py found")
        return True
    else:
        print("   ❌ api_secrets.py NOT found!")
        print("   → Copy api_secrets.example.py to api_secrets.py")
        return False


def check_api_secrets_configured():
    """Verify api_secrets.py is properly configured"""
    print("\n2️⃣  Checking if api_secrets.py is configured...")
    
    try:
        from api_secrets import MATCH_DATA_CONFIG, ODDS_PROVIDER_CONFIG
        
        # Check MatchDataProvider config
        if not MATCH_DATA_CONFIG.get('headers'):
            print("   ⚠️  MatchDataProvider headers are empty")
            return False
        
        # Check OddsProvider config
        user_id = ODDS_PROVIDER_CONFIG.get('user_id')
        if not user_id or user_id == 'YOUR_USER_ID':
            print("   ⚠️  OddsProvider user_id not configured")
            return False
        
        print("   ✅ API secrets are configured")
        return True
        
    except ImportError as e:
        print(f"   ❌ Error importing api_secrets: {e}")
        return False


def check_services_import():
    """Verify services can import api_secrets"""
    print("\n3️⃣  Checking if services import correctly...")
    
    try:
        from app.services.match_data_service import MatchDataProviderService
        from app.services.player_analysis_service import PlayerAnalysisService
        
        # Check if they're using api_secrets
        service = MatchDataProviderService()
        if service.BASE_URL:
            print(f"   ✅ MatchDataProviderService configured (base URL: {service.BASE_URL})")
        
        player_service = PlayerAnalysisService()
        if player_service.BASE_URL:
            print(f"   ✅ PlayerAnalysisService configured")
        
        return True
        
    except ImportError as e:
        print(f"   ❌ Error importing services: {e}")
        return False


def check_gitignore_protection():
    """Verify .gitignore is protecting sensitive files"""
    print("\n4️⃣  Checking .gitignore protection...")
    
    try:
        # Check if api_secrets.py is in git
        result = subprocess.run(
            ["git", "ls-files", "api_secrets.py"],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            print("   ❌ api_secrets.py is tracked by git!")
            print("   → Run: git rm --cached api_secrets.py")
            return False
        else:
            print("   ✅ api_secrets.py is NOT tracked by git")
        
        # Check if CSV files are tracked
        result = subprocess.run(
            ["git", "ls-files", "*.csv"],
            capture_output=True,
            text=True
        )
        
        csv_files = [f for f in result.stdout.strip().split('\n') if f and 'tennis_predictions' in f]
        if csv_files:
            print(f"   ⚠️  Prediction CSV files are tracked: {csv_files}")
            return False
        else:
            print("   ✅ Prediction CSV files are NOT tracked")
        
        return True
        
    except subprocess.CalledProcessError:
        print("   ⚠️  Not a git repository or git not available")
        return True  # Don't fail if not in git repo


def check_no_hardcoded_secrets():
    """Search for hardcoded secrets in Python files"""
    print("\n5️⃣  Checking for hardcoded secrets in code...")
    
    # Patterns to search for (abstracted to avoid leaking examples)
    # Load actual patterns from api_secrets if available
    try:
        from api_secrets import ODDS_PROVIDER_CONFIG
        user_id_pattern = ODDS_PROVIDER_CONFIG.get('user_id', '')[:10] if ODDS_PROVIDER_CONFIG.get('user_id') else ''
    except:
        user_id_pattern = ''
    
    patterns = [
        user_id_pattern,  # OddsProvider user ID pattern (if configured)
        "sentry-release=",  # Generic sentry pattern
    ]
    
    # Filter out empty patterns
    patterns = [p for p in patterns if p]
    
    issues = []
    
    for pattern in patterns:
        try:
            result = subprocess.run(
                ["grep", "-r", pattern, ".", 
                 "--exclude-dir=.venv", 
                 "--exclude-dir=.git",
                 "--exclude-dir=archive",  # Exclude archived files (already gitignored)
                 "--exclude-dir=node_modules",
                 "--exclude=api_secrets.py",
                 "--exclude=*_odds_provider*.py",  # Exclude test files (gitignored)
                 "--exclude=dump_*.py",  # Exclude dump utilities (gitignored)
                 "--include=*.py"],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                matches = result.stdout.strip().split('\n')
                # Filter out safe files (api_secrets, verify script, test/utils)
                dangerous = [m for m in matches if 
                           'api_secrets' not in m and 
                           'verify_api' not in m and
                           '/tests/' not in m and
                           '/utils/' not in m]
                if dangerous:
                    issues.extend(dangerous)
        except:
            pass
    
    if issues:
        print(f"   ⚠️  Found potential hardcoded secrets:")
        for issue in issues[:5]:  # Show first 5
            print(f"      {issue}")
        return False
    else:
        print("   ✅ No hardcoded secrets found")
        return True


def check_example_file_exists():
    """Verify api_secrets.example.py exists"""
    print("\n6️⃣  Checking if api_secrets.example.py exists...")
    
    if Path("api_secrets.example.py").exists():
        print("   ✅ api_secrets.example.py found (safe to commit)")
        return True
    else:
        print("   ⚠️  api_secrets.example.py NOT found")
        return False


def main():
    """Run all verification checks"""
    print("=" * 70)
    print("🔐 API Security Verification")
    print("=" * 70)
    
    checks = [
        check_api_secrets_exists(),
        check_api_secrets_configured(),
        check_services_import(),
        check_gitignore_protection(),
        check_no_hardcoded_secrets(),
        check_example_file_exists(),
    ]
    
    print("\n" + "=" * 70)
    
    if all(checks):
        print("✅ ALL CHECKS PASSED - Safe to push to GitHub!")
        print("=" * 70)
        print("\n📝 Next steps:")
        print("   1. Run: git status")
        print("   2. Verify no sensitive files appear")
        print("   3. Run: git add .")
        print("   4. Run: git commit -m 'Your message'")
        print("   5. Run: git push")
        return 0
    else:
        print("❌ SOME CHECKS FAILED - DO NOT push to GitHub yet!")
        print("=" * 70)
        print("\n🔧 Fix the issues above before pushing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

