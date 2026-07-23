import re
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def _converter_duracao_iso(duracao_iso: str | None) -> str | None:
    """
    Converte duração ISO 8601 para texto legível.
    PT2H53M -> 2h 53min
    PT96M   -> 1h 36min
    """
    if not duracao_iso:
        return None

    horas = 0
    minutos = 0

    match_h = re.search(r"(\d+)H", duracao_iso)
    match_m = re.search(r"(\d+)M", duracao_iso)

    if match_h:
        horas = int(match_h.group(1))
    if match_m:
        minutos = int(match_m.group(1))

    # Se veio só minutos (ex: PT96M), converte para horas + minutos
    total_minutos = horas * 60 + minutos
    horas = total_minutos // 60
    minutos = total_minutos % 60

    if horas and minutos:
        return f"{horas}h {minutos}min"
    elif horas:
        return f"{horas}h"
    else:
        return f"{minutos}min"


def limpar_sessoes_da_cidade(cidade_slug: str):
    """
    Remove todas as sessões dos cinemas de uma cidade antes de repovoar.
    """
    cinemas = supabase.table("cinemas").select("id").eq("cidade", cidade_slug).execute()
    cinema_ids = [c["id"] for c in cinemas.data]

    if cinema_ids:
        supabase.table("sessoes").delete().in_("cinema_id", cinema_ids).execute()
        print(f"Sessões de '{cidade_slug}' limpas.\n")


def salvar_dados_ingresso(filme_dados, sinopse, sessoes_lista, cidade_slug):
    try:
        dados_filme = {
            "titulo": filme_dados["titulo"],
            "sinopse": sinopse,
            "url_ingresso": filme_dados.get("url", ""),
            "imagem_url": filme_dados.get("imagem_url"),
            "duracao": _converter_duracao_iso(filme_dados.get("duracao")),
            "classificacao": filme_dados.get("classificacao"),
            "diretor": filme_dados.get("diretor"),
            "generos": filme_dados.get("generos", []),
            "elenco": filme_dados.get("elenco", []),
        }

        imdb_id = filme_dados.get("imdb_id")
        if imdb_id:
            dados_filme["imdb_id"] = imdb_id
            dados_filme["nota_imdb"] = filme_dados.get("nota_imdb")
            dados_filme["popularidade_imdb"] = filme_dados.get("popularidade_imdb")

        response_filme = supabase.table("filmes").upsert(
            dados_filme,
            on_conflict="titulo"
        ).execute()

        filme_id = response_filme.data[0]["id"]

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

        print(f"Sucesso! Filme '{filme_dados['titulo']}' salvo com {sessoes_salvas} sessões em {cidade_slug}.")

    except Exception as e:
        print(f"Erro ao salvar no banco: {e}")


def salvar_dados_youtube(titulo: str, trailer_url: str, imagem_url_youtube: str):
    try:
        supabase.table("filmes").update({
            "trailer_url_youtube": trailer_url,
            "imagem_url_youtube": imagem_url_youtube,
        }).eq("titulo", titulo).execute()

        print(f"YouTube atualizado para '{titulo}'.")

    except Exception as e:
        print(f"Erro ao atualizar YouTube para '{titulo}': {e}")


def salvar_bilheteria_mojo(titulo: str, bilheteria: str):
    try:
        if bilheteria:
            supabase.table("filmes").update({
                "bilheteria_mojo": bilheteria,
            }).eq("titulo", titulo).execute()

            print(f"Bilheteria atualizada para '{titulo}': {bilheteria}")
        else:
            print(f"Bilheteria não encontrada para '{titulo}'")

    except Exception as e:
        print(f"Erro ao atualizar bilheteria para '{titulo}': {e}")