"""Serviços transacionais: o controller confirma uma única transação por operação."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import UUID, uuid4
from sqlalchemy import select, func
from ..models import *

ZERO = Decimal('0.00')
def number(value, places=2, positive=False):
    try:
        d = Decimal(str(value).replace(',','.'))
        if not d.is_finite() or abs(d) > Decimal('9999999'):
            raise ValueError('Valor fora do limite.')
        rounded = d.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)
        if d != rounded: raise ValueError(f'Use no máximo {places} casas decimais.')
        if d < 0 or (positive and d <= 0): raise ValueError('Informe valor positivo válido.')
        return d
    except (InvalidOperation, TypeError):
        raise ValueError('Número inválido.')

def money(value):
    result = value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    if abs(result) > Decimal('9999999999.99'): raise ValueError('Total excede o limite.')
    return result

def audit(db,user,action): db.add(Audit(user_id=user.id,action=action[:200]))

def quantity(product,value):
    q = number(value,3,True)
    if product.unit=='UN' and q != q.to_integral_value():
        raise ValueError(f'{product.name}: unidades devem ser inteiras.')
    return q

def stock_move(db,user,p,delta,reason):
    p.stock += delta
    if p.stock < 0: raise ValueError(f'Estoque insuficiente: {p.name}.')
    db.add(StockMovement(product_id=p.id,user_id=user.id,quantity=delta,balance=p.stock,reason=reason))

def open_cash(db,user,opening):
    db.scalar(select(User).where(User.id==user.id).with_for_update())
    if db.scalar(select(CashSession).where(CashSession.user_id==user.id,CashSession.closed_at.is_(None))):
        raise ValueError('Você já possui caixa aberto.')
    c=CashSession(user_id=user.id,opening=number(opening))
    db.add(c); db.flush(); audit(db,user,f'Abertura caixa {c.id}')
    return c

def locked_cash(db,user):
    c=db.scalar(select(CashSession).where(CashSession.user_id==user.id,CashSession.closed_at.is_(None)).with_for_update())
    if not c: raise ValueError('Abra seu caixa antes de continuar.')
    return c

def cash_totals(db,c):
    rows=db.execute(select(Payment.method,func.sum(Payment.amount)).join(Sale,Sale.id==Payment.sale_id)
        .where(Sale.cash_id==c.id,Sale.status=='completed').group_by(Payment.method)).all()
    totals={k:ZERO for k in ('cash','debit','credit','pix')}
    totals.update(dict(rows))
    moves=db.scalars(select(CashMovement).where(CashMovement.cash_id==c.id)).all()
    supplies=sum((m.amount for m in moves if m.kind=='supply'),ZERO)
    withdrawals=sum((m.amount for m in moves if m.kind=='withdrawal'),ZERO)
    expected=c.opening+totals['cash']+supplies-withdrawals
    return totals, supplies, withdrawals, expected

def close_cash(db,user,counted):
    c=locked_cash(db,user)
    c.expected=cash_totals(db,c)[3]
    c.counted=number(counted); c.difference=c.counted-c.expected; c.closed_at=now()
    audit(db,user,f'Fechamento caixa {c.id} diferença {c.difference}')
    return c

def checkout(db,user,cart,key,payments,received):
    UUID(key)
    previous=db.scalar(select(Sale).where(Sale.key==key))
    if previous:
        if previous.user_id!=user.id: raise ValueError('Identificador inválido.')
        return previous
    c=locked_cash(db,user)
    # Segunda consulta após bloqueio evita repetir venda simultânea do mesmo operador.
    previous=db.scalar(select(Sale).where(Sale.key==key))
    if previous: return previous
    if not cart or len(cart)>40: raise ValueError('Carrinho vazio ou acima de 40 produtos.')
    lines=[]; total=ZERO
    for pid,value in sorted(cart.items(),key=lambda kv:int(kv[0])):
        p=db.scalar(select(Product).where(Product.id==int(pid)).with_for_update())
        if not p or not p.active: raise ValueError('Produto indisponível.')
        q=quantity(p,value)
        if p.stock<q: raise ValueError(f'Estoque insuficiente: {p.name}.')
        subtotal=money(q*p.price); total+=subtotal; lines.append((p,q,subtotal))
    total=money(total)
    if total<=0: raise ValueError('Total deve ser positivo.')
    if set(payments)-{'cash','debit','credit','pix'}: raise ValueError('Pagamento desconhecido.')
    amounts={k:number(v) for k,v in payments.items()}
    if sum(amounts.values(),ZERO)!=total: raise ValueError('A soma dos pagamentos deve coincidir com o total.')
    cash=amounts.get('cash',ZERO); received=number(received)
    if cash==0 and received!=0: raise ValueError('Recebido em espécie só se aplica a dinheiro.')
    if received<cash: raise ValueError('Dinheiro recebido é insuficiente.')
    sale=Sale(key=key,user_id=user.id,cash_id=c.id,total=total,cash_received=received,change=received-cash)
    db.add(sale); db.flush()
    for p,q,subtotal in lines:
        db.add(SaleItem(sale_id=sale.id,product_id=p.id,name=p.name,sku=p.sku,unit=p.unit,
                        quantity=q,price=p.price,cost=p.cost,subtotal=subtotal))
        stock_move(db,user,p,-q,f'Venda #{sale.id}')
    for method,amount in amounts.items():
        if amount>0: db.add(Payment(sale_id=sale.id,method=method,amount=amount,reference='SIM-'+uuid4().hex[:16].upper()))
    db.add(Ledger(user_id=user.id,sale_id=sale.id,description=f'Venda simulada #{sale.id}',amount=total))
    audit(db,user,f'Venda {sale.id} concluída'); return sale

def cancel_sale(db,user,sale_id,reason):
    if user.role!='admin': raise ValueError('Administrador necessário.')
    reason=reason.strip()
    if len(reason)<5: raise ValueError('Informe motivo com pelo menos 5 caracteres.')
    initial=db.get(Sale,sale_id)
    if not initial: raise ValueError('Venda inexistente.')
    cash=db.scalar(select(CashSession).where(CashSession.id==initial.cash_id).with_for_update())
    sale=db.scalar(select(Sale).where(Sale.id==sale_id).with_for_update().execution_options(populate_existing=True))
    if cash.closed_at: raise ValueError('Cancelamento permitido apenas enquanto o caixa de origem estiver aberto.')
    if sale.status!='completed': raise ValueError('Venda já cancelada.')
    for item in sorted(sale.items,key=lambda i:i.product_id):
        p=db.scalar(select(Product).where(Product.id==item.product_id).with_for_update())
        stock_move(db,user,p,item.quantity,f'Estorno venda #{sale.id}')
    sale.status='cancelled'; sale.cancel_reason=reason[:200]
    db.add(Ledger(user_id=user.id,sale_id=sale.id,description=f'Estorno venda #{sale.id}',amount=-sale.total))
    audit(db,user,f'Cancelamento venda {sale.id}: {reason}')

def receive_purchase(db,user,supplier_id,reference,rows,key):
    UUID(key)
    db.scalar(select(User).where(User.id==user.id).with_for_update())
    previous=db.scalar(select(Purchase).where(Purchase.key==key))
    if previous: return previous
    supplier=db.get(Supplier,supplier_id)
    if not supplier: raise ValueError('Fornecedor inválido.')
    if not reference.strip(): raise ValueError('Informe documento/referência simulada.')
    if not rows: raise ValueError('Adicione itens à compra.')
    if len({r[0] for r in rows})!=len(rows): raise ValueError('Agrupe o produto em uma única linha.')
    purchase=Purchase(key=key,user_id=user.id,supplier_id=supplier.id,reference=reference[:80],total=ZERO)
    db.add(purchase); db.flush()
    total=ZERO
    for pid,rawq,rawcost in sorted(rows):
        p=db.scalar(select(Product).where(Product.id==pid).with_for_update())
        if not p or not p.active: raise ValueError('Produto inválido ou inativo.')
        q=quantity(p,rawq); cost=number(rawcost,2,True); subtotal=money(q*cost)
        p.cost=money((p.stock*p.cost+q*cost)/(p.stock+q))
        stock_move(db,user,p,q,f'Compra #{purchase.id}')
        db.add(PurchaseItem(purchase_id=purchase.id,product_id=p.id,quantity=q,cost=cost,subtotal=subtotal))
        total+=subtotal
    purchase.total=money(total)
    db.add(Ledger(user_id=user.id,purchase_id=purchase.id,description=f'Compra à vista simulada #{purchase.id}',amount=-purchase.total))
    audit(db,user,f'Compra {purchase.id} recebida'); return purchase
