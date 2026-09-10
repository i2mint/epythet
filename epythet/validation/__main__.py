"""``python -m epythet.validation``: the validate command on its own."""

import cw

from epythet.validation.cli import validate

if __name__ == "__main__":
    raise SystemExit(cw.dispatch(validate, prog="epythet-validate"))
