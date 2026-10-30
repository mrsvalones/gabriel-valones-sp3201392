"""Cria .env local sem sobrescrever configuração existente."""
from pathlib import Path
import secrets
root=Path(__file__).resolve().parent.parent
target=root/'.env'
if target.exists():
    print('.env já existe; preservado.')
else:
    data=(root/'.env.example').read_text().replace('SUBSTITUA_POR_64_CARACTERES_ALEATORIOS',secrets.token_hex(32))
    target.write_text(data)
    try: target.chmod(0o600)
    except OSError: pass
    print('.env local criado com segredo exclusivo e SQLite de desenvolvimento.')
