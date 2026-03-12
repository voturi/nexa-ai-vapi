"""Database models — import all so SQLAlchemy FK resolution works correctly."""
from app.models.tenant import Tenant  # noqa: F401 — must be first (other tables FK to it)
from app.models.call import Call  # noqa: F401
from app.models.booking import Booking  # noqa: F401
from app.models.lead import Lead  # noqa: F401
from app.models.integration import TenantIntegration  # noqa: F401
