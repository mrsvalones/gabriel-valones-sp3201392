from uuid import uuid4
from decimal import Decimal
from flask import Blueprint,g,request,render_template,redirect,url_for,flash,session,abort
from sqlalchemy import select,func
from ..models import *
from ..security import admin_required, reauthenticate, password_policy
from ..services.operations import number, stock_move, receive_purchase, audit

bp=Blueprint('catalog',__name__)
def label(name,maximum=120):
    value=request.form.get(name,'').strip()
    if not value or len(value)>maximum: raise ValueError(f'Campo {name}: informe de 1 a {maximum} caracteres.')
    return value

@bp.route('/products',methods=['GET','POST'])
@admin_required
def products():
    if request.method=='POST':
        pid=request.form.get('id')
        p=g.db.scalar(select(Product).where(Product.id==int(pid)).with_for_update()) if pid else Product(stock=0)
        if pid and not p: abort(404)
        p.name=label('name'); p.sku=label('sku',40)
        p.category_id=int(request.form['category_id'])
        if not g.db.get(Category,p.category_id): raise ValueError('Categoria inexistente.')
        unit=request.form.get('unit','UN')
        if unit not in ('UN','KG'): raise ValueError('Unidade inválida.')
        if pid and unit!=p.unit:
            raise ValueError('A unidade de produto existente não pode ser alterada; crie outro SKU.')
        p.unit=unit; p.price=number(request.form['price'],2,True)
        p.minimum=number(request.form['minimum'],3); p.active=request.form.get('active')=='on'
        if not pid: p.cost=number(request.form.get('cost','0'))
        g.db.add(p); g.db.flush(); audit(g.db,g.user,f'Cadastro produto {p.id}'); g.db.commit()
        return redirect(url_for('catalog.products'))
    edit=g.db.get(Product,request.args.get('edit',type=int)) if request.args.get('edit') else None
    return render_template('products.html',products=g.db.scalars(select(Product).order_by(Product.name)).all(),
                           categories=g.db.scalars(select(Category).order_by(Category.name)).all(),edit=edit)

@bp.route('/masters',methods=['GET','POST'])
@admin_required
def masters():
    if request.method=='POST':
        if request.form.get('kind')=='category': g.db.add(Category(name=label('name',80)))
        elif request.form.get('kind')=='supplier': g.db.add(Supplier(name=label('name'),contact=request.form.get('contact','')[:180]))
        else: raise ValueError('Tipo inválido.')
        audit(g.db,g.user,'Cadastro categoria/fornecedor'); g.db.commit()
        return redirect(url_for('catalog.masters'))
    return render_template('masters.html',categories=g.db.scalars(select(Category).order_by(Category.name)).all(),suppliers=g.db.scalars(select(Supplier).order_by(Supplier.name)).all())

@bp.route('/stock',methods=['GET','POST'])
@admin_required
def stock():
    if request.method=='POST':
        reauthenticate()
        p=g.db.scalar(select(Product).where(Product.id==int(request.form['product_id'])).with_for_update())
        if not p: raise ValueError('Produto inválido.')
        target=number(request.form['balance'],3)
        if p.unit=='UN' and target!=target.to_integral_value(): raise ValueError('UN exige saldo inteiro.')
        reason=label('reason',180)
        stock_move(g.db,g.user,p,target-p.stock,'Ajuste: '+reason)
        audit(g.db,g.user,f'Ajuste estoque {p.id}: {reason}'); g.db.commit()
        return redirect(url_for('catalog.stock'))
    query=select(Product).order_by(Product.name)
    category=request.args.get('category',type=int)
    if category: query=query.where(Product.category_id==category)
    products=g.db.scalars(query).all()
    groups=g.db.execute(select(Category.name,func.sum(Product.stock*Product.cost),func.count(Product.id)).join(Product).group_by(Category.name)).all()
    moves=g.db.scalars(select(StockMovement).order_by(StockMovement.id.desc()).limit(100)).all()
    return render_template('stock.html',products=products,categories=g.db.scalars(select(Category)).all(),groups=groups,moves=moves,category=category)

@bp.route('/purchases',methods=['GET','POST'])
@admin_required
def purchases():
    if request.method=='POST':
        ids=request.form.getlist('product_id'); quantities=request.form.getlist('quantity'); costs=request.form.getlist('cost')
        if not len(ids)==len(quantities)==len(costs): raise ValueError('Itens inválidos.')
        rows=[(int(p),q,c) for p,q,c in zip(ids,quantities,costs) if p]
        key=request.form.get('key','')
        if key!=session.get('purchase_key'): raise ValueError('Formulário expirado. Consulte as compras antes de repetir.')
        purchase=receive_purchase(g.db,g.user,int(request.form['supplier_id']),request.form.get('reference',''),rows,key)
        g.db.commit(); session.pop('purchase_key',None)
        flash(f'Compra #{purchase.id} recebida. Estoque e financeiro atualizados.','success')
        return redirect(url_for('catalog.purchases'))
    session.setdefault('purchase_key',str(uuid4()))
    return render_template('purchases.html',key=session['purchase_key'],products=g.db.scalars(select(Product).where(Product.active.is_(True)).order_by(Product.name)).all(),
       suppliers=g.db.scalars(select(Supplier).order_by(Supplier.name)).all(),purchases=g.db.scalars(select(Purchase).order_by(Purchase.id.desc()).limit(100)).all())

@bp.route('/users',methods=['GET','POST'])
@admin_required
def users():
    if request.method=='POST':
        reauthenticate()
        if request.form.get('action')=='toggle':
            user=g.db.scalar(select(User).where(User.id==int(request.form['id'])).with_for_update())
            if not user: abort(404)
            if user.role=='admin': raise ValueError('Administradores não podem ser desativados por esta tela.')
            if g.db.scalar(select(CashSession).where(CashSession.user_id==user.id,CashSession.closed_at.is_(None))):
                raise ValueError('Feche o caixa deste operador antes de desativá-lo.')
            user.active=not user.active; user.version+=1; audit(g.db,g.user,f'Ativação usuário {user.id}: {user.active}')
        else:
            email=label('email',180).lower()
            if '@' not in email or '.' not in email.split('@')[-1]: raise ValueError('E-mail inválido.')
            role=request.form.get('role')
            if role not in ('admin','operator'): raise ValueError('Perfil inválido.')
            user=User(name=label('name',100),email=email,role=role,password_hash=password_policy(request.form.get('password','')))
            g.db.add(user); g.db.flush(); audit(g.db,g.user,f'Criação usuário {user.id}')
        g.db.commit(); return redirect(url_for('catalog.users'))
    return render_template('users.html',users=g.db.scalars(select(User).order_by(User.name)).all())
