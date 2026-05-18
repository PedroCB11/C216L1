import os
from contextlib import asynccontextmanager
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import Integer, String, create_engine, delete, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

CURSOS = ["GES", "GEC"]
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/alunos",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


class AlunoModel(Base):
    __tablename__ = "alunos"

    db_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    curso: Mapped[str] = mapped_column(String(10), index=True)
    matricula: Mapped[int] = mapped_column(Integer)


class ContadorCursoModel(Base):
    __tablename__ = "contadores_cursos"

    curso: Mapped[str] = mapped_column(String(10), primary_key=True)
    proxima_matricula: Mapped[int] = mapped_column(Integer, default=1)


class AlunoBase(BaseModel):
    nome: str = Field(..., min_length=1)
    email: EmailStr
    curso: str


class AlunoCreate(AlunoBase):
    pass


class AlunoUpdate(AlunoBase):
    pass


class AlunoPatch(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=1)
    email: Optional[EmailStr] = None
    curso: Optional[str] = None


class AlunoResponse(AlunoBase):
    matricula: int
    id: str

    model_config = ConfigDict(from_attributes=True)


def criar_tabelas():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        inicializar_contadores(db)
        db.commit()


def inicializar_contadores(db: Session):
    for curso in CURSOS:
        contador = db.get(ContadorCursoModel, curso)
        if contador is None:
            db.add(ContadorCursoModel(curso=curso, proxima_matricula=1))


def reset_state():
    criar_tabelas()
    with SessionLocal() as db:
        db.execute(delete(AlunoModel))
        for curso in CURSOS:
            contador = db.get(ContadorCursoModel, curso)
            if contador is None:
                db.add(ContadorCursoModel(curso=curso, proxima_matricula=1))
            else:
                contador.proxima_matricula = 1
        db.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DBSession = Annotated[Session, Depends(get_db)]


def validar_curso(curso: str) -> str:
    curso_normalizado = curso.strip().upper()
    if curso_normalizado not in CURSOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Curso invalido.",
        )
    return curso_normalizado


def cria_matricula(db: Session, curso: str) -> tuple[int, str]:
    contador = db.get(ContadorCursoModel, curso)
    if contador is None:
        contador = ContadorCursoModel(curso=curso, proxima_matricula=1)
        db.add(contador)
        db.flush()

    matricula = contador.proxima_matricula
    contador.proxima_matricula += 1
    return matricula, f"{curso}{matricula}"


def buscar_modelo_por_id(db: Session, aluno_id: str) -> AlunoModel:
    aluno = db.scalar(select(AlunoModel).where(AlunoModel.id == aluno_id.upper()))
    if aluno is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aluno nao encontrado.",
        )
    return aluno


def salvar_aluno(db: Session, aluno: AlunoModel) -> AlunoModel:
    db.add(aluno)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(aluno)
    return aluno


@asynccontextmanager
async def lifespan(app: FastAPI):
    criar_tabelas()
    yield


app = FastAPI(title="CRUD de Alunos", version="1.0.0", lifespan=lifespan)


@app.get("/")
def read_root():
    return {"message": "API de alunos em funcionamento."}


@app.get("/api/v1/alunos", response_model=list[AlunoResponse])
def listar_alunos(db: DBSession):
    alunos = db.scalars(select(AlunoModel).order_by(AlunoModel.db_id)).all()
    return alunos


@app.get("/api/v1/alunos/{aluno_id}", response_model=AlunoResponse)
def buscar_aluno(aluno_id: str, db: DBSession):
    return buscar_modelo_por_id(db, aluno_id)


@app.post(
    "/api/v1/alunos",
    response_model=AlunoResponse,
    status_code=status.HTTP_201_CREATED,
)
def cadastrar_aluno(payload: AlunoCreate, db: DBSession):
    curso = validar_curso(payload.curso)
    matricula, aluno_id = cria_matricula(db, curso)

    aluno = AlunoModel(
        nome=payload.nome.strip(),
        email=str(payload.email),
        curso=curso,
        matricula=matricula,
        id=aluno_id,
    )
    return salvar_aluno(db, aluno)


@app.put("/api/v1/alunos/{aluno_id}", response_model=AlunoResponse)
def atualizar_aluno(aluno_id: str, payload: AlunoUpdate, db: DBSession):
    aluno = buscar_modelo_por_id(db, aluno_id)
    curso = validar_curso(payload.curso)

    if curso != aluno.curso:
        aluno.matricula, aluno.id = cria_matricula(db, curso)

    aluno.nome = payload.nome.strip()
    aluno.email = str(payload.email)
    aluno.curso = curso
    return salvar_aluno(db, aluno)


@app.patch("/api/v1/alunos/{aluno_id}", response_model=AlunoResponse)
def atualizar_parcialmente_aluno(aluno_id: str, payload: AlunoPatch, db: DBSession):
    aluno = buscar_modelo_por_id(db, aluno_id)
    dados = payload.model_dump(exclude_unset=True)

    if "curso" in dados:
        curso = validar_curso(dados["curso"])
        if curso != aluno.curso:
            aluno.matricula, aluno.id = cria_matricula(db, curso)
        aluno.curso = curso

    if "nome" in dados:
        aluno.nome = dados["nome"].strip()
    if "email" in dados:
        aluno.email = str(dados["email"])

    return salvar_aluno(db, aluno)


@app.delete("/api/v1/alunos/{aluno_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_aluno(aluno_id: str, db: DBSession):
    aluno = buscar_modelo_por_id(db, aluno_id)
    db.delete(aluno)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/api/v1/alunos", status_code=status.HTTP_204_NO_CONTENT)
def resetar_alunos():
    reset_state()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def total_alunos_persistidos() -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(AlunoModel)) or 0
