# Validação da entrega

## Executado neste ambiente

- 20 testes pytest aprovados em Python 3.12, usando bancos SQLite temporários isolados.
- Migração Alembic aplicada em banco novo e execução da carga inicial de 12 produtos.
- Compilação dos módulos Python e verificação de sintaxe JavaScript com node --check.
- Renderização das páginas Jinja2 por requisições do cliente de teste Flask, em ambos os perfis.
- Geração offline do SQL PostgreSQL completo pela migração Alembic.
- PDF do roteiro renderizado em 11 páginas e revisado visualmente.

## Cobertura automatizada

Login/CSRF/bloqueio, páginas e autorização, reautenticação, venda com quatro meios, troco,
idempotência, recebimento/custo médio, rollback por estoque insuficiente, cancelamento e estorno,
restrição de caixa fechado, quantidade fracionada e arredondamento, rejeição de números inválidos,
recuperação de uso único, proteção de tickets por operador, cadastros e ajustes, unicidade de caixa
aberto e filtro de datas no fuso America/Sao_Paulo.

## Verificações que dependem do aluno

A publicação na conta Vercel, o PostgreSQL remoto, a entrega de e-mail SMTP, a concorrência real
entre conexões PostgreSQL e a impressão no equipamento físico não foram executados nesta entrega.
A geração do SQL PostgreSQL não equivale a um teste de integração em servidor PostgreSQL.
A tentativa de revisão automatizada no Chromium foi impedida pela restrição de criação de sockets
do ambiente; não se declara teste visual de navegador concluído. Os temas e o gráfico devem ser
conferidos pelo aluno em seu navegador, seguindo o roteiro de aceitação.

Use docs/AVALIACAO_PROFESSOR.md para confirmar a instalação externa ponta a ponta.
