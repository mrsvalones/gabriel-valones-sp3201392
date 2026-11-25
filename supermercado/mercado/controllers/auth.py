import hashlib, os, secrets, smtplib, ssl
from email.message import EmailMessage
from datetime import timedelta
from flask import Blueprint, g, session, request, render_template, redirect, url_for, flash, current_app
from sqlalchemy import select, update
from werkzeug.security import check_password_hash, generate_password_hash
from ..models import User, ResetToken, now
from ..security import login_required, password_policy, reauthenticate, aware
from ..services.operations import audit

bp=Blueprint('auth',__name__)
DUMMY=generate_password_hash('dummy-credential-not-for-login')

@bp.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form.get('email','').strip().lower()
        user=g.db.scalar(select(User).where(User.email==email).with_for_update())
        valid=check_password_hash(user.password_hash if user else DUMMY,request.form.get('password',''))
        blocked=user and user.locked_until and aware(user.locked_until)>now()
        if not user or not user.active or not valid or blocked:
            if user and not blocked:
                user.failures+=1
                if user.failures>=5: user.locked_until=now()+timedelta(minutes=15)
                g.db.commit()
            flash('Credenciais inválidas ou acesso temporariamente bloqueado. Após 5 falhas, aguarde 15 minutos.','error')
            return render_template('login.html'),401
        user.failures=0; user.locked_until=None
        audit(g.db,user,'Login'); g.db.commit()
        theme=session.get('theme','aurora'); session.clear()
        session.update(uid=user.id,version=user.version,theme=theme)
        return redirect(url_for('reports.dashboard'))
    return render_template('login.html')

@bp.post('/logout')
def logout():
    session.clear(); return redirect(url_for('auth.login'))

@bp.post('/theme')
def theme():
    session['theme']='tropical' if request.form.get('theme')=='tropical' else 'aurora'
    return redirect(url_for('reports.dashboard') if g.user else url_for('auth.login'))

@bp.route('/account',methods=['GET','POST'])
@login_required
def account():
    if request.method=='POST':
        reauthenticate()
        if request.form['password']!=request.form['confirmation']: raise ValueError('Senhas não coincidem.')
        user=g.db.scalar(select(User).where(User.id==g.user.id).with_for_update())
        user.password_hash=password_policy(request.form['password']); user.version+=1
        g.db.execute(update(ResetToken).where(ResetToken.user_id==user.id).values(used=True))
        audit(g.db,user,'Alteração de senha'); g.db.commit(); session.clear()
        flash('Senha alterada. Entre novamente.','success'); return redirect(url_for('auth.login'))
    return render_template('account.html')

def new_reset(db,user):
    db.execute(update(ResetToken).where(ResetToken.user_id==user.id).values(used=True))
    token=secrets.token_urlsafe(32)
    db.add(ResetToken(user_id=user.id,digest=hashlib.sha256(token.encode()).hexdigest(),expires_at=now()+timedelta(minutes=20)))
    return token

@bp.route('/forgot',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        user=g.db.scalar(select(User).where(User.email==request.form.get('email','').strip().lower()).with_for_update())
        if user and user.active and os.getenv('SMTP_HOST'):
            recent=g.db.scalar(select(ResetToken).where(ResetToken.user_id==user.id,ResetToken.expires_at>now()+timedelta(minutes=18)))
            if not recent:
                token=new_reset(g.db,user); g.db.commit()
                message=EmailMessage(); message['Subject']='Recuperação de acesso - Mercado Viva'
                message['From']=os.getenv('SMTP_FROM'); message['To']=user.email
                message.set_content(f"Redefina a senha em até 20 minutos: {current_app.config['APP_URL'].rstrip('/')}/reset/{token}")
                try:
                    with smtplib.SMTP(os.getenv('SMTP_HOST'),int(os.getenv('SMTP_PORT','587')),timeout=8) as smtp:
                        smtp.starttls(context=ssl.create_default_context())
                        smtp.login(os.getenv('SMTP_USER'),os.getenv('SMTP_PASSWORD')); smtp.send_message(message)
                except (OSError,smtplib.SMTPException):
                    current_app.logger.error('Envio SMTP falhou; use recuperação pelo responsável.')
        flash('Se a conta estiver ativa e o envio configurado, você receberá instruções. Sem e-mail, contate o responsável pelo projeto.','success')
        return redirect(url_for('auth.login'))
    return render_template('forgot.html')

@bp.route('/reset/<token>',methods=['GET','POST'])
def reset(token):
    digest=hashlib.sha256(token.encode()).hexdigest()
    row=g.db.scalar(select(ResetToken).where(ResetToken.digest==digest).with_for_update())
    if not row or row.used or aware(row.expires_at)<now(): raise ValueError('Link inválido ou expirado.')
    if request.method=='POST':
        if request.form['password']!=request.form['confirmation']: raise ValueError('Senhas não coincidem.')
        user=g.db.scalar(select(User).where(User.id==row.user_id).with_for_update())
        if not user.active: raise ValueError('Conta indisponível.')
        user.password_hash=password_policy(request.form['password']); user.version+=1
        user.failures=0; user.locked_until=None
        g.db.execute(update(ResetToken).where(ResetToken.user_id==user.id).values(used=True))
        audit(g.db,user,'Recuperação de senha'); g.db.commit(); session.clear()
        flash('Senha redefinida. Faça login.','success'); return redirect(url_for('auth.login'))
    return render_template('reset.html')
