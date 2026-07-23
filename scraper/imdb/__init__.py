from scraper.imdb.browser import create_browser, close_browser
from scraper.imdb.imdb_search import get_film_link
from scraper.imdb.imdb_movie import get_movie_data


def buscar_dados_imdb(titulo_filme: str) -> dict | None:
    """
    Busca os dados de um filme no IMDb.

    titulo_filme: nome do filme (ex: "Moana")

    Retorno: dict com imdb_id, nota_imdb, popularidade e classificacao,
    ou None se nao encontrar o filme.
    """
    playwright, browser, page = create_browser(headless=True)

    try:
        link = get_film_link(page, titulo_filme)
        if not link:
            print(f"  ⚠️ Filme não encontrado no IMDb: '{titulo_filme}'")
            return None

        filme = get_movie_data(page, link)
        if not filme:
            print(f"  ⚠️ Dados do IMDb incompletos para '{titulo_filme}'")
            return None

        return {
            "imdb_id": filme.imdb_id,
            "nota_imdb": filme.imdb_rating,
            "popularidade_imdb": filme.popularity,
            "duracao": filme.duration,
        }

    except Exception as e:
        print(f"  ⚠️ Erro no scraper do IMDb para '{titulo_filme}': {e}")
        return None

    finally:
        close_browser(playwright, browser)