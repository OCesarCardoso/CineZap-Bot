from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, parse_qs
import time


def buscar_trailer_youtube(titulo_filme: str) -> dict:
    """
    Busca o primeiro trailer do filme no YouTube.

    titulo_filme: nome do filme (ex: "Moana")

    Retorno: dict com trailer_url e imagem_url_youtube,
             ou dict vazio se não encontrar.
    """
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(
        options=options,
        service=Service(ChromeDriverManager().install())
    )

    query = titulo_filme.strip().replace(" ", "+")
    url = f"https://www.youtube.com/results?search_query=trailer+{query}"

    driver.get(url)
    time.sleep(5)

    try:
        videos = driver.find_elements(By.TAG_NAME, "ytd-video-renderer")
        if not videos:
            return {}

        elem = videos[0].find_element(By.ID, "video-title")
        href = elem.get_attribute("href") or ""
        if "v=" not in href:
            return {}

        video_id = parse_qs(urlparse(href).query).get("v", [None])[0]
        if not video_id:
            return {}

        return {
            "trailer_url": f"https://www.youtube.com/watch?v={video_id}",
            "imagem_url_youtube": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        }

    except Exception as e:
        print(f"Erro no scraper do YouTube para '{titulo_filme}': {e}")
        return {}

    finally:
        driver.quit()