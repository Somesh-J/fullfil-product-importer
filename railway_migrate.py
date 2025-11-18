#!/usr/bin/env python
"""
Railway Database Migration Script
Run this in Railway to create database tables
Usage: railway run python railway_migrate.py
"""

import os
import sys
import asyncio
from alembic.config import Config
from alembic import command
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def verify_tables(db_url: str):
    """Verify that tables were created successfully"""
    print("\n🔍 Verifying tables were created...")
    
    # Convert URL to asyncpg format
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(db_url, echo=False)
    
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
            )
            tables = result.fetchall()
            
            if tables:
                print("\n✅ Tables created successfully:")
                for table in tables:
                    print(f"   ✓ {table[0]}")
                return True
            else:
                print("\n⚠️  No tables found!")
                return False
    finally:
        await engine.dispose()


def run_migrations():
    """Run Alembic migrations"""
    print("🚀 Starting Railway Database Migration...\n")
    print(f"📍 Current directory: {os.getcwd()}")
    print(f"🐍 Python version: {sys.version.split()[0]}\n")
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable not set!")
        sys.exit(1)
    
    print(f"📊 Database URL: {db_url[:50]}...\n")
    
    # Configure Alembic
    print("🔄 Running Alembic migrations...")
    alembic_cfg = Config("alembic.ini")
    
    try:
        # Run upgrade to head
        command.upgrade(alembic_cfg, "head")
        print("\n✅ Migration completed successfully!")
        
        # Verify tables
        success = asyncio.run(verify_tables(db_url))
        
        if success:
            print("\n🎉 Database is ready for use!")
            return 0
        else:
            print("\n⚠️  Migration completed but tables not found!")
            return 1
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_migrations())
