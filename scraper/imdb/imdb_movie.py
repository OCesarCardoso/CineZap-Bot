import re
import json
from scraper.models.movie import Movie


def get_movie_data(page, movie_link: str) -> Movie | None:
    """
    Extrai os dados estruturados (JSON-LD) da pagina do filme no IMDb.

    Retorno: instancia de Movie, ou None se a pagina nao tiver os dados
    esperados.
    """
    page.goto(movie_link)

    json_ld = page.locator('script[type="application/ld+json"]')
    if json_ld.count() == 0:
        return None

    try:
        data = json.loads(json_ld.first.inner_text())
    except json.JSONDecodeError:
        return None

    match_id = re.search(r"tt\d+", movie_link)
    if not match_id:
        return None
    imdb_id = match_id.group()

    diretores = data.get("director") or []
    stars = [a.get("name") for a in data.get("actor", []) if a.get("name")]

    popularity = None
    popularidade_locator = page.locator('[data-testid="hero-rating-bar__popularity"]').first
    if popularidade_locator.count() > 0:
        numeros = re.findall(r"\d+", popularidade_locator.inner_text())
        if numeros:
            popularity = numeros[0]

    return Movie(
        imdb_id=imdb_id,
        title=data.get("name"),
        popularity=popularity,
        parental_guide=data.get("contentRating"),
        director=diretores[0].get("name") if diretores else None,
        stars=stars or None,
        release_date=data.get("datePublished"),
        imdb_rating=(data.get("aggregateRating") or {}).get("ratingValue"),
        duration=data.get("duration"),
    )