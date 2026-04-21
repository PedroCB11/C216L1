import pytest
from fastapi.testclient import TestClient

from app.main import app, reset_state

URL_BASE = "/api/v1/alunos"
ALUNO_PADRAO = {
    "nome": "aluno_01",
    "email": "aluno_01@example.com",
    "curso": "GEC",
}

ALUNO_ATUALIZADO = {
    "nome": "aluno_atualizado",
    "email": "aluno_atualizado@example.com",
    "curso": "GES",
}


@pytest.fixture(autouse=True)
def limpar_estado():
    reset_state()


@pytest.fixture
def cliente():
    return TestClient(app)


def montar_payload_aluno(**alteracoes):
    payload = ALUNO_PADRAO.copy()
    payload.update(alteracoes)
    return payload


def validar_resposta_aluno(aluno, *, nome, email, curso, matricula):
    assert aluno == {
        "nome": nome,
        "email": email,
        "curso": curso,
        "matricula": matricula,
    }


def criar_aluno(cliente, **alteracoes):
    resposta = cliente.post(URL_BASE, json=montar_payload_aluno(**alteracoes))

    assert resposta.status_code == 201
    return resposta.json()


class TestesStatusApi:
    def test_deve_retornar_mensagem_de_status_da_api(self, cliente):
        resposta = cliente.get("/")

        assert resposta.status_code == 200
        assert resposta.json() == {"message": "API de alunos em funcionamento."}


class TestesGetAlunos:
    def test_deve_retornar_lista_vazia_quando_nao_existirem_alunos(self, cliente):
        resposta = cliente.get(URL_BASE)

        assert resposta.status_code == 200
        assert resposta.json() == []

    def test_deve_retornar_todos_os_alunos_cadastrados(self, cliente):
        primeiro_aluno = criar_aluno(cliente)
        segundo_aluno = criar_aluno(
            cliente,
            nome="aluno_02",
            email="aluno_02@example.com",
            curso="GES",
        )

        resposta = cliente.get(URL_BASE)

        assert resposta.status_code == 200
        assert resposta.json() == [primeiro_aluno, segundo_aluno]

    def test_deve_retornar_um_aluno_pela_matricula(self, cliente):
        aluno = criar_aluno(cliente)

        resposta = cliente.get(f"{URL_BASE}/{aluno['matricula']}")

        assert resposta.status_code == 200
        assert resposta.json() == aluno

    def test_deve_retornar_404_quando_a_matricula_nao_existir(self, cliente):
        resposta = cliente.get(f"{URL_BASE}/GEC999")

        assert resposta.status_code == 404
        assert resposta.json() == {"detail": "Aluno nao encontrado."}


class TestesPostAlunos:
    def test_deve_cadastrar_aluno_com_matricula_gerada(self, cliente):
        resposta = cliente.post(
            URL_BASE,
            json=montar_payload_aluno(
                nome="aluno_03",
                email="aluno_03@example.com",
                curso="GES",
            ),
        )

        assert resposta.status_code == 201
        validar_resposta_aluno(
            resposta.json(),
            nome="aluno_03",
            email="aluno_03@example.com",
            curso="GES",
            matricula="GES1",
        )

    def test_deve_normalizar_curso_em_minusculo_ao_cadastrar(self, cliente):
        resposta = cliente.post(
            URL_BASE,
            json=montar_payload_aluno(curso="ges"),
        )

        assert resposta.status_code == 201
        assert resposta.json()["curso"] == "GES"
        assert resposta.json()["matricula"] == "GES1"

    def test_deve_retornar_400_para_curso_invalido_ao_cadastrar(self, cliente):
        resposta = cliente.post(
            URL_BASE,
            json=montar_payload_aluno(curso="INVALID"),
        )

        assert resposta.status_code == 400
        assert resposta.json() == {"detail": "Curso invalido."}

    @pytest.mark.parametrize(
        "payload_invalido",
        [
            {"nome": "", "email": "aluno_01@example.com", "curso": "GEC"},
            {"nome": "aluno_01", "email": "email-invalido", "curso": "GEC"},
            {"email": "aluno_01@example.com", "curso": "GEC"},
        ],
    )
    def test_deve_retornar_422_para_payload_invalido_no_cadastro(self, cliente, payload_invalido):
        resposta = cliente.post(URL_BASE, json=payload_invalido)

        assert resposta.status_code == 422


class TestesPutAlunos:
    def test_deve_substituir_todos_os_dados_do_aluno(self, cliente):
        aluno = criar_aluno(cliente)

        resposta = cliente.put(
            f"{URL_BASE}/{aluno['matricula']}",
            json=ALUNO_ATUALIZADO,
        )

        assert resposta.status_code == 200
        validar_resposta_aluno(
            resposta.json(),
            nome="aluno_atualizado",
            email="aluno_atualizado@example.com",
            curso="GES",
            matricula="GES1",
        )

    def test_mantem_a_mesma_matricula_quando_o_curso_nao_mudar(self, cliente):
        aluno = criar_aluno(cliente)

        resposta = cliente.put(
            f"{URL_BASE}/{aluno['matricula']}",
            json=montar_payload_aluno(
                nome="aluno_substituido",
                email="aluno_substituido@example.com",
                curso="GEC",
            ),
        )

        assert resposta.status_code == 200
        assert resposta.json()["matricula"] == aluno["matricula"]

    def test_deve_retornar_404_para_aluno_inexistente_no_put(self, cliente):
        resposta = cliente.put(
            f"{URL_BASE}/GEC999",
            json=ALUNO_ATUALIZADO,
        )

        assert resposta.status_code == 404
        assert resposta.json() == {"detail": "Aluno nao encontrado."}

    def test_retorna_400_para_curso_invalido_no_put(self, cliente):
        aluno = criar_aluno(cliente)

        resposta = cliente.put(
            f"{URL_BASE}/{aluno['matricula']}",
            json=montar_payload_aluno(curso="INVALID"),
        )

        assert resposta.status_code == 400
        assert resposta.json() == {"detail": "Curso invalido."}


class TestesPatchAlunos:
    def test_atualiza_apenas_os_campos_informados(self, cliente):
        aluno = criar_aluno(cliente)

        resposta = cliente.patch(
            f"{URL_BASE}/{aluno['matricula']}",
            json={"nome": "aluno_patch"},
        )

        assert resposta.status_code == 200
        validar_resposta_aluno(
            resposta.json(),
            nome="aluno_patch",
            email=ALUNO_PADRAO["email"],
            curso=ALUNO_PADRAO["curso"],
            matricula="GEC1",
        )

    def test_deve_gerar_nova_matricula_quando_patch_alterar_curso(self, cliente):
        aluno = criar_aluno(cliente)

        resposta = cliente.patch(
            f"{URL_BASE}/{aluno['matricula']}",
            json={"curso": "GES"},
        )

        assert resposta.status_code == 200
        assert resposta.json()["curso"] == "GES"
        assert resposta.json()["matricula"] == "GES1"

    def test_deve_retornar_404_para_aluno_inexistente_no_patch(self, cliente):
        resposta = cliente.patch(
            f"{URL_BASE}/GEC999",
            json={"nome": "aluno_patch"},
        )

        assert resposta.status_code == 404
        assert resposta.json() == {"detail": "Aluno nao encontrado."}

    def test_retorna_400_para_curso_invalido_no_patch(self, cliente):
        aluno = criar_aluno(cliente)

        resposta = cliente.patch(
            f"{URL_BASE}/{aluno['matricula']}",
            json={"curso": "INVALID"},
        )

        assert resposta.status_code == 400
        assert resposta.json() == {"detail": "Curso invalido."}

    @pytest.mark.parametrize(
        "payload_invalido",
        [
            {"nome": ""},
            {"email": "email-invalido"},
        ],
    )
    def test_retorna_422_para_payload_invalido_no_patch(self, cliente, payload_invalido):
        aluno = criar_aluno(cliente)

        resposta = cliente.patch(
            f"{URL_BASE}/{aluno['matricula']}",
            json=payload_invalido,
        )

        assert resposta.status_code == 422


class TestesDeleteAlunos:
    def test_retorna_204_para_aluno_existente(self, cliente):
        aluno = criar_aluno(cliente)

        resposta = cliente.delete(f"{URL_BASE}/{aluno['matricula']}")

        assert resposta.status_code == 204
        assert resposta.text == ""

    def test_retorna_404_para_aluno_inexistente_no_delete(self, cliente):
        resposta = cliente.delete(f"{URL_BASE}/GEC999")

        assert resposta.status_code == 404
        assert resposta.json() == {"detail": "Aluno nao encontrado."}

    def test_nao_encontra_aluno_apos_delete_com_sucesso(self, cliente):
        aluno = criar_aluno(cliente)

        resposta_delete = cliente.delete(f"{URL_BASE}/{aluno['matricula']}")
        resposta_get = cliente.get(f"{URL_BASE}/{aluno['matricula']}")

        assert resposta_delete.status_code == 204
        assert resposta_get.status_code == 404
