import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def salvar_dados_ingresso(filme_dados, sinopse, sessoes_lista, cidade_slug):
    try:
        dados_filme = {
            "titulo": filme_dados["titulo"],
            "sinopse": sinopse,
            "url_ingresso": filme_dados.get("url", ""),
            "imagem_url": filme_dados.get("imagem_url"),
            "duracao": filme_dados.get("duracao"),
            "classificacao": filme_dados.get("classificacao"),
            "diretor": filme_dados.get("diretor"),
            "generos": filme_dados.get("generos", []),
            "elenco": filme_dados.get("elenco", []),
        }

        imdb_id = filme_dados.get("imdb_id")
        if imdb_id:
            dados_filme["imdb_id"] = imdb_id
            dados_filme["nota_imdb"] = filme_dados.get("nota_imdb")

        # imdb_id e o identificador real do filme; so cai pro titulo
        # quando o scraper do IMDb nao encontrou nada (raro).
        chave_conflito = "imdb_id" if imdb_id else "titulo"

        response_filme = supabase.table("filmes").upsert(
            dados_filme,
            on_conflict=chave_conflito
        ).execute()

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


def salvar_dados_youtube(titulo: str, trailer_url: str, imagem_url_youtube: str):
    """
    Atualiza os dados do YouTube de um filme já salvo no banco.
    """
    try:
        supabase.table("filmes").update({
            "trailer_url_youtube": trailer_url,
            "imagem_url_youtube": imagem_url_youtube,
        }).eq("titulo", titulo).execute()

        print(f"YouTube atualizado para '{titulo}'.")

    except Exception as e:
        print(f"Erro ao atualizar YouTube para '{titulo}': {e}")

def salvar_bilheteria_mojo(titulo: str, bilheteria: str):
    """
    Atualiza a bilheteria do Box Office Mojo de um filme já salvo no banco.
    """
    try:
        if bilheteria:
            supabase.table("filmes").update({
                "bilheteria_mojo": bilheteria,
            }).eq("titulo", titulo).execute()
            
            print(f"💰 Bilheteria atualizada para '{titulo}': {bilheteria}")
        else:
            print(f"⚠️ Bilheteria não encontrada para '{titulo}'")
            
    except Exception as e:
        print(f"Erro ao atualizar bilheteria para '{titulo}': {e}")