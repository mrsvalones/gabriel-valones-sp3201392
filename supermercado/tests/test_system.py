"""Testes de regras de negócio e integração HTTP com banco isolado."""
import re
from decimal import Decimal as D
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from alembic import command
from alembic.config import Config
from mercado import create_app
from mercado.models import *
from mercado.security import password_policy
from mercado.services.operations import *
from mercado.controllers.auth import new_reset

PASSWORD='Lua! Escola Mercado 2026'
@pytest.fixture
def app(tmp_path,monkeypatch):
    monkeypatch.delenv('VERCEL',raising=False); monkeypatch.setenv('APP_ENV','development')
    url='sqlite:///'+str(tmp_path/'test.db')
    monkeypatch.setenv('DATABASE_URL',url); monkeypatch.setenv('DATABASE_DIRECT_URL',url)
    command.upgrade(Config('alembic.ini'),'head')
    app=create_app({'TESTING':True,'SECRET_KEY':'a'*64,'DATABASE_URL':url,'WTF_CSRF_ENABLED':True})
    with app.extensions['db_session']() as db:
        a=User(name='Admin',email='admin@example.test',role='admin',password_hash=password_policy(PASSWORD))
        o=User(name='Operador',email='op@example.test',role='operator',password_hash=password_policy(PASSWORD))
        other=User(name='Outro',email='other@example.test',role='operator',password_hash=password_policy(PASSWORD))
        c=Category(name='Teste'); s=Supplier(name='Fornecedor Escola')
        db.add_all([a,o,other,c,s]); db.flush()
        db.add_all([Product(sku='1001',name='Arroz',category_id=c.id,unit='UN',price=D('10'),cost=D('6'),stock=D('10'),minimum=D('2')),
                    Product(sku='3001',name='Banana',category_id=c.id,unit='KG',price=D('6.90'),cost=D('3.80'),stock=D('20'),minimum=D('2'))])
        db.commit()
    yield app
    app.extensions['engine'].dispose()

@pytest.fixture
def client(app): return app.test_client()
def token(client,path='/login'):
    r=client.get(path)
    assert r.status_code==200,(path,r.status_code,r.data[:500])
    return re.search(rb'name="csrf_token" value="([^"]+)"',r.data)[1].decode()
def post(client,path,data,source='/login'):
    return client.post(path,data={'csrf_token':token(client,source),**data})
def login(client,email='admin@example.test'):
    r=post(client,'/login',{'email':email,'password':PASSWORD})
    assert r.status_code==302

def test_pages_and_permissions(client):
    assert client.get('/products').status_code==302
    login(client)
    for path in ['/','/products','/stock','/purchases','/masters','/users','/cash','/pos','/sales','/finance','/audit','/account','/css/aurora.css','/css/tropical.css','/js/app.js']:
        r=client.get(path); assert r.status_code==200,(path,r.data[:500])
    post(client,'/logout',{},'/')
    login(client,'op@example.test')
    for path in ['/products','/stock','/purchases','/masters','/users','/finance','/audit']:
        assert client.get(path).status_code==403

def test_csrf_and_login_lockout(client):
    assert client.post('/login',data={'email':'admin@example.test','password':PASSWORD}).status_code==400
    for _ in range(5): assert post(client,'/login',{'email':'admin@example.test','password':'wrong'}).status_code==401
    assert post(client,'/login',{'email':'admin@example.test','password':PASSWORD}).status_code==401

def test_sale_split_and_double_submit(app,client):
    login(client,'op@example.test')
    assert post(client,'/cash',{'action':'open','opening':'100'},'/cash').status_code==302
    assert post(client,'/pos',{'action':'add','sku':'1001','quantity':'2'},'/pos').status_code==302
    with client.session_transaction() as s: key=s['sale_key']
    data={'key':key,'cash':'5','debit':'5','credit':'5','pix':'5','received':'10','price':'0.01'}
    r=post(client,'/checkout',data,'/pos'); assert r.status_code==302
    assert client.get(r.location).status_code==200
    assert b'SEM VALOR FISCAL' in client.get(r.location).data
    assert post(client,'/checkout',data,'/pos').status_code==302
    with app.extensions['db_session']() as db:
        sale=db.scalar(select(Sale)); assert sale.total==D('20'); assert sale.change==D('5')
        assert db.scalar(select(func.count(Sale.id)))==1
        assert db.get(Product,1).stock==D('8')
        assert len(sale.payments)==4
        cash=db.get(CashSession,1); assert cash_totals(db,cash)[3]==D('105')
    assert post(client,'/cash',{'action':'close','counted':'104','current_password':PASSWORD},'/cash').status_code==302
    with app.extensions['db_session']() as db:
        c=db.get(CashSession,1); assert c.expected==105; assert c.difference==-1
    assert client.get('/sales.xlsx').status_code==200

def test_purchase_cost_and_idempotency(app):
    with app.extensions['db_session']() as db:
        user=db.get(User,1); key=str(uuid4())
        purchase=receive_purchase(db,user,1,'AULA',[(1,'10','8')],key); db.commit()
        assert db.get(Product,1).stock==20; assert db.get(Product,1).cost==7
        assert purchase.total==80
        receive_purchase(db,user,1,'AULA',[(1,'10','8')],key); db.commit()
        assert db.get(Product,1).stock==20
        assert db.scalar(select(func.sum(Ledger.amount)))==-80

def test_rollback_when_stock_insufficient(app):
    with app.extensions['db_session']() as db:
        user=db.get(User,2); open_cash(db,user,'0'); db.commit()
        with pytest.raises(ValueError,match='Estoque insuficiente'):
            checkout(db,user,{'1':'1','2':'99'},str(uuid4()),{'pix':'1'},'0')
        db.rollback()
        assert db.get(Product,1).stock==10
        assert db.scalar(select(func.count(Sale.id)))==0
        assert db.scalar(select(func.count(Ledger.id)))==0

def test_cancel_restores_stock_once(app):
    with app.extensions['db_session']() as db:
        op=db.get(User,2); admin=db.get(User,1); c=open_cash(db,op,'100'); db.commit()
        sale=checkout(db,op,{'1':'2'},str(uuid4()),{'cash':'20'},'50'); db.commit()
        cancel_sale(db,admin,sale.id,'Cliente desistiu'); db.commit()
        assert db.get(Product,1).stock==10
        assert db.scalar(select(func.sum(Ledger.amount)))==0
        assert cash_totals(db,c)[3]==100
        with pytest.raises(ValueError): cancel_sale(db,admin,sale.id,'Repetição proibida')

def test_closed_cash_prevents_cancel(app):
    with app.extensions['db_session']() as db:
        op=db.get(User,2); open_cash(db,op,'0'); db.commit()
        s=checkout(db,op,{'1':'1'},str(uuid4()),{'pix':'10'},'0'); db.commit()
        close_cash(db,op,'0'); db.commit()
        with pytest.raises(ValueError,match='caixa de origem'): cancel_sale(db,db.get(User,1),s.id,'Cliente desistiu')

def test_fraction_rounding_and_invalid_payments(app):
    with app.extensions['db_session']() as db:
        op=db.get(User,2); open_cash(db,op,'0'); db.commit()
        s=checkout(db,op,{'2':'0.125'},str(uuid4()),{'pix':'0.86'},'0'); db.commit()
        assert s.total==D('.86'); assert db.get(Product,2).stock==D('19.875')
        for cart,payments,received in [({'1':'0.5'},{'pix':'5'},'0'),({'1':'1'},{'pix':'9'},'0'),({'1':'1'},{'cash':'10'},'9'),({'1':'1'},{'pix':'10'},'5')]:
            with pytest.raises(ValueError): checkout(db,op,cart,str(uuid4()),payments,received)
            db.rollback()

@pytest.mark.parametrize('value',['NaN','Infinity','-1','0.001','10000000','abc'])
def test_money_validation(value):
    with pytest.raises(ValueError): number(value)

def test_password_recovery_single_use(app,client):
    with app.extensions['db_session']() as db:
        user=db.get(User,2); reset=new_reset(db,user); db.commit()
    path='/reset/'+reset
    response=post(client,path,{'password':'Nova frase! Escola 2027','confirmation':'Nova frase! Escola 2027'},path)
    assert response.status_code==302
    assert client.get(path).status_code==400
    assert post(client,'/login',{'email':'op@example.test','password':'Nova frase! Escola 2027'}).status_code==302

def test_operator_cannot_read_other_receipt(app,client):
    with app.extensions['db_session']() as db:
        op=db.get(User,2); open_cash(db,op,'0'); db.commit()
        sale=checkout(db,op,{'1':'1'},str(uuid4()),{'pix':'10'},'0'); db.commit(); sid=sale.id
    login(client,'other@example.test'); assert client.get('/sales/'+str(sid)).status_code==403
    assert ('/sales/'+str(sid)).encode() not in client.get('/sales').data

def test_admin_crud_routes(app,client):
    login(client)
    assert post(client,'/masters',{'kind':'category','name':'Congelados'},'/masters').status_code==302
    assert post(client,'/masters',{'kind':'supplier','name':'Fornecedor B','contact':'Escola'},'/masters').status_code==302
    assert post(client,'/products',{'sku':'9001','name':'Sorvete','category_id':'2','unit':'UN','price':'15','cost':'9','minimum':'3','active':'on'},'/products').status_code==302
    assert post(client,'/stock',{'product_id':'3','balance':'10','reason':'Inventário inicial','current_password':PASSWORD},'/stock').status_code==302
    assert post(client,'/users',{'name':'Caixa B','email':'b@example.test','role':'operator','password':'Frase teste! Escola 2026','current_password':PASSWORD},'/users').status_code==302
    assert post(client,'/finance',{'kind':'expense','description':'Despesa de teste','amount':'12.50','current_password':PASSWORD},'/finance').status_code==302
    with app.extensions['db_session']() as db:
        assert db.get(Product,3).stock==10; assert db.get(User,4).role=='operator'

def test_unique_open_cash(app):
    with app.extensions['db_session']() as db:
        u=db.get(User,2); open_cash(db,u,'0'); db.commit()
        with pytest.raises(ValueError): open_cash(db,u,'0')

def test_report_date_uses_sao_paulo_even_on_sqlite(app,client):
    from datetime import datetime,timezone
    with app.extensions['db_session']() as db:
        op=db.get(User,2);open_cash(db,op,'0');db.commit()
        earlier=checkout(db,op,{'1':'1'},str(uuid4()),{'pix':'10'},'0')
        earlier.created_at=datetime(2026,10,29,2,30,tzinfo=timezone.utc) # 28/10 23h30 São Paulo
        db.commit()
        included=checkout(db,op,{'1':'1'},str(uuid4()),{'pix':'10'},'0')
        included.created_at=datetime(2026,10,29,3,30,tzinfo=timezone.utc) # 29/10 00h30 São Paulo
        db.commit(); first=earlier.id; second=included.id
    login(client)
    html=client.get('/sales?start=2026-10-29&end=2026-10-29').data
    assert f'href="/sales/{first}"'.encode() not in html
    assert f'href="/sales/{second}"'.encode() in html

def test_reauthentication_and_bad_payment_leave_db_unchanged(app,client):
    login(client)
    assert post(client,'/stock',{'product_id':'1','balance':'5','reason':'Teste ajuste','current_password':'wrong'},'/stock').status_code==400
    post(client,'/cash',{'action':'open','opening':'0'},'/cash')
    post(client,'/pos',{'action':'add','sku':'1001','quantity':'1'},'/pos')
    with client.session_transaction() as s: key=s['sale_key']
    assert post(client,'/checkout',{'key':key,'pix':'9'},'/pos').status_code==400
    with app.extensions['db_session']() as db:
        assert db.get(Product,1).stock==10
        assert db.scalar(select(func.count(Sale.id)))==0
