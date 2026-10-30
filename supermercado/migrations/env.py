import os
from pathlib import Path
from dotenv import load_dotenv
from alembic import context
from mercado.db import Base,make_engine,normalize_url
from mercado import models
load_dotenv(Path(__file__).resolve().parent.parent/'.env')
url=os.getenv('DATABASE_DIRECT_URL') or os.getenv('DATABASE_URL')
if not url: raise RuntimeError('Configure DATABASE_DIRECT_URL ou DATABASE_URL.')
if context.is_offline_mode():
    context.configure(url=normalize_url(url),target_metadata=Base.metadata,literal_binds=True,dialect_opts={'paramstyle':'named'})
    with context.begin_transaction(): context.run_migrations()
else:
    engine=make_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection,target_metadata=Base.metadata,compare_type=True)
        with context.begin_transaction(): context.run_migrations()
