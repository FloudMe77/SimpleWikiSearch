import requests
from bs4 import BeautifulSoup
import sqlite3
from urllib.parse import quote
import re
import time
from urllib.parse import urlparse, unquote
from collections import deque
import numpy as np
import pickle

KEYWORDS = {
    'history', 'historical', 'historian', 'historiography', 'ancient', 'medieval', 
    'renaissance', 'enlightenment', 'modern', 'prehistoric', 'neolithic', 
    'bronze age', 'iron age', 'classical', 'middle ages', 'dark ages', 
    'colonial', 'victorian', 'industrial', 'postmodern', 'contemporary', 
    'century', 'millennium', 'era', 'period', 'antiquity', 'prehistoric', 
    'pre-columbian', 'post-war', 'interwar', 'war', 'battle', 'siege', 
    'invasion', 'conquest', 'conflict', 'crusade', 'rebellion', 'revolt', 
    'uprising', 'insurrection', 'civil war', 'world war', 'campaign', 
    'revolution', 'insurgency', 'raid', 'guerrilla', 'occupation', 
    'resistance', 'combat', 'skirmish', 'offensive', 'warfare', 'empire', 
    'kingdom', 'dynasty', 'monarchy', 'republic', 'state', 'nation', 
    'civilization', 'colony', 'realm', 'territory', 'commonwealth', 'province', 
    'principality', 'duchy', 'sultanate', 'caliphate', 'confederation', 
    'federation', 'union', 'horde', 'khanate', 'shogunate', 'chiefdom'
}

def save_data(Q, visited, cnt):
    with open("saved_data/scraper3.pkl", "wb") as f:
            pickle.dump({
                "Q": Q,
                "visited": visited,
                "cnt": cnt
            }, f)
def read_data():
    with open("saved_data/scraper3.pkl", "rb") as f:
            data = pickle.load(f)
            Q = data["Q"]
            visited = data["visited"]
            cnt = data["cnt"]
    return Q, visited, cnt

def get_title_from_url(url):
    path = urlparse(url).path 
    title = path.split('/')[-1] 
    return unquote(title.replace('_', ' ')) 

conn = sqlite3.connect('historywiki.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                title TEXT,
                intro TEXT,
                content TEXT
            )''')
conn.commit()

def clean_wikipedia_text(text):
    # 1. Wyciągamy główną treść artykułu
    match = re.search(
        r"From Wikipedia, the free encyclopedia(.*)",
        text,
        re.DOTALL
    )
    content = match.group(1) if match else text

    # 2. Usuwamy przypisy w nawiasach kwadratowych, np. [1], [b]
    content = re.sub(r"\[\w{1,3}\]", "", content)

    # 3. Usuwamy fragmenty zawierające "vte"
    content = re.sub(r"\bvte\b", "", content)

    # 4. Rozdzielamy camelCase / PascalCase np. "CategoryReferance" → "Category Referance"
    content = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", content)

    # 5. Usuwamy nadmiarowe spacje i taby
    content = re.sub(r"[ \t]{2,}", " ", content)

    # 6. Redukujemy wiele nowych linii do pojedynczego
    content = re.sub(r"\n{2,}", "\n", content)

    # 7. Usuwamy puste linie i whitespace
    content = "\n".join(line.strip() for line in content.splitlines() if line.strip())

    return content

def is_history_related(title):
    return any(keyword in title.lower() for keyword in KEYWORDS)

def get_content(content, content_div, url, title):
    content = clean_wikipedia_text(content)

    # Inicjalizacja intro_paragraphs
    intro_paragraphs = ""
    
    if content_div:
        for elem in content_div.find_all(['p', 'h2']):
            if elem.name == 'p':
                text = elem.get_text(strip=True)
                if text and len(text) > 70:
                    intro_paragraphs = text
                    break
                    
        # Sprawdź czy artykuł już istnieje w bazie danych
        c.execute("SELECT id FROM articles WHERE url = ?", (url,))
        existing = c.fetchone()
        
        if not existing:  # Zapisz tylko jeśli nie istnieje
            c.execute('''
                INSERT INTO articles (url, title, intro, content)
                VALUES (?, ?, ?, ?)
            ''', (url, title, intro_paragraphs, content))
            conn.commit()
            print(f"Zapisano artykuł: {title}")
        else:
            print(f"Artykuł już istnieje w bazie: {title}")

def search(url, maxdepth, read = False):

    Q = deque()
    Q.append((url,0))
    visited = set()
    cnt=0
    last_request_start_time = time.time()
    if read:
        Q,visited,cnt = read_data()
    while Q:
        url,depth = Q.pop()
        
        if depth > maxdepth or url in visited:
            continue
            
        print(f"Przetwarzanie: {url} (głębokość: {depth})")
        visited.add(url)
        current_time = time.time()
        time_since_last_start = current_time - last_request_start_time
        
        desired_interval = np.random.uniform(0.4, 0.6)
        
        sleep_duration = desired_interval - time_since_last_start
        
        # if sleep_duration > 0:
        #     time.sleep(sleep_duration)
            
        # Zapisz czas tuż przed wysłaniem nowego requestu
        last_request_start_time = time.time() 
        
        try:
            headers = {
                'User-Agent': 'own project HistoryWikiSearch/1.0',
                'From': 'marecik7@gmail.com' 
            }

            r = requests.get(url, headers=headers)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"Błąd pobierania {url}: {e}")
            continue
        cnt+=1
        if cnt%100 ==0:
            save_data(Q, visited, cnt)
        
        
        soup = BeautifulSoup(r.text, 'html.parser')
        content_div = soup.find('div', {'id': 'mw-content-text'})
        
        if not content_div:
            continue
            
        # Sprawdź, czy to jest artykuł o historii i zapisz go
        title = get_title_from_url(url)
        if is_history_related(title) and not url.startswith('https://en.wikipedia.org/wiki/Category:'):
            get_content(soup.get_text(), content_div, url, title)
        
        # Przeszukaj linki na stronie
        else:
            for link in content_div.find_all('a')[::-1]:
                href = link.get('href')
                if href and href.startswith('/wiki/'):
                    rest = href[6:]
                    full_url = 'https://en.wikipedia.org' + href
                    
                    # Jeśli to kategoria, przejdź do niej
                    if rest.startswith('Category:') and any(keyword in rest.lower() for keyword in KEYWORDS):
                        Q.append((full_url,depth + 1))
                        
                    # Jeśli to artykuł związany z historią, dodaj go do kolejki
                    elif is_history_related(rest) and not any(rest.startswith(prefix) for prefix in ['Wikipedia:', 'Special:', 'File:', 'Help:', 'Template:']):
                        if depth < maxdepth:
                            Q.append((full_url,depth + 1))
                        
                    
    return cnt

def main():
    print("Rozpoczynam pobieranie artykułów z Wikipedii")
    
    # Początkowa strona kategorii
    start_url = "https://en.wikipedia.org/wiki/Category:History_by_location"
    
    # Maksymalna głębokość przeszukiwania
    max_depth = 5
    
    # Rozpocznij przeszukiwanie
    found_urls = search(start_url, max_depth)
    
    print(f"Znaleziono {found_urls} artykułów związanych z historią")
    
    conn.close()

if __name__ == "__main__":
    main()