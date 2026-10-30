# Arquitetura e conteúdos da disciplina

## MVC e MPA

| Conceito | Implementação e ponto de estudo |
|---|---|
| Model | mercado/models.py: entidades, propriedades, tipos, relacionamentos e restrições. |
| View | templates/*.html: Jinja2, herança, macros, condicionais, laços e escape automático. |
| Controller | mercado/controllers: recebe HTTP, autentica/autoriza, valida, chama serviços e escolhe resposta. |
| Serviço | mercado/services/operations.py: regras de compra/venda, estoque e fechamento. |
| MPA | GET retorna página HTML completa; POST processa formulário; sucesso redireciona (Post/Redirect/Get). |
| ORM | SQLAlchemy: objetos persistidos, select(), relationships, ForeignKey, session/commit/rollback. |
| Middleware | before_request abre sessão ORM e identifica usuário; after_request define cabeçalhos; teardown fecha a sessão. |
| Sessão web | Cookie assinado Flask guarda ID/versão do usuário, tema e carrinho limitado. Não armazena senha. |
| Validação | Servidor verifica Decimal, estoque, unidade, usuário, perfis, total e recebido. HTML auxilia a entrada. |
| Autenticação | Login com hash scrypt; bloqueio temporário persistido em banco. |
| Autorização | Decoradores login_required/admin_required e verificação de proprietário nas vendas. |
| Reautenticação | Confirma senha para fechamento, sangria, suprimento, cancelamento, ajuste, contas e financeiro avulso. |
| Erros | Páginas de erro sem expor SQL/credenciais; rollback antes da resposta. |
| Migração | Alembic 0001 define esquema congelado; não há create_all por requisição. |
| Interface | Duas folhas CSS; JavaScript progressivo; SVG para gráfico, sem CDN externa. |
| Relatórios | Consulta por período, Excel em memória e impressão/PDF no navegador. |

JavaScript (.js) é a linguagem do navegador. **Java (.java) não é necessário** para uma aplicação Flask Python; por isso o pacote contém .py, .html, .css e .js, não um segundo backend Java.

## Dicionário de tabelas

| Tabela | Papel e vínculos |
|---|---|
| users | Administradores/operadores, hash, status, versão de sessão e bloqueio. |
| categories | Categorias de produtos. |
| suppliers | Fornecedores fictícios. |
| products | SKU único; categoria; unidade; preço/custo/saldo/mínimo e status. |
| cash_sessions | Abertura/fechamento por usuário, fundo, contado/esperado/diferença. |
| cash_movements | Suprimento/sangria e motivo em um caixa. |
| sales | Venda, usuário, caixa, chave única, total, recebido, troco e status. |
| sale_items | Produto e fotografia de nome, SKU, unidade, preço/custo/quantidade/subtotal na venda. |
| payments | Meio, valor e referência fictícia de pagamento da venda. |
| purchases | Fornecedor, usuário, referência, chave única e total da compra. |
| purchase_items | Produtos, quantidades, custos e subtotais recebidos. |
| stock_movements | Produto, usuário, variação, saldo resultante, motivo e instante. |
| ledger | Entradas/saídas, usuário e vínculo opcional com venda/compra. |
| audit | Eventos sensíveis, usuário e instante. |
| reset_tokens | Hash do token, usuário, expiração e uso. |
| alembic_version | Tabela técnica da versão do esquema, criada pelo Alembic. |

Relacionamentos principais: categoria 1:N produtos; usuário 1:N caixas; caixa 1:N vendas; venda 1:N itens e pagamentos; fornecedor 1:N compras; compra 1:N itens; produto 1:N movimentos. Exclusões são restritas para preservar integridade referencial.

Preço histórico da venda é uma fotografia intencional: alterar o cadastro não muda o ticket antigo. Quantidade utiliza Numeric(12,3); moeda Numeric(12,2). Cálculos usam Decimal e arredondamento half-up por linha. Float aparece somente na representação do gráfico/Excel, não na gravação de moeda.

## Transação de venda

O serviço bloqueia o caixa e os produtos com SELECT FOR UPDATE no PostgreSQL, em ordem de ID. Verifica estoque e soma dos pagamentos, cria venda e filhos, baixa saldos, registra movimentos e financeiro. O controller dá um único commit. Falha provoca rollback e nenhuma venda parcial.

A chave UUID é única no banco. Reenvio do mesmo formulário concluído retorna o ticket existente, sem duplicar a baixa. Há uma segunda consulta da chave após o bloqueio do caixa. Caixa aberto por usuário tem índice único parcial. Compras também possuem chave única e bloqueio para repetição do formulário.

Cancelamento e venda bloqueiam o caixa antes dos produtos. O banco protege integridade; a interface desabilitar um botão é apenas conveniência. SQLite não implementa os mesmos bloqueios de linha; use-o apenas no desenvolvimento individual. Os testes locais não substituem um teste concorrente em PostgreSQL.

## Limites e extensões para estudo

O escopo implementa o fluxo acadêmico especificado. Não equivale a certificação fiscal ou a um ERP comercial completo. Possíveis trabalhos posteriores: migração de permissões para tabelas, paginação de relatórios muito grandes, sessão centralizada, limites por IP em gateway, lotes/validade, contas a pagar/receber, estorno parcial, cadastro de clientes e testes de concorrência reais.

Nenhuma dessas extensões é necessária para executar a versão entregue. Não altere os indicadores financeiros para chamar saldo de lucro; antes modele custo da mercadoria vendida e despesas por competência.
