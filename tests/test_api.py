"""
Testes de Automação - Sistema de Controle Financeiro
Projeto Faculdade
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db, Usuario, Categoria, Transacao
from main import app
from auth import gerar_hash_senha

# Banco de dados de teste em memória
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_financeiro.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def registrar_e_logar(email="teste@faculdade.com", senha="teste123", nome="Aluno Teste"):
    # Registro
    r = client.post("/api/auth/register", json={"nome": nome, "email": email, "senha": senha})
    assert r.status_code == 201, f"Registro falhou: {r.text}"
    # Login
    r = client.post("/api/auth/login", data={"username": email, "password": senha})
    assert r.status_code == 200, f"Login falhou: {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==================== TESTES DE AUTENTICAÇÃO ====================
class TestAuth:
    def test_registro_sucesso(self):
        r = client.post("/api/auth/register", json={
            "nome": "Maria Silva",
            "email": "maria@teste.com",
            "senha": "senha123"
        })
        assert r.status_code == 201
        data = r.json()
        assert data["nome"] == "Maria Silva"
        assert data["email"] == "maria@teste.com"
        assert "id" in data

    def test_registro_email_duplicado(self):
        client.post("/api/auth/register", json={
            "nome": "João", "email": "joao@teste.com", "senha": "senha123"
        })
        r = client.post("/api/auth/register", json={
            "nome": "João 2", "email": "joao@teste.com", "senha": "senha456"
        })
        assert r.status_code == 400
        assert "já cadastrado" in r.json()["detail"].lower()

    def test_login_sucesso(self):
        client.post("/api/auth/register", json={
            "nome": "Pedro", "email": "pedro@teste.com", "senha": "abc123"
        })
        r = client.post("/api/auth/login", data={
            "username": "pedro@teste.com", "password": "abc123"
        })
        assert r.status_code == 200
        assert "access_token" in r.json()
        assert r.json()["token_type"] == "bearer"

    def test_login_senha_errada(self):
        client.post("/api/auth/register", json={
            "nome": "Ana", "email": "ana@teste.com", "senha": "correta"
        })
        r = client.post("/api/auth/login", data={
            "username": "ana@teste.com", "password": "errada"
        })
        assert r.status_code == 401

    def test_me_autenticado(self):
        headers = registrar_e_logar()
        r = client.get("/api/auth/me", headers=headers)
        assert r.status_code == 200
        assert r.json()["email"] == "teste@faculdade.com"

    def test_me_sem_token(self):
        r = client.get("/api/auth/me")
        assert r.status_code == 401


# ==================== TESTES DE CATEGORIAS ====================
class TestCategorias:
    def test_listar_categorias_padrao(self):
        headers = registrar_e_logar()
        r = client.get("/api/categorias", headers=headers)
        assert r.status_code == 200
        cats = r.json()
        assert len(cats) >= 5  # Categorias padrão criadas no registro
        nomes = [c["nome"] for c in cats]
        assert "Alimentação" in nomes or "Salário" in nomes

    def test_criar_categoria(self):
        headers = registrar_e_logar()
        r = client.post("/api/categorias", headers=headers, json={
            "nome": "Investimentos", "tipo": "receita"
        })
        assert r.status_code == 201
        assert r.json()["nome"] == "Investimentos"
        assert r.json()["tipo"] == "receita"

    def test_deletar_categoria(self):
        headers = registrar_e_logar()
        r = client.post("/api/categorias", headers=headers, json={
            "nome": "Temporária", "tipo": "despesa"
        })
        cat_id = r.json()["id"]
        r = client.delete(f"/api/categorias/{cat_id}", headers=headers)
        assert r.status_code == 204
        # Verifica que sumiu
        r = client.get("/api/categorias", headers=headers)
        ids = [c["id"] for c in r.json()]
        assert cat_id not in ids


# ==================== TESTES DE TRANSAÇÕES ====================
class TestTransacoes:
    def test_criar_receita(self):
        headers = registrar_e_logar()
        r = client.post("/api/transacoes", headers=headers, json={
            "descricao": "Salário mensal",
            "valor": 3500.00,
            "tipo": "receita"
        })
        assert r.status_code == 201
        data = r.json()
        assert data["descricao"] == "Salário mensal"
        assert data["valor"] == 3500.00
        assert data["tipo"] == "receita"

    def test_criar_despesa(self):
        headers = registrar_e_logar()
        r = client.post("/api/transacoes", headers=headers, json={
            "descricao": "Almoço",
            "valor": 45.50,
            "tipo": "despesa"
        })
        assert r.status_code == 201
        assert r.json()["tipo"] == "despesa"

    def test_listar_transacoes(self):
        headers = registrar_e_logar()
        client.post("/api/transacoes", headers=headers, json={
            "descricao": "Teste 1", "valor": 100, "tipo": "receita"
        })
        client.post("/api/transacoes", headers=headers, json={
            "descricao": "Teste 2", "valor": 50, "tipo": "despesa"
        })
        r = client.get("/api/transacoes", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_filtrar_por_tipo(self):
        headers = registrar_e_logar()
        client.post("/api/transacoes", headers=headers, json={
            "descricao": "Receita", "valor": 200, "tipo": "receita"
        })
        client.post("/api/transacoes", headers=headers, json={
            "descricao": "Despesa", "valor": 80, "tipo": "despesa"
        })
        r = client.get("/api/transacoes?tipo=receita", headers=headers)
        assert r.status_code == 200
        assert all(t["tipo"] == "receita" for t in r.json())

    def test_atualizar_transacao(self):
        headers = registrar_e_logar()
        r = client.post("/api/transacoes", headers=headers, json={
            "descricao": "Original", "valor": 100, "tipo": "despesa"
        })
        trans_id = r.json()["id"]
        r = client.put(f"/api/transacoes/{trans_id}", headers=headers, json={
            "descricao": "Atualizada", "valor": 150
        })
        assert r.status_code == 200
        assert r.json()["descricao"] == "Atualizada"
        assert r.json()["valor"] == 150

    def test_deletar_transacao(self):
        headers = registrar_e_logar()
        r = client.post("/api/transacoes", headers=headers, json={
            "descricao": "Para deletar", "valor": 30, "tipo": "despesa"
        })
        trans_id = r.json()["id"]
        r = client.delete(f"/api/transacoes/{trans_id}", headers=headers)
        assert r.status_code == 204
        r = client.get("/api/transacoes", headers=headers)
        assert len(r.json()) == 0

    def test_valor_invalido(self):
        headers = registrar_e_logar()
        r = client.post("/api/transacoes", headers=headers, json={
            "descricao": "Negativo", "valor": -10, "tipo": "despesa"
        })
        assert r.status_code == 422  # Validation error


# ==================== TESTES DE RESUMO / DASHBOARD ====================
class TestResumo:
    def test_resumo_vazio(self):
        headers = registrar_e_logar()
        r = client.get("/api/resumo", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["saldo"] == 0
        assert data["total_receitas"] == 0
        assert data["total_despesas"] == 0
        assert data["quantidade_transacoes"] == 0

    def test_resumo_com_transacoes(self):
        headers = registrar_e_logar()
        client.post("/api/transacoes", headers=headers, json={
            "descricao": "Salário", "valor": 5000, "tipo": "receita"
        })
        client.post("/api/transacoes", headers=headers, json={
            "descricao": "Aluguel", "valor": 1500, "tipo": "despesa"
        })
        client.post("/api/transacoes", headers=headers, json={
            "descricao": "Mercado", "valor": 400, "tipo": "despesa"
        })
        r = client.get("/api/resumo", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total_receitas"] == 5000
        assert data["total_despesas"] == 1900
        assert data["saldo"] == 3100
        assert data["quantidade_transacoes"] == 3


# ==================== TESTE DE ISOLAMENTO ENTRE USUÁRIOS ====================
class TestIsolamento:
    def test_usuarios_nao_veem_dados_uns_dos_outros(self):
        headers1 = registrar_e_logar("user1@teste.com", "senha1", "User 1")
        headers2 = registrar_e_logar("user2@teste.com", "senha2", "User 2")

        # User1 cria transação
        client.post("/api/transacoes", headers=headers1, json={
            "descricao": "Só do user1", "valor": 999, "tipo": "receita"
        })

        # User2 não deve ver
        r = client.get("/api/transacoes", headers=headers2)
        assert r.status_code == 200
        assert len(r.json()) == 0

        # User1 vê
        r = client.get("/api/transacoes", headers=headers1)
        assert len(r.json()) == 1
        assert r.json()[0]["descricao"] == "Só do user1"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
