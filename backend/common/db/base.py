from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import BigInteger
from sqlalchemy.types import TypeDecorator, Integer

Base = declarative_base()


class BigIntegerType(TypeDecorator):
    """A type that maps to BigInteger on PostgreSQL/MySQL and Integer on SQLite."""

    impl = Integer
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name in ("postgresql", "mysql"):
            return dialect.type_descriptor(BigInteger())
        else:
            return dialect.type_descriptor(Integer())
