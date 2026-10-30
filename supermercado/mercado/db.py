from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

class Base(DeclarativeBase):
    pass

def normalize_url(url):
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    if url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    return url

def make_engine(url):
    engine = create_engine(normalize_url(url), poolclass=NullPool, pool_pre_ping=True)
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine, 'connect')
        def foreign_keys(conn, record):
            conn.execute('PRAGMA foreign_keys=ON')
    return engine

def configure(app):
    engine = make_engine(app.config['DATABASE_URL'])
    app.extensions['engine'] = engine
    app.extensions['db_session'] = sessionmaker(engine, expire_on_commit=False)
