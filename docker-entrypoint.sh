#!/bin/sh
# Entrypoint script for Railway deployment
# Runs migrations before starting the application

set -e

echo "🚀 Railway Deployment Starting..."

# Wait for database to be ready
echo "⏳ Waiting for database connection..."
python -c "
import time
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine

async def wait_for_db():
    db_url = os.getenv('DATABASE_URL', '')
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    engine = create_async_engine(db_url, echo=False)
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            async with engine.connect() as conn:
                await conn.execute(__import__('sqlalchemy').text('SELECT 1'))
            print('✅ Database connection established!')
            await engine.dispose()
            return True
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                print(f'⏳ Waiting for database... ({retry_count}/{max_retries})')
                time.sleep(2)
            else:
                print(f'❌ Database connection failed: {e}')
                await engine.dispose()
                return False
    return False

if not asyncio.run(wait_for_db()):
    exit(1)
"

# Run migrations
echo "🔄 Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully!"
else
    echo "❌ Migration failed!"
    exit 1
fi

# Verify tables exist
echo "🔍 Verifying database tables..."
python -c "
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    db_url = os.getenv('DATABASE_URL', '')
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    engine = create_async_engine(db_url, echo=False)
    async with engine.connect() as conn:
        result = await conn.execute(text(\"SELECT COUNT(*) FROM pg_tables WHERE schemaname='public'\"))
        count = result.scalar()
        print(f'✅ Found {count} tables in database')
    await engine.dispose()

asyncio.run(check())
"

echo "🎉 Starting application..."
echo ""

# Start the application
exec "$@"
