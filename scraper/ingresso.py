"""
Scraper do ingresso.com

Extraímos os blocos <script type="application/ld+json"> que o
site ja usa para SEO. Sao dados estruturados, estaveis e confiaveis.

Duas funcoes principais:
    listar_filmes_em_cartaz(cidade) -> lista de filmes em cartaz na cidade
    listar_sessoes_do_filme(cidade, filme_url_key) -> cinemas/horarios do filme
"""

import json
import re
from playwright.sync_api import sync_playwright


def _extrair_blocos_json_ld(html: str) -> list[dict]:
    """
    Encontra todos os blocos [script type='application/ld+json'] e retorna
    como lista de dicionarios ja parseados.
    """
    padrao = re.compile(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
        re.DOTALL,
    )
    blocos = []
    for match in padrao.finditer(html):
        texto = match.group(1).strip()
        try:
            blocos.append(json.loads(texto))
        except json.JSONDecodeError:
            continue
    return blocos


def _carregar_pagina(url: str, headless: bool = True) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(6000)
        html = page.content()
        browser.close()
        return html


def listar_filmes_em_cartaz(cidade: str) -> list[dict]:
    """
    Retorna a lista de filmes REALMENTE em cartaz numa cidade.

    Extraimos diretamente dos cartoes de filme visiveis na pagina
    (elementos com data-testid="event-item"), que sao os que o site
    realmente exibe como "em cartaz" para a cidade selecionada.

    cidade: slug da cidade no formato do ingresso.com (ex: "uberlandia")

    Retorno: lista de dicts, cada um com:
        titulo, url_key (usado para montar a URL da pagina do filme)
    """
    url = f"https://www.ingresso.com/filmes/em-cartaz?city={cidade}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(6000)

        # Pega todos os cartoes de filme realmente exibidos na pagina
        cartoes = page.query_selector_all('[data-testid="event-item"]')

        filmes = []
        vistos = set()  # evita duplicados (o mesmo filme pode aparecer 2x na pagina)

        for cartao in cartoes:
            link_elemento = cartao.query_selector("a")
            if not link_elemento:
                continue

            href = link_elemento.get_attribute("href") or ""
            titulo_elemento = cartao.query_selector("h4")
            titulo = titulo_elemento.inner_text().strip() if titulo_elemento else ""

            # extrai o url_key do link, ex: "/filme/moana?city=uberlandia" -> "moana"
            if "/filme/" in href:
                url_key = href.split("/filme/")[1].split("?")[0]
            else:
                continue

            if url_key in vistos or not titulo:
                continue
            vistos.add(url_key)

            filmes.append({"titulo": titulo, "url_key": url_key})

        browser.close()
        return filmes


def listar_sessoes_do_filme(cidade: str, filme_url_key: str) -> dict:
    """
    Retorna detalhes do filme + todas as sessoes (cinema, horario, link de compra)
    numa cidade.

    cidade: slug da cidade (ex: "uberlandia")
    filme_url_key: slug do filme na URL (ex: "moana")

    Retorno: dict com:
        filme: {titulo, sinopse, duracao_minutos, classificacao, generos,
                diretor, elenco, trailer_url}
        sessoes: lista de {cinema_nome, cinema_endereco, horario, checkout_url}
    """
    url = f"https://www.ingresso.com/filme/{filme_url_key}?city={cidade}"
    html = _carregar_pagina(url)
    blocos = _extrair_blocos_json_ld(html)

    resultado = {"filme": {}, "sessoes": []}

    for bloco in blocos:
        grafo = bloco.get("@graph", [])
        for item in grafo:
            tipo = item.get("@type")

            if tipo == "Movie":
                resultado["filme"] = {
                    "titulo": item.get("name"),
                    "sinopse": item.get("description"),
                    "duracao": item.get("duration"),  # formato ISO 8601 (ex: PT115M)
                    "classificacao": item.get("contentRating"),
                    "generos": item.get("genre", []),
                    "diretor": (item.get("director") or {}).get("name"),
                    "elenco": [a.get("name") for a in item.get("actor", [])],
                    "trailer_url": (item.get("trailer") or {}).get("embedUrl"),
                    "imagem_url": item.get("image"),
                }

            elif tipo == "ScreeningEvent":
                cinema = item.get("location", {})
                endereco = cinema.get("address", {})
                oferta = item.get("offers", {})

                resultado["sessoes"].append({
                    "cinema_nome": cinema.get("name"),
                    "cinema_endereco": endereco.get("streetAddress"),
                    "horario": item.get("startDate"),  # formato ISO: 2026-07-22T12:10:00-03:00
                    "checkout_url": oferta.get("url"),
                    "disponivel": oferta.get("availability") == "https://schema.org/InStock",
                })

    return resultado


# print("=== Filmes em cartaz em Uberlandia (fonte corrigida) ===")
# filmes = listar_filmes_em_cartaz("uberlandia")
# print(f"Total encontrado: {len(filmes)}\n")
# for f in filmes:
#     print(f"- {f['titulo']} (url_key: {f['url_key']})")

# print("\n=== Sessoes de Moana em Uberlandia ===")
# detalhes = listar_sessoes_do_filme("uberlandia", "moana")
# print(f"Filme: {detalhes['filme'].get('titulo')}")
# print(f"Sinopse: {detalhes['filme'].get('sinopse', '')[:100]}...")
# print(f"\nTotal de sessoes encontradas: {len(detalhes['sessoes'])}")
# for s in detalhes["sessoes"][:5]:
#     print(f"- {s['cinema_nome']} | {s['horario']}")