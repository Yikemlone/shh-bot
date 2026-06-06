#!/usr/bin/env python3
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / "src" / ".env")

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("WEB_PORT", "8080"))
    host = os.getenv("WEB_HOST", "0.0.0.0")
    uvicorn.run("web.app:app", host=host, port=port, reload=True)
