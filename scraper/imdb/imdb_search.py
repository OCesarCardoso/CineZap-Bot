from urllib.parse import quote_plus


def get_film_link(page, movie_name: str) -> str | None:
    query = quote_plus(movie_name)
    page.goto(f"https://www.imdb.com/find/?q={query}")
    page.wait_for_timeout(3000)

    links = page.locator("a[href*='/title/tt']")

    if links.count() == 0:
        return None

    link = links.nth(0).get_attribute("href")
    if not link:
        return None

    return "https://www.imdb.com" + link