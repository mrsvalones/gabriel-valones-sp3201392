import os
from pathlib import Path
from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from flask import Flask, g, session, render_template, request, send_from_directory
from flask_wtf.csrf import CSRFProtect, CSRFError
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from .db import configure
from .security import load_user, aware

ROOT = Path(__file__).resolve().parent.parent

def create_app(overrides=None):
    load_dotenv(ROOT / '.env')
    app = Flask(__name__, template_folder=str(ROOT/'templates'), static_folder=None)
    app.config.update(SECRET_KEY=os.getenv('SECRET_KEY'), DATABASE_URL=os.getenv('DATABASE_URL'),
        STORE_NAME=os.getenv('STORE_NAME','Mercado Viva'), APP_URL=os.getenv('APP_URL','http://127.0.0.1:5000'),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.getenv('APP_ENV')=='production',
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30), MAX_CONTENT_LENGTH=128*1024,
        WTF_CSRF_TIME_LIMIT=3600)
    if overrides: app.config.update(overrides)
    if not app.config['SECRET_KEY'] or len(app.config['SECRET_KEY']) < 32 or 'SUBSTITUA' in app.config['SECRET_KEY']:
        raise RuntimeError('Configure SECRET_KEY aleatória com pelo menos 32 caracteres.')
    if not app.config['DATABASE_URL']:
        raise RuntimeError('Configure DATABASE_URL.')
    if (os.getenv('VERCEL') or os.getenv('APP_ENV')=='production') and not app.config['DATABASE_URL'].startswith(('postgres:', 'postgresql:', 'postgresql+psycopg:')):
        raise RuntimeError('Produção exige PostgreSQL persistente.')
    configure(app)
    CSRFProtect(app)
    @app.before_request
    def middleware():
        g.db = app.extensions['db_session']()
        load_user()
        session.permanent = True
    @app.teardown_request
    def cleanup(error=None):
        if hasattr(g,'db'): g.db.close()  # desfaz transações não confirmadas
    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Cache-Control']='no-store'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        if app.config['SESSION_COOKIE_SECURE']:
            response.headers['Strict-Transport-Security']='max-age=31536000'
        return response
    @app.template_filter('brl')
    def brl(value):
        return 'R$ ' + f'{Decimal(value or 0):,.2f}'.replace(',','X').replace('.',',').replace('X','.')
    @app.template_filter('qty')
    def qty(value):
        return f'{Decimal(value):.3f}'.rstrip('0').rstrip('.').replace('.',',')
    @app.template_filter('localtime')
    def localtime(value):
        return aware(value).astimezone(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M') if value else '—'
    @app.context_processor
    def context():
        return dict(current_user=getattr(g,'user',None), store_name=app.config['STORE_NAME'],
            theme=session.get('theme','aurora'), payment_names={'cash':'Dinheiro','debit':'Débito','credit':'Crédito','pix':'Pix'})
    @app.route('/assets/<path:filename>')
    def local_assets(filename):
        return send_from_directory(ROOT/'public', filename)
    # Em produção, a CDN atende /css e /js a partir de public.
    @app.route('/css/<path:filename>')
    def css(filename): return send_from_directory(ROOT/'public/css', filename)
    @app.route('/images/<path:filename>')
    def images(filename): return send_from_directory(ROOT/'public/images', filename)
    @app.route('/js/<path:filename>')
    def js(filename): return send_from_directory(ROOT/'public/js', filename)
    @app.errorhandler(ValueError)
    def invalid(error):
        if hasattr(g,'db'): g.db.rollback()
        return render_template('error.html', title='Revise os dados', message=str(error)), 400
    @app.errorhandler(IntegrityError)
    def conflict(error):
        if hasattr(g,'db'): g.db.rollback()
        return render_template('error.html', title='Conflito', message='Registro duplicado ou operação simultânea. Atualize a página e confira o resultado antes de repetir.'),409
    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        if hasattr(g,'db'): g.db.rollback()
        app.logger.error('Falha de banco: %s', type(error).__name__)
        return render_template('error.html',title='Banco indisponível',message='Verifique a conexão e as migrações. Nenhuma operação parcial foi confirmada.'),503
    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return render_template('error.html',title='Formulário expirado',message='Atualize a página e tente novamente.'),400
    for status in (403,404,500):
        app.register_error_handler(status, lambda e: (render_template('error.html',title=f'Erro {e.code}',message='Acesso não permitido, página inexistente ou falha interna.'),e.code))
    from .controllers import auth, catalog, pos, reports
    for module in (auth,catalog,pos,reports): app.register_blueprint(module.bp)
    return app
