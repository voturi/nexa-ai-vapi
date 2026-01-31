"""Quick startup test script."""
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))


def test_config():
    """Test configuration loading."""
    print("🔍 Testing configuration...")
    try:
        from app.core.config import settings
        print(f"   ✅ Config loaded")
        print(f"   - Environment: {settings.ENVIRONMENT}")
        print(f"   - Project: {settings.PROJECT_NAME}")
        print(f"   - Redis URL: {settings.REDIS_URL}")
        print(f"   - Database configured: {'Yes' if settings.DATABASE_URL else 'No'}")
        print(f"   - VAPI configured: {'Yes' if settings.VAPI_API_KEY else 'No'}")
        print(f"   - Twilio configured: {'Yes' if settings.TWILIO_ACCOUNT_SID else 'No'}")
        return True
    except Exception as e:
        print(f"   ❌ Config error: {e}")
        return False


def test_redis():
    """Test Redis connection."""
    print("\n🔍 Testing Redis connection...")
    try:
        import redis
        r = redis.Redis.from_url("redis://localhost:6379")
        r.ping()
        print("   ✅ Redis is running and accessible")
        return True
    except Exception as e:
        print(f"   ⚠️  Redis connection failed: {e}")
        print("   💡 Make sure Redis is running: brew services start redis")
        return False


def test_imports():
    """Test all critical imports."""
    print("\n🔍 Testing imports...")
    try:
        from app.main import app
        print("   ✅ FastAPI app imports successfully")

        from app.models.tenant import Tenant
        print("   ✅ Models import successfully")

        from app.services.skills_engine import skills_engine
        print("   ✅ Services import successfully")

        return True
    except Exception as e:
        print(f"   ❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_skills():
    """Test skills loading."""
    print("\n🔍 Testing skills system...")
    try:
        from app.services.skills_engine import skills_engine

        # Test loading core skills
        core_skills = skills_engine.get_core_skills()
        print(f"   ✅ Loaded {len(core_skills)} core skills")

        # Test loading vertical skills
        tradies_skills = skills_engine.get_skills_for_vertical("tradies")
        print(f"   ✅ Loaded {len(tradies_skills)} tradies skills")

        salon_skills = skills_engine.get_skills_for_vertical("hair_salon")
        print(f"   ✅ Loaded {len(salon_skills)} salon skills")

        return True
    except Exception as e:
        print(f"   ⚠️  Skills loading issue: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("🚀 Backend Startup Test")
    print("=" * 60)

    results = []

    results.append(("Configuration", test_config()))
    results.append(("Redis", test_redis()))
    results.append(("Imports", test_imports()))
    results.append(("Skills", test_skills()))

    print("\n" + "=" * 60)
    print("📊 Test Results")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    all_passed = all(result[1] for result in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! Ready to start the server:")
        print("   uvicorn app.main:app --reload")
    else:
        print("⚠️  Some tests failed. Check the issues above.")
        print("\n💡 Quick fixes:")
        print("   - Make sure .env file exists (cp .env.minimal .env)")
        print("   - Start Redis: brew services start redis")
        print("   - Check all required packages are installed")
    print("=" * 60)


if __name__ == "__main__":
    main()
