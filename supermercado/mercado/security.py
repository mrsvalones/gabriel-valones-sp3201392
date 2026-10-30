from functools import wraps
from datetime import datetime, timezone
from flask import g, session, redirect, url_for, abort, request
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User

def aware(dt):
    return dt.replace(tzinfo=timezone.utc) if dt and dt.tzinfo is None else dt

def password_policy(password):
    if not 15 <= len(password) <= 128 or len(set(password)) < 8:
        raise ValueError('Use uma frase-senha de 15 a 128 caracteres e pelo menos 8 caracteres distintos.')
    if any(word in password.lower() for word in ('123456', 'password', 'senha123', 'qwerty', 'administrador')):
        raise ValueError('Senha previsível. Escolha uma frase-senha diferente.')
    return generate_password_hash(password, method='scrypt')

def load_user():
    g.user = g.db.get(User, session.get('uid')) if session.get('uid') else None
    if g.user and (not g.user.active or session.get('version') != g.user.version):
        session.clear()
        g.user = None

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for('auth.login'))
        return fn(*args, **kwargs)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user.role != 'admin': abort(403)
        return fn(*args, **kwargs)
    return wrapped

def reauthenticate():
    if not check_password_hash(g.user.password_hash, request.form.get('current_password','')):
        raise ValueError('Confirme sua senha atual para esta operação.')
