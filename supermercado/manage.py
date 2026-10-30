"""Comandos administrativos locais. Nunca publique senhas no repositório."""
import argparse, getpass, os
from sqlalchemy import select
from mercado import create_app
from mercado.models import User,Category,Supplier,Product
from mercado.security import password_policy
from mercado.controllers.auth import new_reset
from mercado.services.operations import audit,receive_purchase
from uuid import uuid4

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['create-admin','create-operator','seed','reset-link','check-db'])
    args=parser.parse_args(); app=create_app()
    with app.extensions['db_session']() as db:
        if args.command in ('create-admin','create-operator'):
            email=input('E-mail: ').strip().lower(); name=input('Nome: ').strip()
            if not name or len(name)>100 or '@' not in email or len(email)>180: raise ValueError('Nome/e-mail inválidos.')
            if db.scalar(select(User).where(User.email==email)): raise ValueError('E-mail já cadastrado.')
            password=getpass.getpass('Frase-senha (15 a 128 caracteres): ')
            if password!=getpass.getpass('Repita: '): raise ValueError('Senhas não coincidem.')
            user=User(name=name,email=email,password_hash=password_policy(password),role='admin' if args.command=='create-admin' else 'operator')
            db.add(user); db.flush(); audit(db,user,'Usuário criado pelo terminal'); db.commit()
            print('Usuário criado, sem senha padrão.')
        elif args.command=='check-db':
            print('Conexão e consulta OK. Usuários:',len(db.scalars(select(User)).all()))
        elif args.command=='reset-link':
            user=db.scalar(select(User).where(User.email==input('E-mail da conta: ').strip().lower()).with_for_update())
            if not user or not user.active: raise ValueError('Conta ativa não encontrada.')
            token=new_reset(db,user); audit(db,user,'Link de recuperação emitido pelo terminal'); db.commit()
            print('Link de uso único, válido por 20 minutos. Entregue em canal privado:')
            print(app.config['APP_URL'].rstrip('/')+'/reset/'+token)
        elif args.command=='seed':
            admin=db.scalar(select(User).where(User.role=='admin',User.active.is_(True)).order_by(User.id))
            if not admin: raise ValueError('Crie o administrador primeiro.')
            if db.scalar(select(Product.id).limit(1)): raise ValueError('Seed só pode ser executado em catálogo vazio.')
            names=['Mercearia','Bebidas','Hortifruti','Limpeza','Laticínios']
            cats={}
            for name in names:
                c=db.scalar(select(Category).where(Category.name==name)) or Category(name=name)
                db.add(c); db.flush(); cats[name]=c.id
            supplier=db.scalar(select(Supplier).where(Supplier.name=='Distribuidora Escola (fictícia)')) or Supplier(name='Distribuidora Escola (fictícia)',contact='Contato de demonstração')
            db.add(supplier); db.flush()
            data=[('1001','Arroz 5 kg','Mercearia','UN','27.90','21.00','30'),('1002','Feijão 1 kg','Mercearia','UN','8.50','5.90','40'),('1003','Café 500 g','Mercearia','UN','19.90','14.00','25'),('1004','Macarrão 500 g','Mercearia','UN','5.20','3.50','50'),('2001','Água mineral 1,5 L','Bebidas','UN','3.50','1.80','60'),('2002','Suco integral 1 L','Bebidas','UN','12.90','8.20','20'),('3001','Banana prata','Hortifruti','KG','6.90','3.80','25'),('3002','Tomate','Hortifruti','KG','8.90','5.00','20'),('4001','Detergente 500 ml','Limpeza','UN','2.90','1.40','50'),('4002','Sabão em pó 1 kg','Limpeza','UN','14.90','10.20','20'),('5001','Leite integral 1 L','Laticínios','UN','5.90','4.00','40'),('5002','Queijo muçarela','Laticínios','KG','44.90','29.00','10')]
            rows=[]
            for sku,name,cat,unit,price,cost,qty in data:
                p=Product(sku=sku,name=name,category_id=cats[cat],unit=unit,price=price,cost=0,stock=0,minimum=5,active=True)
                db.add(p); db.flush(); rows.append((p.id,qty,cost))
            receive_purchase(db,admin,supplier.id,'CARGA-DIDATICA-INICIAL',rows,str(uuid4()))
            db.commit(); print('12 produtos, 5 categorias e compra inicial criados. A compra gera saída financeira simulada.')

if __name__=='__main__':
    try: main()
    except ValueError as error: raise SystemExit(str(error))
