"""
Scraper do ingresso.com

Playwright: lista filmes em cartaz + dados do filme (JSON-LD)
API interna: sessoes com tipo (Dublado, XD, etc.) e precos
"""

import json
import re
import requests
from playwright.sync_api import sync_playwright


# ── Helpers internos ──────────────────────────────────────────────────────────

def _extrair_blocos_json_ld(html: str) -> list[dict]:
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


def _carregar_pagina(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(6000)
        html = page.content()
        browser.close()
        return html


def _buscar_id_cidade(cidade_slug: str) -> str | None:
    """
    Busca o ID numerico da cidade na API do ingresso.com.
    ex: "uberlandia" -> "23"
    """
    url = f"https://api-content.ingresso.com/v0/states/city/name/{cidade_slug}"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        return str(data.get("id"))
    except Exception:
        return None


def _buscar_id_evento(filme_url_key: str) -> str | None:
    """
    Busca o ID numerico do filme/evento na API do ingresso.com.
    ex: "a-odisseia" -> "30413"
    """
    url = f"https://api-content.ingresso.com/v0/events/url-key/{filme_url_key}/partnership/home"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        return str(data.get("id"))
    except Exception:
        return None


def _buscar_datas_disponiveis(cidade_id: str, evento_id: str) -> list[str]:
    """
    Retorna as datas disponíveis para um filme numa cidade.
    """
    url = f"https://api-content.ingresso.com/v0/sessions/city/{cidade_id}/event/{evento_id}/dates/partnership/home"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        datas = r.json()
        return [d.get("date") for d in datas if d.get("date")]
    except Exception:
        return []


def _formatar_tipo_sessao(tipos: list[str]) -> str:
    """
    Remove "Normal" e junta os tipos restantes.
    ["Normal", "Dublado"] -> "Dublado"
    ["XD", "Legendado"]   -> "XD Legendado"
    ["Normal", "Vip", "Legendado"] -> "Vip Legendado"
    """
    tipos_filtrados = [t for t in tipos if t.lower() != "normal"]
    return " ".join(tipos_filtrados) if tipos_filtrados else "Normal"


def _buscar_preco_sessao(session_id: str, section_id: str) -> dict:
    """
    Busca preço inteira sem e com taxa de serviço para uma sessão.
    Retorna {"preco_sem_taxa": 46.0, "preco_com_taxa": 52.44}
    """
    url = f"https://api.ingresso.com/v1/sessions/{session_id}/sections/{section_id}/tickets"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        tickets = r.json().get("default", [])
        for ticket in tickets:
            if ticket.get("name", "").lower() == "inteira":
                return {
                    "preco_sem_taxa": ticket.get("price"),
                    "preco_com_taxa": ticket.get("total"),
                }
    except Exception:
        pass
    return {"preco_sem_taxa": None, "preco_com_taxa": None}


def _buscar_sessoes_por_data(cidade_id: str, evento_id: str, data: str) -> list[dict]:
    """
    Busca todas as sessoes de um filme numa cidade em uma data especifica.
    Retorna lista de sessoes com cinema, horario, tipo e preco.
    """
    url = (
        f"https://api-content.ingresso.com/v0/sessions"
        f"/city/{cidade_id}/event/{evento_id}/partnership/home/groupBy/sessionType"
    )
    try:
        r = requests.get(
            url,
            params={"date": data},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        dados = r.json()
    except Exception:
        return []

    sessoes = []

    for dia in dados:
        for teatro in dia.get("theaters", []):
            cinema_nome = teatro.get("name")
            cinema_endereco = teatro.get("address")

            for grupo in teatro.get("sessionTypes", []):
                tipo = _formatar_tipo_sessao(grupo.get("type", []))

                for s in grupo.get("sessions", []):
                    horario = s.get("date", {}).get("localDate")
                    checkout_url = s.get("siteURL") or s.get("checkoutUrl")
                    session_id = s.get("id")
                    section_id = s.get("sectionId") or s.get("room", "")

                    # Busca preço só se tiver o ID necessário
                    preco = {"preco_sem_taxa": s.get("price"), "preco_com_taxa": None}
                    if session_id and section_id and str(section_id).isdigit():
                        preco = _buscar_preco_sessao(session_id, section_id)

                    sessoes.append({
                        "cinema_nome": cinema_nome,
                        "cinema_endereco": cinema_endereco,
                        "horario": horario,
                        "tipo_sessao": tipo,
                        "preco_sem_taxa": preco["preco_sem_taxa"],
                        "preco_com_taxa": preco["preco_com_taxa"],
                        "checkout_url": checkout_url,
                    })

    return sessoes


# ── Funções públicas ──────────────────────────────────────────────────────────

def listar_filmes_em_cartaz(cidade: str) -> list[dict]:
    """
    Retorna a lista de filmes em cartaz numa cidade via Playwright.
    """
    url = f"https://www.ingresso.com/filmes/em-cartaz?city={cidade}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(6000)

        cartoes = page.query_selector_all('[data-testid="event-item"]')

        filmes = []
        vistos = set()

        for cartao in cartoes:
            link_elemento = cartao.query_selector("a")
            if not link_elemento:
                continue

            href = link_elemento.get_attribute("href") or ""
            titulo_elemento = cartao.query_selector("h4")
            titulo = titulo_elemento.inner_text().strip() if titulo_elemento else ""

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
    Retorna dados do filme (via Playwright/JSON-LD) e todas as sessoes
    de todos os dias disponiveis (via API interna do ingresso.com).
    """
    # Dados do filme via Playwright
    url = f"https://www.ingresso.com/filme/{filme_url_key}?city={cidade}"
    html = _carregar_pagina(url)
    blocos = _extrair_blocos_json_ld(html)

    resultado = {"filme": {}, "sessoes": []}

    for bloco in blocos:
        grafo = bloco.get("@graph", [])
        for item in grafo:
            if item.get("@type") == "Movie":
                resultado["filme"] = {
                    "titulo": item.get("name"),
                    "sinopse": item.get("description"),
                    "duracao": item.get("duration"),
                    "classificacao": item.get("contentRating"),
                    "generos": item.get("genre", []),
                    "diretor": (item.get("director") or {}).get("name"),
                    "elenco": [a.get("name") for a in item.get("actor", [])],
                    "trailer_url": (item.get("trailer") or {}).get("embedUrl"),
                    "imagem_url": item.get("image"),
                }

    # Sessoes via API interna
    cidade_id = _buscar_id_cidade(cidade)
    evento_id = _buscar_id_evento(filme_url_key)

    if cidade_id and evento_id:
        datas = _buscar_datas_disponiveis(cidade_id, evento_id)
        for data in datas:
            sessoes_do_dia = _buscar_sessoes_por_data(cidade_id, evento_id, data)
            resultado["sessoes"].extend(sessoes_do_dia)

    return resultado