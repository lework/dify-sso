from sqlalchemy.orm import declarative_base

from .engine import metadata

Base = declarative_base(metadata=metadata)