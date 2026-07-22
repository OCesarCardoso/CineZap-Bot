import re
from scraper.models.movie import Movie
import json

def get_movie_data(page, movie_link):
    page.goto(movie_link)

    json_text = page.locator(
        'script[type="application/ld+json"]'
    ).inner_text()

    data = json.loads(json_text)

    imdb_id = re.search(
        r"tt\d+",
        movie_link
    ).group()

    title = data['name']

    imdb_rating = data['aggregateRating']['ratingValue']

    release_date = data['datePublished']

    duration = data['duration']

    director = data['director'][0]['name']

    stars = [
        actor['name']
        for actor in data['actor']
    ]
    parental_guide = data['contentRating']

    popularity_text = page.locator('[data-testid="hero-rating-bar__popularity"]').first.inner_text()

    popularity = re.findall(r"\d+", popularity_text)[0]

    return Movie(
        imdb_id=imdb_id,
        title=title,
        popularity=popularity,
        parental_guide=parental_guide,
        director=director,
        stars=stars,
        release_date=release_date,
        imdb_rating=imdb_rating,
        duration=duration
    )
