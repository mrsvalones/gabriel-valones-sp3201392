# Manual de operação — Mercado Viva

## Perfis

Administrador: todos os módulos, criação de contas, cadastro de produtos/categorias/fornecedores, compras, ajustes, relatórios gerais, financeiro e auditoria. Também pode operar seu próprio caixa.

Operador: login, senha, seu caixa, seu carrinho, suas vendas e seus tickets. Não acessa cadastros, financeiro geral ou vendas de outros operadores. As restrições são verificadas nas rotas do servidor, não apenas nos menus.

## Sequência de implantação da loja fictícia

1. Crie categorias e fornecedores em Categorias e fornecedores.
2. Cadastre produtos com SKU único, unidade UN ou KG, preço e estoque mínimo.
3. Receba uma compra: selecione fornecedor, referência e itens, quantidade e custo unitário.
4. Confira Estoque e Financeiro. Produtos novos começam com saldo zero até a entrada.
5. Crie operadores e a conta de avaliação do professor em Equipe e acessos.

A carga seed faz os passos 1 a 3 com dados fictícios. O estoque mínimo alerta quando o saldo é menor ou igual ao valor cadastrado. Inativar produto impede novas vendas/compras, preservando registros anteriores.

## Caixa e venda

1. Faça login como operador. Acesse Movimento de caixa e informe o fundo inicial.
2. Entre na Frente de caixa. Digite o SKU ou selecione na lista; informe quantidade.
3. Para UN, use números inteiros; KG aceita até três casas. Para corrigir quantidade já inserida, remova a linha e adicione novamente.
4. Adicione outros produtos. O carrinho aceita até 40 produtos distintos. O total é recalculado no servidor; preço enviado pelo navegador é ignorado.
5. Escolha o preenchimento automático do total em dinheiro, débito, crédito ou Pix; ou divida o total nos quatro campos.
6. A soma dos meios deve ser exatamente igual ao total. Em dinheiro, o campo da forma de pagamento representa a parcela da venda, enquanto Recebido em espécie representa as cédulas/moedas entregues.
7. Exemplo de pagamento misto: venda R$ 39,70; dinheiro R$ 19,70; Pix R$ 20,00; recebido em espécie R$ 20,00; troco R$ 0,30.
8. Confirme. O servidor verifica caixa, produtos ativos, saldo e valores, grava venda/itens/pagamentos, baixa estoque e lança o financeiro em uma única transação.
9. O comprovante abre com número, data, operador, itens, meios, referências simuladas, recebido e troco.

Não há coleta de PAN, CVV, chave Pix, CPF de cliente ou credenciais bancárias. Não há confirmação de instituição financeira: todos os registros são explicitamente fictícios. Os identificadores SIM não são códigos de autorização reais.

## Ticket e relatórios

No ticket, use Imprimir ticket / salvar PDF. Na caixa de impressão do navegador, selecione impressora ou Salvar como PDF. Para impressora térmica, use papel 80 mm, escala próxima de 100%, margens mínimas e desative cabeçalhos/rodapés do navegador. Ajuste conforme o driver. A área útil do ticket é 76 mm.

O ticket é profissional na organização visual, mas **sem valor fiscal**. Não possui CNPJ inventado, chave fiscal, código Pix pagável ou QR de pagamento. Não substitui NFC-e.

Em Vendas e relatórios, escolha início/fim e status. O intervalo é inclusivo nas datas, em America/Sao_Paulo, com máximo de 367 dias. O Excel respeita período, status e permissões. Valores são numéricos no arquivo; os textos permanecem literais. O botão de impressão permite PDF do relatório sem salvar arquivos no disco da Vercel.

O painel exibe faturamento das vendas concluídas, quantidade e ticket médio; o gráfico de barras mostra cada dia, incluindo dias com zero. O quadro de dados acessível permite conferir os números sem depender do gráfico.

## Fechamento

Dinheiro esperado = fundo inicial + parcelas das vendas em dinheiro + suprimentos − sangrias.

Cartões e Pix são mostrados separadamente e não entram na contagem física. O troco já foi descontado: soma-se a parcela em dinheiro da venda, não o dinheiro bruto recebido.

Informe o total físico contado, confirme sua senha e feche. Diferença = contado − esperado: positiva é sobra, negativa é falta. O registro fechado é preservado. Abra outro movimento para continuar vendendo. Há no máximo um caixa aberto por usuário.

Suprimentos e sangrias exigem motivo e reautenticação. Sangria não pode superar o saldo esperado disponível. São transferências de numerário, não receita/despesa do livro financeiro geral.

## Compras, estoque e financeiro

Uma compra pode conter múltiplos produtos; use Adicionar linha para ampliar a tabela. Não repita o mesmo produto em duas linhas: consolide sua quantidade. A confirmação representa recebimento e pagamento à vista simulados.

Custo médio = (saldo anterior × custo anterior + quantidade recebida × novo custo) ÷ saldo resultante. O resultado monetário é arredondado a centavos. Cada entrada, saída, ajuste e cancelamento grava movimento com saldo resultante.

Estoque permite filtro por categoria, saldo/mínimo e valor a custo por produto. O resumo por categoria informa quantidade de produtos distintos e valor total, sem somar KG com UN. O histórico mostra os últimos 100 movimentos gerais, mesmo quando há filtro na posição atual.

Ajuste de estoque é a definição do saldo contado, com motivo e senha do administrador. Não é uma compra e não cria automaticamente saída financeira. Não representa apuração contábil de perdas.

Financeiro exibe saldo anterior, entradas, saídas e saldo acumulado. Inclui vendas, estornos, compras e lançamentos avulsos. Não é cálculo de lucro: compra de estoque e venda são fluxos em momentos diferentes. Cartões são tratados como liquidados imediatamente; não há agenda de recebíveis nem taxas.

## Cancelamento

Administrador abre o ticket e expande Cancelar e estornar venda. Deve informar motivo e senha atual. O caixa original precisa estar aberto. O sistema marca cancelada, repõe estoque e cria lançamento financeiro negativo, mantendo a venda e pagamentos originais para rastreabilidade. Relatórios de vendas concluídas e totais do caixa excluem canceladas. Não existe exclusão física, devolução parcial nem cancelamento de compra nesta versão.

## Credenciais

O cadastro público é fechado. Usuários são criados por administrador reautenticado ou pelo terminal autorizado. Senhas usam hash scrypt com salt, nunca texto simples. Cinco falhas consecutivas bloqueiam a conta por 15 minutos. Sessões expiram após 30 minutos sem renovação por atividade e recebem cookies HttpOnly, SameSite=Lax e Secure em produção.

Alterar/recuperar senha invalida sessões anteriores pelo número de versão da conta. Recuperação usa token aleatório, com apenas o hash no banco, uso único e 20 minutos. SMTP é opcional; o responsável pode gerar um link pelo terminal. Contas de operador podem ser desativadas apenas depois de fechar seu caixa. Administradores não são desativados pela interface desta versão.

## Temas e acessibilidade

No cabeçalho, selecione Aurora ou Tropical e clique Aplicar. A seleção fica na sessão. Cada tema usa um arquivo CSS completo, sem depender do outro. Navegação por teclado, foco visível, rótulos, tabelas e adaptação para telas estreitas estão presentes. JavaScript melhora gráfico e preenchimento de pagamento; as regras fundamentais continuam no Python.
