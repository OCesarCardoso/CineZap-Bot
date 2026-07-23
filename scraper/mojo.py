"""
Scraper do Box Office Mojo

Busca a bilheteria arrecadada de um filme.
"""

import requests
from bs4 import BeautifulSoup
import re
import time


def buscar_bilheteria_mojo(titulo_filme: str) -> str:
    """
    Busca a bilheteria de um filme no Box Office Mojo
    
    titulo_filme: nome do filme (ex: "Moana")
    
    Retorno: string com a bilheteria (ex: "$1.2 billion") ou None se não encontrar
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    try:
        time.sleep(0.5)
        
        # Buscar o filme
        url_busca = f'https://www.boxofficemojo.com/search/?q={titulo_filme}'
        response = requests.get(url_busca, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Encontrar o primeiro resultado da busca
        link_filme = None
        todos_links = soup.find_all('a', href=True)
        
        for tag in todos_links:
            href = tag.get('href', '')
            if '/title/' in href and 'boxofficemojo.com' not in href:
                texto = tag.text.strip()
                if texto and len(texto) > 1 and texto.lower() != 'imdbpro':
                    link_filme = "https://www.boxofficemojo.com" + href
                    break
        
        if not link_filme:
            return None
        
        # Acessar página do filme
        response_filme = requests.get(link_filme, headers=headers, timeout=15)
        
        if response_filme.status_code != 200:
            return None
        
        soup_filme = BeautifulSoup(response_filme.content, 'html.parser')
        texto = soup_filme.get_text()
        
        # Padrões para encontrar bilheteria (em ordem de prioridade)
        padroes = [
            # Worldwide gross
            r'Worldwide\s*[:$]\s*([$]?[\d,]+(?:\.\d+)?\s*(?:million|M|bilhão|billion|B)?)',
            r'Total\s+Gross\s*[:$]\s*([$]?[\d,]+(?:\.\d+)?\s*(?:million|M|bilhão|billion|B)?)',
            # Domestic gross (USA)
            r'Domestic\s*[:$]\s*([$]?[\d,]+(?:\.\d+)?\s*(?:million|M|bilhão|billion|B)?)',
            # International gross
            r'International\s*[:$]\s*([$]?[\d,]+(?:\.\d+)?\s*(?:million|M|bilhão|billion|B)?)',
        ]
        
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                bilheteria = match.group(0).strip()
                # Remove "Worldwide", "Domestic", "International", "Gross" e ":" 
                bilheteria = re.sub(
                    r'^(Worldwide|Domestic|International|Total\s+Gross)',
                    '',
                    bilheteria,
                    flags=re.IGNORECASE
                ).strip()
                # Remove espaços extras
                bilheteria = re.sub(r'\s+', ' ', bilheteria)
                return bilheteria
        
        # Tentar encontrar qualquer valor monetário alto que pareça ser bilheteria
        match = re.search(r'[$][\d,]+(?:\.\d+)?\s*(?:million|M|bilhão|billion|B)', texto, re.IGNORECASE)
        if match:
            valor = match.group(0).strip()
            # Verificar se parece ser um valor de bilheteria (não é preço de ingresso)
            if 'million' in valor.lower() or 'billion' in valor.lower() or 'bilhão' in valor.lower():
                return valor
        
        return None
        
    except Exception as e:
        print(f"Erro ao buscar bilheteria para '{titulo_filme}': {e}")
        return None