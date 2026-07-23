from urllib.parse import quote_plus


def get_film_link(page, movie_name: str) -> str | None:
    """
    Busca o link da pagina do filme no IMDb a partir do nome.

    Retorno: URL completa do filme no IMDb, ou None se nao encontrar.
    """
    query = quote_plus(movie_name)
    page.goto(f"https://www.imdb.com/find/?q={query}")

    links = page.locator("a[href*='/title/tt']")

    if links.count() < 2:
        return None

    link = links.nth(1).get_attribute("href")

    if not link:
        return None

    return "https://www.imdb.com" + link