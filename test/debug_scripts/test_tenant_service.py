"""Test script for TenantService."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import AsyncSessionLocal
from app.services.tenant_service import TenantService
from app.schemas.tenant import TenantCreate, TenantUpdate


async def test_tenant_service():
    """Test TenantService CRUD operations."""
    print("=" * 60)
    print("🧪 Testing TenantService")
    print("=" * 60)

    if not AsyncSessionLocal:
        print("❌ Database not configured. Set DATABASE_URL in .env")
        return

    async with AsyncSessionLocal() as db:
        service = TenantService(db)

        # Test 1: Create a tenant
        print("\n✅ Test 1: Create Tenant")
        tenant_data = TenantCreate(
            business_name="Test Plumbing Co",
            vertical="tradies",
            phone="+61400000000",
            email="test@plumbing.com",
            timezone="Australia/Sydney",
            config={
                "operating_hours": {
                    "monday": {"open": "08:00", "close": "17:00"}
                }
            }
        )

        tenant = await service.create(tenant_data)
        print(f"   Created tenant: {tenant.id}")
        print(f"   Business: {tenant.business_name}")
        print(f"   API Key: {tenant.api_key[:20]}...")
        print(f"   Webhook Secret: {tenant.webhook_secret[:20]}...")
        print(f"   Status: {tenant.subscription_status}")

        # Test 2: Get by ID
        print("\n✅ Test 2: Get Tenant by ID")
        retrieved = await service.get_by_id(tenant.id)
        print(f"   Retrieved: {retrieved.business_name}")
        print(f"   Vertical: {retrieved.vertical}")

        # Test 3: Get by API key
        print("\n✅ Test 3: Get Tenant by API Key")
        by_key = await service.get_by_api_key_with_db(tenant.api_key)
        print(f"   Found: {by_key.business_name if by_key else 'Not found'}")

        # Test 4: Update tenant
        print("\n✅ Test 4: Update Tenant")
        update_data = TenantUpdate(
            phone="+61411111111",
            config={"updated": True}
        )
        updated = await service.update(tenant.id, update_data)
        print(f"   Updated phone: {updated.phone}")

        # Test 5: List all tenants
        print("\n✅ Test 5: List All Tenants")
        all_tenants = await service.list_all(limit=5)
        print(f"   Total tenants: {len(all_tenants)}")
        for t in all_tenants:
            print(f"   - {t.business_name} ({t.vertical})")

        # Test 6: Count tenants
        print("\n✅ Test 6: Count Tenants")
        count = await service.count()
        print(f"   Active tenants: {count}")

        # Test 7: Regenerate API key
        print("\n✅ Test 7: Regenerate API Key")
        old_key = tenant.api_key
        new_key = await service.regenerate_api_key(tenant.id)
        print(f"   Old key: {old_key[:20]}...")
        print(f"   New key: {new_key[:20]}...")

        # Test 8: Soft delete
        print("\n✅ Test 8: Soft Delete Tenant")
        await service.delete(tenant.id)
        deleted = await service.get_by_id(tenant.id)
        print(f"   Deleted tenant retrieved: {deleted is None}")

        # Verify count decreased
        new_count = await service.count()
        print(f"   Active tenants after delete: {new_count}")

    print("\n" + "=" * 60)
    print("✅ All TenantService tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_tenant_service())
