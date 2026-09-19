"""BaseX client and DDI querying/reporting scaffolding for DDI-C and DDI-L (Experimental Extension)."""

from dartfx.ddi.basex.client import (
    BaseXAuthError,
    BaseXClient,
    BaseXConfig,
    BaseXConnectionError,
    BaseXError,
    BaseXNotFoundError,
    BaseXQueryError,
)
from dartfx.ddi.basex.queries import (
    BaseDdiQueryManager,
    DdiCodebookQueryManager,
    DdiLifecycle3QueryManager,
    DdiLifecycle4QueryManager,
    DdiLifecycleQueryManager,
)
from dartfx.ddi.basex.reporter import (
    BaseXReporter,
    ReportFormat,
)

__all__ = [
    "BaseDdiQueryManager",
    "BaseXAuthError",
    "BaseXClient",
    "BaseXConfig",
    "BaseXConnectionError",
    "BaseXError",
    "BaseXNotFoundError",
    "BaseXQueryError",
    "BaseXReporter",
    "DdiCodebookQueryManager",
    "DdiLifecycle3QueryManager",
    "DdiLifecycle4QueryManager",
    "DdiLifecycleQueryManager",
    "ReportFormat",
]
