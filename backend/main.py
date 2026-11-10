from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional, List

from database import init_db, get_db, Usuario, Categoria, Transacao, TipoTransacao
from schemas import (
    UsuarioCreate, UsuarioResponse, UsuarioLogin, Token,
    CategoriaCreate, CategoriaResponse,
    TransacaoCreate, TransacaoUpdate, TransacaoResponse,
    ResumoFinanceiro
)
from auth import (
    gerar_hash_senha, verificar_senha, criar_access_token,
    get_usuario_atual, ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(
    title="Sistema de Controle Financeiro",
    description="API completa para gerenciamento de finanças pessoais - Projeto Faculdade",
    version="1.0.0"
)

# CORS para o frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    # Cria categorias padrão se não existirem (para usuário demo)
    db = next(get_db())
    try:
        # Usuário demo
        demo = db.query(Usuario).filter(Usuario.email == "demo@faculdade.com").first()
        if not demo:
            demo = Usuario(
                nome="Usuário Demo",
                email="demo@faculdade.com",
                senha_hash=gerar_hash_senha("demo123")
            )
            db.add(demo)
            db.commit()
            db.refresh(demo)

            # Categorias padrão
            cats = [
                ("Salário", TipoTransacao.receita),
                ("Freelance", TipoTransacao.receita),
                ("Investimentos", TipoTransacao.receita),
                ("Alimentação", TipoTransacao.despesa),
                ("Transporte", TipoTransacao.despesa),
                ("Moradia", TipoTransacao.despesa),
                ("Lazer", TipoTransacao.despesa),
                ("Saúde", TipoTransacao.despesa),
                ("Educação", TipoTransacao.despesa),
                ("Outros", TipoTransacao.despesa),
            ]
            for nome, tipo in cats:
                cat = Categoria(nome=nome, tipo=tipo, usuario_id=demo.id)
                db.add(cat)
            db.commit()
    finally:
        db.close()


# ==================== AUTH ====================
@app.post("/api/auth/register", response_model=UsuarioResponse, status_code=201)
def registrar(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    existe = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    novo = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=gerar_hash_senha(usuario.senha)
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)

    # Cria categorias padrão para o novo usuário
    cats = [
        ("Salário", TipoTransacao.receita),
        ("Freelance", TipoTransacao.receita),
        ("Alimentação", TipoTransacao.despesa),
        ("Transporte", TipoTransacao.despesa),
        ("Moradia", TipoTransacao.despesa),
        ("Lazer", TipoTransacao.despesa),
        ("Outros", TipoTransacao.despesa),
    ]
    for nome, tipo in cats:
        cat = Categoria(nome=nome, tipo=tipo, usuario_id=novo.id)
        db.add(cat)
    db.commit()

    return novo


@app.post("/api/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == form_data.username).first()
    if not usuario or not verificar_senha(form_data.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = criar_access_token(
        data={"sub": usuario.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=UsuarioResponse)
def me(usuario: Usuario = Depends(get_usuario_atual)):
    return usuario


# ==================== CATEGORIAS ====================
@app.get("/api/categorias", response_model=List[CategoriaResponse])
def listar_categorias(
    tipo: Optional[str] = None,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db)
):
    query = db.query(Categoria).filter(Categoria.usuario_id == usuario.id)
    if tipo:
        query = query.filter(Categoria.tipo == tipo)
    return query.order_by(Categoria.nome).all()


@app.post("/api/categorias", response_model=CategoriaResponse, status_code=201)
def criar_categoria(
    cat: CategoriaCreate,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db)
):
    nova = Categoria(nome=cat.nome, tipo=cat.tipo, usuario_id=usuario.id)
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return nova


@app.delete("/api/categorias/{cat_id}", status_code=204)
def deletar_categoria(
    cat_id: int,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db)
):
    cat = db.query(Categoria).filter(
        Categoria.id == cat_id, Categoria.usuario_id == usuario.id
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    db.delete(cat)
    db.commit()
    return None


# ==================== TRANSAÇÕES ====================
@app.get("/api/transacoes", response_model=List[TransacaoResponse])
def listar_transacoes(
    tipo: Optional[str] = None,
    categoria_id: Optional[int] = None,
    mes: Optional[int] = Query(None, ge=1, le=12),
    ano: Optional[int] = Query(None, ge=2020, le=2030),
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db)
):
    query = db.query(Transacao).filter(Transacao.usuario_id == usuario.id)

    if tipo:
        query = query.filter(Transacao.tipo == tipo)
    if categoria_id:
        query = query.filter(Transacao.categoria_id == categoria_id)
    if mes and ano:
        inicio = datetime(ano, mes, 1)
        if mes == 12:
            fim = datetime(ano + 1, 1, 1)
        else:
            fim = datetime(ano, mes + 1, 1)
        query = query.filter(Transacao.data >= inicio, Transacao.data < fim)

    transacoes = query.order_by(Transacao.data.desc()).all()

    resultado = []
    for t in transacoes:
        resp = TransacaoResponse(
            id=t.id,
            descricao=t.descricao,
            valor=t.valor,
            tipo=t.tipo,
            data=t.data,
            categoria_id=t.categoria_id,
            categoria_nome=t.categoria.nome if t.categoria else None,
            criado_em=t.criado_em
        )
        resultado.append(resp)
    return resultado


@app.post("/api/transacoes", response_model=TransacaoResponse, status_code=201)
def criar_transacao(
    trans: TransacaoCreate,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db)
):
    if trans.categoria_id:
        cat = db.query(Categoria).filter(
            Categoria.id == trans.categoria_id,
            Categoria.usuario_id == usuario.id
        ).first()
        if not cat:
            raise HTTPException(status_code=400, detail="Categoria inválida")

    nova = Transacao(
        descricao=trans.descricao,
        valor=trans.valor,
        tipo=trans.tipo,
        data=trans.data or datetime.utcnow(),
        categoria_id=trans.categoria_id,
        usuario_id=usuario.id
    )
    db.add(nova)
    db.commit()
    db.refresh(nova)

    return TransacaoResponse(
        id=nova.id,
        descricao=nova.descricao,
        valor=nova.valor,
        tipo=nova.tipo,
        data=nova.data,
        categoria_id=nova.categoria_id,
        categoria_nome=nova.categoria.nome if nova.categoria else None,
        criado_em=nova.criado_em
    )


@app.put("/api/transacoes/{trans_id}", response_model=TransacaoResponse)
def atualizar_transacao(
    trans_id: int,
    dados: TransacaoUpdate,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db)
):
    trans = db.query(Transacao).filter(
        Transacao.id == trans_id, Transacao.usuario_id == usuario.id
    ).first()
    if not trans:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    if dados.descricao is not None:
        trans.descricao = dados.descricao
    if dados.valor is not None:
        trans.valor = dados.valor
    if dados.tipo is not None:
        trans.tipo = dados.tipo
    if dados.categoria_id is not None:
        trans.categoria_id = dados.categoria_id
    if dados.data is not None:
        trans.data = dados.data

    db.commit()
    db.refresh(trans)

    return TransacaoResponse(
        id=trans.id,
        descricao=trans.descricao,
        valor=trans.valor,
        tipo=trans.tipo,
        data=trans.data,
        categoria_id=trans.categoria_id,
        categoria_nome=trans.categoria.nome if trans.categoria else None,
        criado_em=trans.criado_em
    )


@app.delete("/api/transacoes/{trans_id}", status_code=204)
def deletar_transacao(
    trans_id: int,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db)
):
    trans = db.query(Transacao).filter(
        Transacao.id == trans_id, Transacao.usuario_id == usuario.id
    ).first()
    if not trans:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    db.delete(trans)
    db.commit()
    return None


# ==================== DASHBOARD / RESUMO ====================
@app.get("/api/resumo", response_model=ResumoFinanceiro)
def obter_resumo(
    mes: Optional[int] = Query(None, ge=1, le=12),
    ano: Optional[int] = Query(None, ge=2020, le=2030),
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db)
):
    query = db.query(Transacao).filter(Transacao.usuario_id == usuario.id)

    if mes and ano:
        inicio = datetime(ano, mes, 1)
        if mes == 12:
            fim = datetime(ano + 1, 1, 1)
        else:
            fim = datetime(ano, mes + 1, 1)
        query = query.filter(Transacao.data >= inicio, Transacao.data < fim)

    transacoes = query.all()

    total_receitas = sum(t.valor for t in transacoes if t.tipo == TipoTransacao.receita)
    total_despesas = sum(t.valor for t in transacoes if t.tipo == TipoTransacao.despesa)
    saldo = total_receitas - total_despesas

    # Agrupar por categoria
    receitas_cat = {}
    despesas_cat = {}
    for t in transacoes:
        nome_cat = t.categoria.nome if t.categoria else "Sem categoria"
        if t.tipo == TipoTransacao.receita:
            receitas_cat[nome_cat] = receitas_cat.get(nome_cat, 0) + t.valor
        else:
            despesas_cat[nome_cat] = despesas_cat.get(nome_cat, 0) + t.valor

    return ResumoFinanceiro(
        saldo=round(saldo, 2),
        total_receitas=round(total_receitas, 2),
        total_despesas=round(total_despesas, 2),
        quantidade_transacoes=len(transacoes),
        receitas_por_categoria=[{"categoria": k, "valor": round(v, 2)} for k, v in receitas_cat.items()],
        despesas_por_categoria=[{"categoria": k, "valor": round(v, 2)} for k, v in despesas_cat.items()]
    )


@app.get("/")
def root():
    return {
        "mensagem": "Sistema de Controle Financeiro - API rodando!",
        "docs": "/docs",
        "usuario_demo": "demo@faculdade.com / demo123"
    }
