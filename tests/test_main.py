import pytest
from fastapi.testclient import TestClient

from app.main import app, reset_state, total_alunos_persistidos

URL_BASE = "/api/v1/alunos"


@pytest.fixture(autouse=True)
def limpar_estado():
    reset_state()


@pytest.fixture
def cliente():
    return TestClient(app)


def payload(nome, email, curso):
    return {"nome": nome, "email": email, "curso": curso}


def criar_aluno(cliente, nome="Aluno", email="aluno@example.com", curso="GES"):
    resposta = cliente.post(URL_BASE, json=payload(nome, email, curso))

    assert resposta.status_code == 201
    return resposta.json()


def criar_tres_alunos_por_curso(cliente):
    alunos_criados = []
    for curso in ("GES", "GEC"):
        for indice in range(1, 4):
            alunos_criados.append(
                criar_aluno(
                    cliente,
                    nome=f"Aluno {curso} {indice}",
                    email=f"aluno_{curso.lower()}_{indice}@example.com",
                    curso=curso,
                )
            )
    return alunos_criados


class TestesStatusApi:
    def test_deve_retornar_mensagem_de_status_da_api(self, cliente):
        resposta = cliente.get("/")

        assert resposta.status_code == 200
        assert resposta.json() == {"message": "API de alunos em funcionamento."}


class TestesCrudAlunos:
    def test_deve_cadastrar_tres_alunos_por_curso_com_ids_sequenciais(self, cliente):
        alunos = criar_tres_alunos_por_curso(cliente)

        assert [aluno["id"] for aluno in alunos] == [
            "GES1",
            "GES2",
            "GES3",
            "GEC1",
            "GEC2",
            "GEC3",
        ]
        assert [aluno["matricula"] for aluno in alunos] == [1, 2, 3, 1, 2, 3]

    def test_deve_listar_todos_os_alunos(self, cliente):
        alunos = criar_tres_alunos_por_curso(cliente)

        resposta = cliente.get(URL_BASE)

        assert resposta.status_code == 200
        assert resposta.json() == alunos

    def test_deve_persistir_alunos_no_banco_entre_clientes(self, cliente):
        alunos = criar_tres_alunos_por_curso(cliente)

        with TestClient(app) as novo_cliente:
            resposta = novo_cliente.get(URL_BASE)

        assert resposta.status_code == 200
        assert resposta.json() == alunos
        assert total_alunos_persistidos() == 6

    def test_deve_buscar_aluno_por_id(self, cliente):
        aluno = criar_aluno(
            cliente,
            nome="Ada Lovelace",
            email="ada@example.com",
            curso="GES",
        )

        resposta = cliente.get(f"{URL_BASE}/{aluno['id']}")

        assert resposta.status_code == 200
        assert resposta.json() == aluno

    def test_deve_atualizar_dados_do_aluno_com_patch(self, cliente):
        aluno = criar_aluno(cliente, curso="GES")

        resposta = cliente.patch(
            f"{URL_BASE}/{aluno['id']}",
            json={"nome": "Aluno Atualizado", "email": "atualizado@example.com"},
        )

        assert resposta.status_code == 200
        assert resposta.json() == {
            "nome": "Aluno Atualizado",
            "email": "atualizado@example.com",
            "curso": "GES",
            "matricula": 1,
            "id": "GES1",
        }

    def test_deve_gerar_novo_id_quando_patch_alterar_curso(self, cliente):
        aluno = criar_aluno(cliente, curso="GES")

        resposta = cliente.patch(f"{URL_BASE}/{aluno['id']}", json={"curso": "GEC"})

        assert resposta.status_code == 200
        assert resposta.json()["curso"] == "GEC"
        assert resposta.json()["matricula"] == 1
        assert resposta.json()["id"] == "GEC1"
        assert cliente.get(f"{URL_BASE}/GES1").status_code == 404

    def test_deve_remover_aluno_do_sistema(self, cliente):
        aluno = criar_aluno(cliente, curso="GEC")

        resposta_delete = cliente.delete(f"{URL_BASE}/{aluno['id']}")
        resposta_get = cliente.get(f"{URL_BASE}/{aluno['id']}")

        assert resposta_delete.status_code == 204
        assert resposta_delete.text == ""
        assert resposta_get.status_code == 404

    def test_nao_deve_reutilizar_id_de_aluno_deletado(self, cliente):
        aluno = criar_aluno(cliente, curso="GES")

        resposta_delete = cliente.delete(f"{URL_BASE}/{aluno['id']}")
        novo_aluno = criar_aluno(
            cliente,
            nome="Novo Aluno",
            email="novo@example.com",
            curso="GES",
        )

        assert resposta_delete.status_code == 204
        assert novo_aluno["id"] == "GES2"
        assert novo_aluno["matricula"] == 2

    def test_deve_resetar_lista_de_alunos(self, cliente):
        criar_tres_alunos_por_curso(cliente)

        resposta_delete = cliente.delete(URL_BASE)
        resposta_get = cliente.get(URL_BASE)

        assert resposta_delete.status_code == 204
        assert resposta_get.status_code == 200
        assert resposta_get.json() == []


class TestesValidacoes:
    def test_deve_retornar_400_para_curso_invalido(self, cliente):
        resposta = cliente.post(
            URL_BASE,
            json=payload("Aluno", "aluno@example.com", "INVALID"),
        )

        assert resposta.status_code == 400
        assert resposta.json() == {"detail": "Curso invalido."}

    @pytest.mark.parametrize(
        "payload_invalido",
        [
            {"nome": "", "email": "aluno@example.com", "curso": "GES"},
            {"nome": "Aluno", "email": "email-invalido", "curso": "GES"},
            {"email": "aluno@example.com", "curso": "GES"},
        ],
    )
    def test_deve_retornar_422_para_payload_invalido(
        self,
        cliente,
        payload_invalido,
    ):
        resposta = cliente.post(URL_BASE, json=payload_invalido)

        assert resposta.status_code == 422

    def test_deve_retornar_404_para_aluno_inexistente(self, cliente):
        resposta = cliente.get(f"{URL_BASE}/GES999")

        assert resposta.status_code == 404
        assert resposta.json() == {"detail": "Aluno nao encontrado."}
