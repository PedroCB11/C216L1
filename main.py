# CRUD de alunos para terminal

CURSOS = ["GES", "GEC", "GET", "GEP", "GEA", "GEL", "GEB"]

alunos = []
contador_matriculas = {   
}


def cria_matricula(curso):
    contador_matriculas[curso] += 1
    return f"{curso}{contador_matriculas[curso]}"


def cadastro_aluno():
    print("--- CADASTRAR ALUNO ---")
    nome = input("Digite o nome do aluno: ").strip() #ignora os espaços
    email = input("Digite o email do aluno: ").strip()
    curso = input("Digite o curso, exemplo. (GEC, GES, GELGET, GEP, GEA, , GEB): ").strip().upper() #deixa tudo em maiusculo

    if curso not in CURSOS:
        print("Curso invalido.")
        return

    matricula = cria_matricula(curso)

    aluno = {
        "nome": nome,
        "email": email,
        "curso": curso,
        "matricula": matricula
    }

    alunos.append(aluno)
    print(f"Aluno cadastrado com sucesso! Matrícula gerada: {matricula}")


def lista_alunos():
    print("--- LISTAR ALUNOS ---")
    if len(alunos) == 0:
        print("Nenhum aluno cadastrado.")
        return

    for i, aluno in enumerate(alunos, start=1):
        print(f"Aluno {i}")
        print(f"Nome: {aluno['nome']}")
        print(f"Email: {aluno['email']}")
        print(f"Curso: {aluno['curso']}")
        print(f"Matrícula: {aluno['matricula']}")


def buscar_aluno_mat(matricula):
    for aluno in alunos:
        if aluno["matricula"] == matricula:
            return aluno
    return None


def atualizar_dado_aluno():
    print("--- ATUALIZAR ALUNO ---")
    matricula = input("Digite a matricula do aluno que deseja atualizar: ").strip().upper()

    aluno = buscar_aluno_mat(matricula)

    if aluno is None:
        print("Aluno nao encontrado.")
        return

    novo_nome = input(f"Novo nome ({aluno['nome']}): ").strip()
    novo_email = input(f"Novo email ({aluno['email']}): ").strip()
    novo_curso = input(f"Novo curso ({aluno['curso']}): ").strip().upper()

    if novo_nome != "":
        aluno["nome"] = novo_nome

    if novo_email != "":
        aluno["email"] = novo_email

    if novo_curso != "":
        if novo_curso in CURSOS:
            aluno["curso"] = novo_curso
        else:
            print("Curso invalido. Curso não foi alterado.")

    print("Aluno atualizado com sucesso.")


def excluir_dado_aluno():
    print("--- EXCLUIR ALUNO ---")
    matricula = input("Digite a matricula do aluno que deseja excluir: ").strip().upper()

    aluno = buscar_aluno_mat(matricula)

    if aluno is None:
        print("Aluno nao encontrado.")
        return

    alunos.remove(aluno)
    print("Aluno excluido com sucesso.")


def mostrar_menu():
    print("===== MENU =====")
    print("1 - Cadastro do aluno")
    print("2 - Lista de alunos")
    print("3 - Atualiza dados do aluno")
    print("4 - Excluir dado do aluno")
    print("5 - Sair")


def main():
    while True:
        mostrar_menu()
        opcao = input("Escolha uma opcao: ").strip()

        if opcao == "1":
            cadastro_aluno()
        elif opcao == "2":
            lista_alunos()
        elif opcao == "3":
            atualizar_dado_aluno()
        elif opcao == "4":
            excluir_dado_aluno()
        elif opcao == "5":
            print("Encerrando o programa...")
            break
        else:
            print("Erro.")


main()