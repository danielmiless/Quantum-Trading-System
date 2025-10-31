"""Re-export the full desktop UI entry point."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

# Ensure repository paths are available when running from source checkout
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
for candidate in (_ROOT, _SRC):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

# Load environment variables from project .env if present
load_dotenv(_ROOT / ".env", override=False)

from ui.main import main as launch_ui  # noqa: E402  (import after sys.path setup)


def main(argv: Sequence[str] | None = None) -> int:
    """Launch the full Quantum Portfolio Optimizer UI."""

    return launch_ui(list(argv) if argv is not None else None)


if __name__ == "__main__":  # pragma: no cover - manual invocation
    raise SystemExit(main())
