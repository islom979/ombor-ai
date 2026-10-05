"""Supabase bazasiga migratsiyalarni (va ixtiyoriy seed'ni) qo'llash.

    cd backend
    python -m scripts.apply_migrations           # faqat migratsiyalar
    python -m scripts.apply_migrations --seed    # + demo ma'lumotnomalar

DATABASE_URL backend/.env dan olinadi. Skriptlar idempotent — qayta ishga tushirish xavfsiz.
"""

import argparse
import asyncio
from pathlib import Path

import asyncpg

from app.core.config import get_settings

DATABASE_DIR = Path(__file__).resolve().parents[2] / "database"


def plain_dsn(url: str) -> str:
    """SQLAlchemy DSN'ini asyncpg tushunadigan ko'rinishga keltiradi."""
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def main(seed: bool) -> None:
    files = sorted((DATABASE_DIR / "migrations").glob("*.sql"))
    if seed:
        files.append(DATABASE_DIR / "seed" / "seed.sql")

    settings = get_settings()
    connection = await asyncpg.connect(plain_dsn(settings.database_url), statement_cache_size=0)
    try:
        version = await connection.fetchval("select version()")
        print(f"Ulandi: {version.split(',')[0]}")
        for path in files:
            await connection.execute(path.read_text(encoding="utf-8"))
            print(f"  ✓ {path.relative_to(DATABASE_DIR)}")
        tables = await connection.fetchval(
            "select count(*) from information_schema.tables where table_schema = 'public'"
        )
        print(f"Tayyor: public sxemasida {tables} ta jadval.")
    finally:
        await connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", action="store_true", help="demo ma'lumotnomalarni ham qo'shish")
    asyncio.run(main(parser.parse_args().seed))
