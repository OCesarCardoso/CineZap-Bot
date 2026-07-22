# Objetivo do main.py:

# 1. Escolher a cidade.
# 2. Buscar os filmes em cartaz.
# 3. Para cada filme, buscar os detalhes e as sessões.
# 4. Salvar tudo no banco.
# 5. Exibir um resumo no terminal.

from scraper.ingresso import listar_filmes_em_cartaz
from scraper.ingresso import listar_sessoes_do_filme

from database.supabase_client import salvar_dados_ingresso


cidade = "uberlandia"

print(f"Buscando filmes em cartaz em {cidade}...\n")

filmes = listar_filmes_em_cartaz(cidade)

print(f"{len(filmes)} filmes encontrados.\n")

for filme in filmes:

    print(f"Processando: {filme['titulo']}")

    detalhes = listar_sessoes_do_filme(
        cidade,
        filme["url_key"]
    )

    titulo = detalhes["filme"].get("titulo") or filme["titulo"]

    salvar_dados_ingresso(
        filme_dados={
            "titulo": titulo,
            "url": f"https://www.ingresso.com/filme/{filme['url_key']}",
            "imagem_url": detalhes["filme"].get("imagem_url"),
            "duracao": detalhes["filme"].get("duracao"),
            "classificacao": detalhes["filme"].get("classificacao"),
            "diretor": detalhes["filme"].get("diretor"),
            "generos": detalhes["filme"].get("generos", []),
            "elenco": detalhes["filme"].get("elenco", []),
            "trailer_url": detalhes["filme"].get("trailer_url"),
        },
        sinopse=detalhes["filme"].get("sinopse"),
        sessoes_lista=[
            {
                "cinema": s["cinema_nome"],
                "horario": s["horario"],
                "link_compra": s["checkout_url"]
            }
            for s in detalhes["sessoes"]
            if s["cinema_nome"] and s["horario"]
        ],
        cidade_slug=cidade
    )

    print("OK\n")


print("Scraping finalizado!")
