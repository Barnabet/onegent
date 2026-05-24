"""CLI: python scripts/serve.py  →  starts the FastAPI backend on :8000.

For the web UI, in a separate terminal:
    cd webui && npm run dev   # http://localhost:5173 (proxies /api to :8000)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn  # noqa: E402


def main() -> int:
    uvicorn.run("server.app:app", host="127.0.0.1", port=8000, reload=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
