from dataclasses import dataclass

@dataclass
class Movie:
    imdb_id: str
    title: str
    popularity: str | None
    parental_guide: str
    director: str
    stars: list[str] | None
    release_date: str
    imdb_rating: str
    duration: str