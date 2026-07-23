from scraper.ingresso import listar_filmes_em_cartaz, listar_sessoes_do_filme
from scraper.youtube import buscar_trailer_youtube
from scraper.mojo import buscar_bilheteria_mojo
from scraper.imdb import buscar_dados_imdb
from database.supabase_client import (
    salvar_dados_ingresso,
    salvar_dados_youtube,
    salvar_bilheteria_mojo,
    limpar_sessoes_da_cidade,
)

cidade = "uberlandia"

print(f"Buscando filmes em cartaz em {cidade}...\n")

limpar_sessoes_da_cidade(cidade)

filmes = listar_filmes_em_cartaz(cidade)

print(f"{len(filmes)} filmes encontrados.\n")

for filme in filmes:
    print(f"Processando: {filme['titulo']}")

    detalhes = listar_sessoes_do_filme(cidade, filme["url_key"])
    titulo = detalhes["filme"].get("titulo") or filme["titulo"]

    # IMDb
    print(f"  Buscando dados no IMDb...")
    imdb = buscar_dados_imdb(titulo)

    # Ingresso.com
    salvar_dados_ingresso(
        filme_dados={
            "titulo": titulo,
            "url": f"https://www.ingresso.com/filme/{filme['url_key']}",
            "imagem_url": detalhes["filme"].get("imagem_url"),
            "duracao": imdb.get("duracao") if imdb else detalhes["filme"].get("duracao"),
            "classificacao": detalhes["filme"].get("classificacao"),
            "diretor": detalhes["filme"].get("diretor"),
            "generos": detalhes["filme"].get("generos", []),
            "elenco": detalhes["filme"].get("elenco", []),
            "imdb_id": imdb.get("imdb_id") if imdb else None,
            "nota_imdb": imdb.get("nota_imdb") if imdb else None,
            "popularidade_imdb": imdb.get("popularidade_imdb") if imdb else None,
        },
        sinopse=detalhes["filme"].get("sinopse"),
        sessoes_lista=[
            {
                "cinema": s["cinema_nome"],
                "horario": s["horario"],
                "link_compra": s["checkout_url"],
                "tipo_sessao": s.get("tipo_sessao"),
                "preco_sem_taxa": s.get("preco_sem_taxa"),
                "preco_com_taxa": s.get("preco_com_taxa"),
            }
            for s in detalhes["sessoes"]
            if s["cinema_nome"] and s["horario"]
        ],
        cidade_slug=cidade
    )

    # YouTube
    youtube = buscar_trailer_youtube(titulo)
    if youtube:
        salvar_dados_youtube(titulo, youtube["trailer_url"], youtube["imagem_url_youtube"])

    # Box Office Mojo
    print(f"  Buscando bilheteria no Box Office Mojo...")
    bilheteria = buscar_bilheteria_mojo(titulo)
    if bilheteria:
        salvar_bilheteria_mojo(titulo, bilheteria)
    else:
        print(f"  Bilheteria não encontrada para '{titulo}'")

    print()

print("Scraping finalizado!")