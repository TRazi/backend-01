import environ
from pathlib import Path

env = environ.Env()


# Build paths - pointing to the backend directory (where manage.py is)
BASE_DIR = Path(__file__).resolve().parent.parent
