def get_film_link(page, movie_name):
    page.goto(
        f"https://www.imdb.com/find/?q={movie_name}"
    )

    link = page.locator(
        "a[href*='/title/tt']"
    ).nth(1).get_attribute("href")

    if not link:
        raise Exception(f"Nenhum filme encontrado com nome: {movie_name}")


    return "https://www.imdb.com" + link