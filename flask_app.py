from flask import Flask, render_template, request
import search_engine_manager
import sqlite3
import database_manager

app = Flask(__name__)

# Configuration
DATABASE_NAME = 'simplewiki100'
SEARCH_ENGINE = search_engine_manager.Search_engine_manager(DATABASE_NAME, svd_on=True, k=200)
# SEARCH_ENGINE = search_engine_manager.Search_engine_manager(DATABASE_NAME, svd_on=True, k=750)
# SEARCH_ENGINE = search_engine_manager.Search_engine_manager(DATABASE_NAME, svd_on=True, k=300, start=False)
DB_MANAGER = database_manager.DatabaseManager(DATABASE_NAME)


def get_data(items, index_tab):
    """Fetch data from the database based on given item fields and indices."""
    conn = sqlite3.connect(f"{DATABASE_NAME}.db")
    cursor = conn.cursor()
    placeholders = ','.join(str(i + 1) for i in index_tab)
    query = f"SELECT {items} FROM articles WHERE id IN ({placeholders})"
    return cursor.execute(query).fetchall()


@app.route('/')
@app.route('/index')
def index():
    """Render the index page."""
    return render_template('index.html')


@app.route('/flask_app')
def get_search():
    """Handle search queries and render search results."""
    fraze = request.args.get("fraze")
    raw_data = SEARCH_ENGINE.hendle_query(fraze)
    indexes, rates = zip(*raw_data)
    indexes = list(indexes)
    rates = list(rates)

    results = [
        {"url": url, "title": title, "intro": intro}
        for url, title, intro in DB_MANAGER.get_data("url, title, intro", indexes)
    ]

    for i, rate in enumerate(rates):
        results[i]["rate"] = rate

    return render_template("search_result.html", title=fraze, results=results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
