# Mercado Viva — supermercado acadêmico em Python

Projeto completo para Laboratório de Programação 1, com MVC, MPA, Flask/Jinja2, ORM SQLAlchemy e PostgreSQL na Vercel. Professor: Celso Gonsalez Saes.

## Comece aqui

Leia **docs/ROTEIRO_ALUNO.md** para instalação, criação do banco, GitHub, Vercel e domínio; **docs/MANUAL_SISTEMA.md** para operar; **docs/ARQUITETURA.md** para estudar o código; **docs/AVALIACAO_PROFESSOR.md** para validar.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/setup_local.py
python -m alembic upgrade head
python manage.py create-admin
python manage.py create-operator
python manage.py seed
python app.py
```

Abra http://127.0.0.1:5000. Não há credenciais padrão. Os dois comandos de criação de usuário solicitam nome, e-mail e senha no terminal. O banco SQLite local é apenas para aprendizagem individual; para Vercel use PostgreSQL externo conforme o roteiro.

## Módulos entregues

- Login, perfis administrador/operador, hash scrypt, CSRF, bloqueio temporário após falhas, reautenticação, alteração e recuperação de senha.
- Produtos, categorias, fornecedores, ativação/inativação de produtos e operadores.
- Compras com múltiplos itens, recebimento, custo médio ponderado e saída financeira.
- Estoque por produto/categoria, estoque mínimo, ajustes justificados e histórico.
- Caixa por operador, abertura, suprimento, sangria, fechamento, esperado/contado/diferença.
- Carrinho MPA, preço validado no servidor, produtos UN/KG, transação atômica e proteção contra repetição da venda.
- Dinheiro, débito, crédito e Pix simulados; pagamento combinado e troco.
- Cancelamento administrativo com caixa aberto, devolução ao estoque e estorno financeiro.
- Gráfico de barras, relatórios por período, exportação Excel, impressão/PDF pelo navegador e ticket de 80 mm.
- Duas folhas CSS completas: Aurora e Tropical, com o logo IFSP fornecido em public/images/ifsp.png; JavaScript progressivo sem dependência de CDN.
- Migração Alembic, SQL PostgreSQL de referência, carga de 12 produtos e testes automatizados.

## Limites definidos do projeto

É um simulador acadêmico, sem emissão fiscal, TEF, adquirente, banco, Pix real ou integração contábil. Crédito e débito são liquidados imediatamente na simulação, sem parcelas, taxas ou conciliação externa. Compras são recebidas e pagas à vista. Não há contas a pagar/receber parceladas, lotes/validade, múltiplas filiais ou devolução parcial. Produtos inativos preservam o histórico. Não se excluem vendas confirmadas: registra-se cancelamento.

O projeto foi preparado para publicação pelo aluno; nenhuma conta, banco remoto ou URL real é criada apenas ao baixar o ZIP. Senhas, conta GitHub, projeto Neon e conta Vercel são individuais. O plano Hobby destina-se ao uso pessoal não comercial; confirme limites e condições vigentes nos painéis.

## Testes

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

A suíte usa bancos temporários isolados. Consulte docs/VALIDACAO.md para os resultados efetivamente verificados na entrega.
