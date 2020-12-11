import warnings

warnings.warn(
    "'from epythet.docs_gen import *' is deprecated. Use 'from epythet import *' instead",
    DeprecationWarning,
)

from epythet.setup_docsrc import make_docsrc
from epythet.autogen import make_autodocs
from epythet.call_make import make
