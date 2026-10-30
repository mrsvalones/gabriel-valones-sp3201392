# Roteiro de avaliação do professor

**Acesso:** URL estável entregue pelo aluno + conta administrativa exclusiva. Use dados fictícios. Se a URL abrir uma tela da Vercel em vez do supermercado, solicite ao aluno corrigir a proteção da produção.

## Rubrica sugerida — 10 pontos

| Critério | Pontos |
|---|---:|
| Publicação acessível, nome/prontuário na URL e persistência após redeploy | 1,0 |
| MVC/MPA/ORM, organização e capacidade de explicar o código | 1,5 |
| Autenticação, perfis, CSRF, política e recuperação de senha | 1,5 |
| Cadastros, compras, estoque, categorias e integridade | 1,5 |
| Venda, meios simulados, troco e consistência transacional | 1,5 |
| Abertura, sangria, suprimento e fechamento com diferença | 1,0 |
| Gráfico, financeiro, Excel e ticket | 1,0 |
| Dois temas, usabilidade, documentação e testes | 1,0 |

## Cenário integrado reproduzível

Use um SKU novo para não depender dos saldos existentes. Registre os números gerados e opere em data coberta pelos filtros.

1. Administrador: crie categoria Avaliação e fornecedor Fornecedor Avaliação.
2. Cadastre SKU AVAL-01, nome Produto Avaliação, UN, preço R$ 10,00, custo inicial zero, mínimo 2. Saldo inicial zero.
3. Receba compra de 10 unidades a R$ 6,00. Esperado: estoque 10; custo médio 6; saída financeira R$ 60,00.
4. Operador: abra caixa com R$ 100,00; tente abrir novamente. Deve impedir duplicidade.
5. Venda 2 unidades. Total R$ 20,00. Informe dinheiro 5, débito 5, crédito 5, Pix 5 e recebido em espécie 10. Troco R$ 5,00; estoque 8; caixa esperado R$ 105,00.
6. Confirme que o ticket contém quatro referências SIM e a indicação sem valor fiscal. Não deve pedir dados de cartão ou chave Pix.
7. Faça suprimento R$ 20,00 e sangria R$ 15,00. Caixa esperado: R$ 110,00.
8. Tente vender 99 unidades. Deve recusar; saldo e financeiro permanecem inalterados.
9. Administrador: cancele a venda anterior, enquanto o caixa está aberto. Esperado: estoque 10, estorno financeiro R$ 20,00, caixa esperado R$ 105,00 (fundo 100 + suprimento 20 − sangria 15).
10. Operador: venda 1 unidade no Pix por R$ 10,00. Estoque 9; dinheiro esperado continua R$ 105,00.
11. Feche informando R$ 104,00. Diferença esperada −R$ 1,00. Vendas nesse caixa encerrado não podem mais ser canceladas.
12. Consulte relatório: uma venda cancelada de R$ 20,00 e uma concluída de R$ 10,00. Total concluído R$ 10,00. Gráfico inclui somente a concluída.
13. Delta financeiro apenas destas operações: compra −60, venda +20, estorno −20, venda +10 = **−R$ 50,00**. Suprimento/sangria não entram no financeiro geral. Compare diferenças se houver outros registros no período.
14. Faça nova compra de 1 unidade a R$ 8,00. Saldo 10; custo médio (9 × 6 + 1 × 8)/10 = R$ 6,20. Delta financeiro acumulado deste cenário: −R$ 58,00.
15. Confira Excel, impressão do relatório e do ticket nos dois temas.

## Testes de acesso e credenciais

- Operador não pode acessar /users, /stock, /purchases ou /finance digitando a URL diretamente: deve receber 403.
- Outro operador não pode abrir o ticket do primeiro.
- Logout impede acesso às telas protegidas.
- Cadastro com senha curta deve ser rejeitado.
- Alterar senha exige senha atual e encerra sessões anteriores.
- Link de recuperação expira e só funciona uma vez.
- Operador com caixa aberto não pode ser desativado.

## Evidências e defesa do código

Peça ao aluno indicar a rota POST /checkout, o serviço checkout, a entidade Sale e o template receipt.html. Solicite a explicação de onde estão commit/rollback e por que preço/estoque são validados no servidor. Pergunte por que SQLite não deve ser usado na publicação e por que o banco não pode ficar apenas no cookie ou no filesystem da função.

Solicite uma venda antes/depois de redeploy e a consulta ao mesmo ticket. Não peça a senha de conexão PostgreSQL, SECRET_KEY, token GitHub ou acesso à conta pessoal do aluno.

Os testes de integração incluídos podem ser executados pelo aluno com `python -m pytest -q`. A avaliação remota pelo professor é um passo adicional: confirma contas, infraestrutura, domínio e banco configurados pelo aluno.
