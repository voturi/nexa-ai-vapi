"""Create a sample tenant for testing."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import AsyncSessionLocal
from app.services.tenant_service import TenantService
from app.schemas.tenant import TenantCreate


async def create_sample_tenant():
    """Create a sample tenant."""
    print("🔧 Creating sample tenant...\n")

    if not AsyncSessionLocal:
        print("❌ Database not configured")
        return

    async with AsyncSessionLocal() as db:
        service = TenantService(db)

        # Create Mike's Plumbing - with structured fields
        tenant_data = TenantCreate(
            business_name="Mike's Plumbing Services",
            vertical="tradies",
            phone="+61400123456",
            email="mike@plumbing.com.au",
            timezone="Australia/Sydney",
            operating_hours={
                "monday": {"open": "07:00", "close": "18:00"},
                "tuesday": {"open": "07:00", "close": "18:00"},
                "wednesday": {"open": "07:00", "close": "18:00"},
                "thursday": {"open": "07:00", "close": "18:00"},
                "friday": {"open": "07:00", "close": "18:00"},
                "saturday": {"open": "08:00", "close": "14:00"},
                "sunday": None
            },
            services=[
                {
                    "id": "emergency_plumbing",
                    "name": "Emergency Plumbing",
                    "duration_minutes": 120,
                    "price": "$200-500",
                    "description": "24/7 emergency plumbing service"
                },
                {
                    "id": "routine_maintenance",
                    "name": "Routine Maintenance",
                    "duration_minutes": 60,
                    "price": "$150-300",
                    "description": "Regular plumbing maintenance and inspection"
                },
                {
                    "id": "bathroom_renovation",
                    "name": "Bathroom Renovation",
                    "duration_minutes": 240,
                    "price": "$500-2000",
                    "description": "Full bathroom plumbing installation"
                }
            ],
            booking_rules={
                "min_notice_hours": 2,
                "max_advance_days": 90,
                "allow_same_day": True,
                "require_deposit": False,
                "cancellation_notice_hours": 24
            },
            ai_behavior={
                "personality": "friendly_professional",
                "qualification_strictness": "medium",
                "upsell_enabled": True
            },
            config={
                "notes": "Sample tenant for testing",
                "demo": True
            }
        )

        tenant = await service.create(tenant_data)

        print("✅ Sample tenant created successfully!")
        print(f"\n{'='*60}")
        print(f"ID:              {tenant.id}")
        print(f"Business Name:   {tenant.business_name}")
        print(f"Vertical:        {tenant.vertical}")
        print(f"Phone:           {tenant.phone}")
        print(f"Email:           {tenant.email}")
        print(f"Timezone:        {tenant.timezone}")
        print(f"Status:          {tenant.subscription_status}")
        print(f"Active:          {tenant.is_active}")
        print(f"\n📊 Services:     {len(tenant.services) if tenant.services else 0} services")
        if tenant.services:
            for svc in tenant.services:
                print(f"   - {svc['name']} ({svc['duration_minutes']} min)")
        print(f"\n⏰ Operating:    Mon-Fri 7am-6pm, Sat 8am-2pm")
        print(f"\n🔑 API Key:      {tenant.api_key}")
        print(f"🔐 Secret:       {tenant.webhook_secret}")
        print(f"{'='*60}")
        print(f"\n💡 Use this API key to test authenticated endpoints:")
        print(f"   Authorization: Bearer {tenant.api_key}")
        print(f"\n🌐 Test the endpoint:")
        print(f"   curl http://localhost:8000/api/v1/tenants")

if __name__ == "__main__":
    asyncio.run(create_sample_tenant())
