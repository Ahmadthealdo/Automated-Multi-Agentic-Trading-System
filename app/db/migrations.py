from sqlalchemy import text
from app.db.session import get_db_engine
from app.models.base import Base

async def run_startup_migrations():
    """
    Executes database schema verification and non-destructive column migrations
    on Neon PostgreSQL during application startup.
    """
    try:
        engine = get_db_engine()
        async with engine.connect() as conn:
            # 1. Rename column mobile_number -> verified_phone if needed
            async with conn.begin() as tx:
                try:
                    await conn.execute(text("ALTER TABLE system_users RENAME COLUMN mobile_number TO verified_phone;"))
                    await tx.commit()
                    print("🚀 [Database Migration] Renamed column mobile_number to verified_phone in system_users table.")
                except Exception:
                    await tx.rollback()

            # 2. Add entry_price column to trading_history if missing
            async with conn.begin() as tx:
                try:
                    await conn.execute(text("ALTER TABLE trading_history ADD COLUMN IF NOT EXISTS entry_price VARCHAR;"))
                    await tx.commit()
                    print("🚀 [Database Migration] Verified/added entry_price column to trading_history table.")
                except Exception:
                    await tx.rollback()

            # 3. Add status column to trading_history if missing
            async with conn.begin() as tx:
                try:
                    await conn.execute(text("ALTER TABLE trading_history ADD COLUMN IF NOT EXISTS status VARCHAR;"))
                    await tx.commit()
                    print("🚀 [Database Migration] Verified/added status column to trading_history table.")
                except Exception:
                    await tx.rollback()

        # 4. Create any tables defined in models if they do not exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        await engine.dispose()
        print("🚀 [Database] Relational schemas successfully verified and updated on Neon PostgreSQL.")
    except Exception as err:
        print(f"⚠️ [Database Startup Notice] Schema migration notice: {err}")
