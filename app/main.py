from typing import Optional

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

CURSOS = ["GES", "GEC", "GET", "GEP", "GEA", "GEL", "GEB"]

app = FastAPI(title="CRUD de Alunos", version="1.0.0")

alunos: dict[str, dict] = {}
contador_matriculas = {curso: 0 for curso in CURSOS}


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
    matricula: str

    model_config = ConfigDict(from_attributes=True)


def reset_state():
    alunos.clear()
    for curso in CURSOS:
        contador_matriculas[curso] = 0


def validar_curso(curso: str) -> str:
    curso_normalizado = curso.strip().upper()
    if curso_normalizado not in CURSOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Curso invalido.",
        )
    return curso_normalizado


def cria_matricula(curso: str) -> str:
    contador_matriculas[curso] += 1
    return f"{curso}{contador_matriculas[curso]}"


def serializar_aluno(aluno: dict) -> AlunoResponse:
    return AlunoResponse(**aluno)


@app.get("/")
def read_root():
    return {"message": "API de alunos em funcionamento."}


@app.get("/api/v1/alunos", response_model=list[AlunoResponse])
def listar_alunos():
    return [serializar_aluno(aluno) for aluno in alunos.values()]


@app.get("/api/v1/alunos/{matricula}", response_model=AlunoResponse)
def buscar_aluno(matricula: str):
    aluno = alunos.get(matricula.upper())
    if aluno is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aluno nao encontrado.",
        )
    return serializar_aluno(aluno)


@app.post(
    "/api/v1/alunos",
    response_model=AlunoResponse,
    status_code=status.HTTP_201_CREATED,
)
def cadastrar_aluno(payload: AlunoCreate):
    curso = validar_curso(payload.curso)
    matricula = cria_matricula(curso)

    aluno = {
        "nome": payload.nome.strip(),
        "email": payload.email,
        "curso": curso,
        "matricula": matricula,
    }
    alunos[matricula] = aluno
    return serializar_aluno(aluno)


@app.put("/api/v1/alunos/{matricula}", response_model=AlunoResponse)
def atualizar_aluno(matricula: str, payload: AlunoUpdate):
    matricula_atual = matricula.upper()
    aluno_existente = alunos.get(matricula_atual)
    if aluno_existente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aluno nao encontrado.",
        )

    curso = validar_curso(payload.curso)
    nova_matricula = matricula_atual

    if curso != aluno_existente["curso"]:
        nova_matricula = cria_matricula(curso)
        del alunos[matricula_atual]

    aluno_atualizado = {
        "nome": payload.nome.strip(),
        "email": payload.email,
        "curso": curso,
        "matricula": nova_matricula,
    }
    alunos[nova_matricula] = aluno_atualizado
    return serializar_aluno(aluno_atualizado)


@app.patch("/api/v1/alunos/{matricula}", response_model=AlunoResponse)
def atualizar_parcialmente_aluno(matricula: str, payload: AlunoPatch):
    matricula_atual = matricula.upper()
    aluno_existente = alunos.get(matricula_atual)
    if aluno_existente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aluno nao encontrado.",
        )

    dados = payload.model_dump(exclude_unset=True)
    curso = aluno_existente["curso"]
    nova_matricula = matricula_atual

    if "curso" in dados:
        curso = validar_curso(dados["curso"])
        if curso != aluno_existente["curso"]:
            nova_matricula = cria_matricula(curso)
            del alunos[matricula_atual]

    aluno_atualizado = {
        "nome": dados.get("nome", aluno_existente["nome"]).strip(),
        "email": dados.get("email", aluno_existente["email"]),
        "curso": curso,
        "matricula": nova_matricula,
    }
    alunos[nova_matricula] = aluno_atualizado
    return serializar_aluno(aluno_atualizado)


@app.delete("/api/v1/alunos/{matricula}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_aluno(matricula: str):
    matricula_atual = matricula.upper()
    if matricula_atual not in alunos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aluno nao encontrado.",
        )

    del alunos[matricula_atual]
    return Response(status_code=status.HTTP_204_NO_CONTENT)
