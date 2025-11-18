#!/bin/sh
# Railway Migration Script
# Runs database migrations in Railway's Docker environment

set -e

echo "🚀 Starting Railway Database Migration..."
echo "📍 Current directory: $(pwd)"
echo "🐍 Python version: $(python --version)"

# Check if alembic is installed
if ! command -v alembic >/dev/null 2>&1; then
    echo "❌ Alembic not found! Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "📊 Database connection check..."
python -c "import os; print(f'DATABASE_URL: {os.getenv(\"DATABASE_URL\", \"NOT SET\")[:50]}...')"

echo ""
echo "🔄 Running Alembic migrations..."
alembic upgrade head

echo ""
echo "✅ Migration completed successfully!"
echo ""
echo "🔍 Verifying tables were created..."
python -c "
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_tables():
    db_url = os.getenv('DATABASE_URL', '')
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    engine = create_async_engine(db_url, echo=False)
    async with engine.connect() as conn:
        result = await conn.execute(text(\"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename\"))
        tables = result.fetchall()
        
        if tables:
            print('\\n✅ Tables created successfully:')
            for table in tables:
                print(f'   ✓ {table[0]}')
        else:
            print('\\n⚠️  No tables found!')
        
        await engine.dispose()

asyncio.run(check_tables())
"

echo ""
echo "🎉 Database is ready for use!"
