from typing import Optional

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

CURSOS = ["GES", "GEC"]

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
    matricula: int
    id: str

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


def cria_matricula(curso: str) -> tuple[int, str]:
    contador_matriculas[curso] += 1
    matricula = contador_matriculas[curso]
    return matricula, f"{curso}{matricula}"


def serializar_aluno(aluno: dict) -> AlunoResponse:
    return AlunoResponse(**aluno)


@app.get("/")
def read_root():
    return {"message": "API de alunos em funcionamento."}


@app.get("/api/v1/alunos", response_model=list[AlunoResponse])
def listar_alunos():
    return [serializar_aluno(aluno) for aluno in alunos.values()]


@app.get("/api/v1/alunos/{aluno_id}", response_model=AlunoResponse)
def buscar_aluno(aluno_id: str):
    aluno = alunos.get(aluno_id.upper())
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
    matricula, aluno_id = cria_matricula(curso)

    aluno = {
        "nome": payload.nome.strip(),
        "email": payload.email,
        "curso": curso,
        "matricula": matricula,
        "id": aluno_id,
    }
    alunos[aluno_id] = aluno
    return serializar_aluno(aluno)


@app.put("/api/v1/alunos/{aluno_id}", response_model=AlunoResponse)
def atualizar_aluno(aluno_id: str, payload: AlunoUpdate):
    id_atual = aluno_id.upper()
    aluno_existente = alunos.get(id_atual)
    if aluno_existente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aluno nao encontrado.",
        )

    curso = validar_curso(payload.curso)
    nova_matricula = aluno_existente["matricula"]
    novo_id = id_atual

    if curso != aluno_existente["curso"]:
        nova_matricula, novo_id = cria_matricula(curso)
        del alunos[id_atual]

    aluno_atualizado = {
        "nome": payload.nome.strip(),
        "email": payload.email,
        "curso": curso,
        "matricula": nova_matricula,
        "id": novo_id,
    }
    alunos[novo_id] = aluno_atualizado
    return serializar_aluno(aluno_atualizado)


@app.patch("/api/v1/alunos/{aluno_id}", response_model=AlunoResponse)
def atualizar_parcialmente_aluno(aluno_id: str, payload: AlunoPatch):
    id_atual = aluno_id.upper()
    aluno_existente = alunos.get(id_atual)
    if aluno_existente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aluno nao encontrado.",
        )

    dados = payload.model_dump(exclude_unset=True)
    curso = aluno_existente["curso"]
    nova_matricula = aluno_existente["matricula"]
    novo_id = id_atual

    if "curso" in dados:
        curso = validar_curso(dados["curso"])
        if curso != aluno_existente["curso"]:
            nova_matricula, novo_id = cria_matricula(curso)
            del alunos[id_atual]

    aluno_atualizado = {
        "nome": dados.get("nome", aluno_existente["nome"]).strip(),
        "email": dados.get("email", aluno_existente["email"]),
        "curso": curso,
        "matricula": nova_matricula,
        "id": novo_id,
    }
    alunos[novo_id] = aluno_atualizado
    return serializar_aluno(aluno_atualizado)


@app.delete("/api/v1/alunos/{aluno_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_aluno(aluno_id: str):
    id_atual = aluno_id.upper()
    if id_atual not in alunos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aluno nao encontrado.",
        )

    del alunos[id_atual]
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/api/v1/alunos", status_code=status.HTTP_204_NO_CONTENT)
def resetar_alunos():
    reset_state()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
