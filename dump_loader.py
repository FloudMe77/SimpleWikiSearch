import mwxml
import mwparserfromhell
import sqlite3
import re

conn = sqlite3.connect('simplewiki2.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                title TEXT,
                intro TEXT,
                content TEXT
            )''')
conn.commit()

def clean_text(wiki_text):
    # Parsowanie i usuwanie kodu wiki
    wikicode = mwparserfromhell.parse(wiki_text)
    text = wikicode.strip_code()

    # Usuwanie niechcianych linii (thumb, right, left, center, itp.)
    text = re.sub(r'^.*\b(?:thumb|right|left|center)\b.*$', '', text, flags=re.MULTILINE)

    # Usuwanie nadmiarowych nowych linii, spacji i tabulatorów
    text = re.sub(r'[ \t]+', ' ', re.sub(r'\n{2,}', '\n\n', text))

    # Usuwanie resztek formatowania
    text = re.sub(r'\b(?:[0-9]+\s*px|[0-9]+x[0-9]+px|thumb|right|left|center)\b\|?', '', text, flags=re.IGNORECASE)

    return text.strip()

def count_words(text):
    return len(re.findall(r'\b\w+\b', text))

def main():
    dump_path = "dump/simplewiki-latest-pages-articles.xml"
    cnt = 0
    with open(dump_path, 'r', encoding='utf-8') as f:
        dump = mwxml.Dump.from_file(f)

        # transakcje dla większej wydajności
        c.execute('BEGIN TRANSACTION;')

        for page in dump.pages:
            if page.redirect is not None or page.namespace != 0:
                continue  # pomijamy przekierowania i inne przestrzenie nazw

            for revision in page:
                title = page.title
                wiki_text = revision.text
                if not wiki_text:
                    continue

                clean = clean_text(wiki_text)
                if count_words(clean) < 100:
                    continue  

                if cnt % 1000 == 0:
                    print(f'Przetworzono {cnt} artykułów')

                cnt += 1

                intro = clean.split("\n\n")[0].strip()

                url = f"https://simple.wikipedia.org/wiki/{title.replace(' ', '_')}"

                c.execute('''
                    INSERT INTO articles (url, title, intro, content)
                    VALUES (?, ?, ?, ?)
                ''', (url, title, intro, clean))

                # Commit co 1000 artykułów
                if cnt % 1000 == 0:
                    conn.commit()

        # Zakończenie transakcji po przetworzeniu wszystkich stron
        c.execute('COMMIT;')

    conn.close()

if __name__ == "__main__":
    main()