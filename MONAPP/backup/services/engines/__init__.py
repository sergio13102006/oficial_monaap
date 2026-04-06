from backup.constants import DB_ENGINE_POSTGRES, DB_ENGINE_SQLITE

from .media_engine import MediaBackupEngine
from .postgres_engine import PostgresBackupEngine
from .sqlite_engine import SQLiteBackupEngine


DATABASE_ENGINES = {
    DB_ENGINE_SQLITE: SQLiteBackupEngine(),
    DB_ENGINE_POSTGRES: PostgresBackupEngine(),
}
media_engine = MediaBackupEngine()


def get_database_engine(engine_name):
    return DATABASE_ENGINES[engine_name]


def get_current_database_engine():
    for engine in DATABASE_ENGINES.values():
        if engine.supports_current_database():
            return engine
    raise RuntimeError("No hay engine compatible con la base de datos actual.")
