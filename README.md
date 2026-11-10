# Sistema de Controle Financeiro

**Projeto de Faculdade** – Full Stack (Frontend + Backend + Banco de Dados)

Sistema completo de controle financeiro pessoal com autenticação, CRUD de transações e categorias, dashboard com resumo e gráficos.

## Arquitetura

| Camada | Tecnologia |
| --- | --- |
| Frontend | HTML5 + Tailwind CSS + Vanilla JS + Chart.js |
| Backend | Python + FastAPI + SQLAlchemy |
| Banco | SQLite (`financeiro.db`) |
| Auth | JWT + Bcrypt |
| Testes | Pytest + TestClient |

## Funcionalidades

- Cadastro e Login de usuários (JWT)
- Dashboard com Saldo, Receitas, Despesas e quantidade de transações
- CRUD de Transações (receitas e despesas)
- CRUD de Categorias
- Gráficos por categoria
- Filtros por tipo de transação
- Isolamento de dados por usuário
- Usuário demo pré-cadastrado
- Testes automatizados com Pytest

## Como rodar

```bash
pip install -r requirements.txt
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Em outro terminal:

```bash
cd frontend
python -m http.server 3000
```

Abra http://localhost:3000

Documentação da API: http://localhost:8000/docs

Credenciais demo:

```
Email: demo@faculdade.com
Senha: demo123
```

## Testes

```bash
pytest tests/test_api.py -v
```

## Estrutura

```
backend/     API FastAPI, modelos, auth
frontend/    interface (index.html)
tests/       testes automatizados
```
