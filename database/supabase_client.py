import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def salvar_dados_ingresso(filme_dados, sinopse, sessoes_lista, cidade_slug):
    """
    Salva ou atualiza os dados do filme, cinema e sessões no banco.
    """
    try:
        # 1. Salva ou atualiza o Filme
        response_filme = supabase.table("filmes").upsert(
            {
                "titulo": filme_dados["titulo"],
                "sinopse": sinopse,
                "url_ingresso": filme_dados.get("url", ""),
                "imagem_url": filme_dados.get("imagem_url"),
                "duracao": filme_dados.get("duracao"),
                "classificacao": filme_dados.get("classificacao"),
                "diretor": filme_dados.get("diretor"),
                "generos": filme_dados.get("generos", []),
                "elenco": filme_dados.get("elenco", []),
                "trailer_url_youtube": filme_dados.get("trailer_url"),
            },
            on_conflict="titulo"
        ).execute() 

        # Pega o ID do filme salvo
        filme_id = response_filme.data[0]["id"]

        # 2. Salva Cinemas e Sessões
        sessoes_salvas = 0

        for sessao in sessoes_lista:

            response_cinema = supabase.table("cinemas").upsert(
                {
                    "nome": sessao["cinema"],
                    "cidade": cidade_slug
                },
                on_conflict="nome,cidade"
            ).execute()

            cinema_id = response_cinema.data[0]["id"]

            supabase.table("sessoes").upsert(
                {
                    "filme_id": filme_id,
                    "cinema_id": cinema_id,
                    "data_horario": sessao["horario"],
                    "link_compra": sessao["link_compra"]
                },
                on_conflict="filme_id,cinema_id,data_horario"
            ).execute()

            sessoes_salvas += 1

        print(
            f"Sucesso! Filme '{filme_dados['titulo']}' salvo com {sessoes_salvas} sessões em {cidade_slug}."
        )

    except Exception as e:
        print(f"Erro ao salvar no banco: {e}")


# TESTE
# print("Testando conexão e salvamento no Supabase...")

# filme_teste = {
#     "titulo": "Filme Teste MVP",
#     "url": "https://www.ingresso.com/filme/filme-teste"
# }

# sinopse_teste = (
#     "Esta é uma sinopse de teste para verificar se o banco está salvando."
# )

# sessoes_teste = [
#     {
#         "cinema": "Cinema Exemplo Uberlândia 2",
#         "horario": "2026-07-22T15:00:00-03:00",
#         "link_compra": "https://checkout.ingresso.com/?sessionId=12345"
#     }
# ]

# salvar_dados_ingresso(
#     filme_teste,
#     sinopse_teste,
#     sessoes_teste,
#     "uberlandia"
# )