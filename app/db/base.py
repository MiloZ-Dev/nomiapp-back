"""Punto único de importación de la metadata.

Importa la ``Base`` y todos los modelos para que queden registrados en
``Base.metadata``. Lo usan ``create_all`` (seed) y Alembic (autogenerate).
"""

from app.db.base_class import Base  # noqa: F401
from app.models.usuario import Usuario  # noqa: F401
from app.models.empresa import Empresa  # noqa: F401
from app.models.empleado import Empleado  # noqa: F401
from app.models.contrato import Contrato  # noqa: F401
from app.models.nomina import Nomina, NominaDetalle  # noqa: F401
