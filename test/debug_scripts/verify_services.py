"""Verify services are in database."""
import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant
from sqlalchemy import select


async def verify_services():
    """Check if services are properly stored."""
    print("🔍 Verifying services in database...\n")

    async with AsyncSessionLocal() as db:
        # Get latest active tenant
        result = await db.execute(
            select(Tenant)
            .where(Tenant.is_active == True, Tenant.deleted_at.is_(None))
            .order_by(Tenant.created_at.desc())
            .limit(1)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            print("❌ No active tenant found")
            return

        print(f"✅ Found tenant: {tenant.business_name}")
        print(f"   ID: {tenant.id}\n")

        print("📊 Services Column:")
        if tenant.services:
            print(f"   ✅ {len(tenant.services)} services found:")
            for svc in tenant.services:
                print(f"      - {svc.get('name')} ({svc.get('duration_minutes')} min)")
                print(f"        Price: {svc.get('price')}")
        else:
            print("   ❌ No services in services column")

        print(f"\n⏰ Operating Hours Column:")
        if tenant.operating_hours:
            print(f"   ✅ Operating hours set")
            for day, hours in tenant.operating_hours.items():
                if hours:
                    print(f"      {day}: {hours.get('open')} - {hours.get('close')}")
        else:
            print("   ❌ No operating hours")

        print(f"\n📋 Booking Rules Column:")
        if tenant.booking_rules:
            print(f"   ✅ Booking rules set:")
            for key, value in tenant.booking_rules.items():
                print(f"      {key}: {value}")
        else:
            print("   ❌ No booking rules")

        print(f"\n🤖 AI Behavior Column:")
        if tenant.ai_behavior:
            print(f"   ✅ AI behavior set:")
            for key, value in tenant.ai_behavior.items():
                print(f"      {key}: {value}")
        else:
            print("   ❌ No AI behavior")

        print(f"\n⚙️  Config Column:")
        if tenant.config:
            print(f"   ✅ Config set: {json.dumps(tenant.config, indent=2)}")
        else:
            print("   ❌ No config")

if __name__ == "__main__":
    asyncio.run(verify_services())
