"""
Regia application runner.
"""

import uvicorn
from app.config import load_config


def main():
    settings = load_config()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
