"""Single import point for the metadata.

Imports ``Base`` and all models so they get registered in ``Base.metadata``.
Used by ``create_all`` (seed) and Alembic (autogenerate).
"""

from app.db.base_class import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.company import Company  # noqa: F401
from app.models.employee import Employee  # noqa: F401
from app.models.contract import Contract  # noqa: F401
from app.models.incident import Incident  # noqa: F401
from app.models.payroll import Payroll, PayrollDetail  # noqa: F401
