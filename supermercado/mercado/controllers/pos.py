from uuid import uuid4
from decimal import Decimal
from flask import Blueprint,g,session,request,render_template,redirect,url_for,flash,abort
from sqlalchemy import select
from ..models import *
from ..security import login_required,admin_required,reauthenticate
from ..services.operations import *

bp=Blueprint('pos',__name__)
@bp.route('/cash',methods=['GET','POST'])
@login_required
def cash():
    if request.method=='POST':
        action=request.form.get('action')
        if action=='open': open_cash(g.db,g.user,request.form['opening'])
        elif action=='close':
            reauthenticate(); close_cash(g.db,g.user,request.form['counted'])
        elif action in ('supply','withdrawal'):
            reauthenticate(); c=locked_cash(g.db,g.user)
            amount=number(request.form['amount'],2,True)
            if action=='withdrawal' and amount>cash_totals(g.db,c)[3]: raise ValueError('Sangria excede o dinheiro esperado.')
            reason=request.form.get('reason','').strip()
            if len(reason)<5: raise ValueError('Informe motivo com 5 a 200 caracteres.')
            g.db.add(CashMovement(cash_id=c.id,kind=action,amount=amount,reason=reason[:200]))
            audit(g.db,g.user,f'{action} caixa {c.id}: {amount}')
        else: raise ValueError('Ação inválida.')
        g.db.commit(); return redirect(url_for('pos.cash'))
    c=g.db.scalar(select(CashSession).where(CashSession.user_id==g.user.id,CashSession.closed_at.is_(None)))
    history=select(CashSession).order_by(CashSession.id.desc()).limit(100)
    if g.user.role!='admin': history=history.where(CashSession.user_id==g.user.id)
    return render_template('cash.html',cash=c,totals=cash_totals(g.db,c) if c else None,history=g.db.scalars(history).all())

@bp.route('/pos',methods=['GET','POST'])
@login_required
def terminal():
    cart=dict(session.get('cart',{}))
    if request.method=='POST':
        action=request.form.get('action')
        if action=='clear': cart={}
        elif action=='remove': cart.pop(request.form.get('id'),None)
        elif action=='add':
            p=g.db.scalar(select(Product).where(Product.sku==request.form.get('sku','').strip(),Product.active.is_(True)))
            if not p: raise ValueError('SKU/código de barras não encontrado.')
            q=quantity(p,request.form.get('quantity','1'))+Decimal(cart.get(str(p.id),'0'))
            if q>p.stock: raise ValueError('Quantidade acima do estoque disponível.')
            if str(p.id) not in cart and len(cart)>=40: raise ValueError('Limite de 40 produtos distintos por venda.')
            cart[str(p.id)]=str(q)
        else: raise ValueError('Ação inválida.')
        session['cart']=cart; session['sale_key']=str(uuid4())
        return redirect(url_for('pos.terminal'))
    session.setdefault('sale_key',str(uuid4()))
    lines=[]; total=ZERO
    for pid,raw in cart.items():
        p=g.db.get(Product,int(pid))
        if p:
            q=Decimal(raw); sub=money(q*p.price); total+=sub; lines.append((p,q,sub))
    products=g.db.scalars(select(Product).where(Product.active.is_(True)).order_by(Product.name)).all()
    cash=g.db.scalar(select(CashSession).where(CashSession.user_id==g.user.id,CashSession.closed_at.is_(None)))
    return render_template('pos.html',lines=lines,total=total,products=products,cash=cash,key=session['sale_key'])

@bp.post('/checkout')
@login_required
def finalize():
    key=request.form.get('key','')
    previous=g.db.scalar(select(Sale).where(Sale.key==key,Sale.user_id==g.user.id))
    if previous: return redirect(url_for('pos.receipt',sale_id=previous.id))
    if key!=session.get('sale_key'): raise ValueError('Formulário expirado. Confira as vendas antes de repetir.')
    payments={method:request.form.get(method,'0') or '0' for method in ('cash','debit','credit','pix')}
    # Preço informado no cliente nunca é usado; os valores vêm do banco.
    sale=checkout(g.db,g.user,session.get('cart',{}),key,payments,request.form.get('received','0') or '0')
    g.db.commit(); session.pop('cart',None); session.pop('sale_key',None)
    return redirect(url_for('pos.receipt',sale_id=sale.id))

@bp.get('/sales/<int:sale_id>')
@login_required
def receipt(sale_id):
    sale=g.db.get(Sale,sale_id)
    if not sale: abort(404)
    if g.user.role!='admin' and sale.user_id!=g.user.id: abort(403)
    return render_template('receipt.html',sale=sale)

@bp.post('/sales/<int:sale_id>/cancel')
@admin_required
def cancel(sale_id):
    reauthenticate(); cancel_sale(g.db,g.user,sale_id,request.form.get('reason','')); g.db.commit()
    return redirect(url_for('pos.receipt',sale_id=sale_id))
