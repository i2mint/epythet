"""``epythet validate``: tiered documentation validation with a growing artifact ledger.

Levels 0 (lint and coverage), 0.5 (parse), 1 (build), 2 (render) and 3
(review packet) live here. The ledger of known rendering artifacts is under
``epythet/ledger/rules`` (one YAML per rule with a sibling ``.py`` fixture);
observations from real runs are appended outside the repository, and rules a
reviewer proposes go to an overlay there too (``epythet ledger propose``).

>>> from epythet.validation import validate  # doctest: +SKIP
>>> report = validate("path/to/project", level=1)  # doctest: +SKIP
>>> report.exit_code()  # doctest: +SKIP
0
"""

from epythet.validation.model import (  # noqa: F401
    EXIT_FOR_LEVEL,
    EXIT_INTERNAL,
    EXIT_LEDGER,
    EXIT_OK,
    LEVELS,
    Finding,
    Report,
)
from epythet.validation.ledger import Ledger, LedgerError, load_ledger  # noqa: F401
from epythet.validation.core import resolve_package, validate  # noqa: F401
from epythet.validation.render import render  # noqa: F401
from epythet.validation.propose import propose  # noqa: F401
