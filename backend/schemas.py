from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TipoTransacao(str, Enum):
    receita = "receita"
    despesa = "despesa"


class UsuarioCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    senha: str = Field(..., min_length=6)


class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str


class UsuarioResponse(BaseModel):
    id: int
    nome: str
    email: str
    criado_em: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class CategoriaCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=50)
    tipo: TipoTransacao


class CategoriaResponse(BaseModel):
    id: int
    nome: str
    tipo: TipoTransacao
    criado_em: datetime

    class Config:
        from_attributes = True


class TransacaoCreate(BaseModel):
    descricao: str = Field(..., min_length=1, max_length=200)
    valor: float = Field(..., gt=0)
    tipo: TipoTransacao
    categoria_id: Optional[int] = None
    data: Optional[datetime] = None


class TransacaoUpdate(BaseModel):
    descricao: Optional[str] = Field(None, min_length=1, max_length=200)
    valor: Optional[float] = Field(None, gt=0)
    tipo: Optional[TipoTransacao] = None
    categoria_id: Optional[int] = None
    data: Optional[datetime] = None


class TransacaoResponse(BaseModel):
    id: int
    descricao: str
    valor: float
    tipo: TipoTransacao
    data: datetime
    categoria_id: Optional[int]
    categoria_nome: Optional[str] = None
    criado_em: datetime

    class Config:
        from_attributes = True


class ResumoFinanceiro(BaseModel):
    saldo: float
    total_receitas: float
    total_despesas: float
    quantidade_transacoes: int
    receitas_por_categoria: List[dict]
    despesas_por_categoria: List[dict]
