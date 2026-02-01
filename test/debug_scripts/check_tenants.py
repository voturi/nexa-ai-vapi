"""Check tenants in database."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant
from sqlalchemy import select


async def check_tenants():
    """Check all tenants in database."""
    print("🔍 Checking tenants in database...")
    
    if not AsyncSessionLocal:
        print("❌ Database not configured")
        return
    
    async with AsyncSessionLocal() as db:
        # Check all tenants (including deleted)
        result = await db.execute(select(Tenant))
        all_tenants = result.scalars().all()
        
        print(f"\n📊 Total tenants in database: {len(all_tenants)}")
        
        for tenant in all_tenants:
            print(f"\n{'='*60}")
            print(f"ID: {tenant.id}")
            print(f"Business: {tenant.business_name}")
            print(f"Vertical: {tenant.vertical}")
            print(f"Active: {tenant.is_active}")
            print(f"Deleted: {tenant.deleted_at is not None}")
            print(f"Created: {tenant.created_at}")
            if tenant.deleted_at:
                print(f"Deleted at: {tenant.deleted_at}")
            print(f"API Key: {tenant.api_key[:30]}...")

if __name__ == "__main__":
    asyncio.run(check_tenants())
