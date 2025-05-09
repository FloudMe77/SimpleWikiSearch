from flask import Flask, render_template, request, current_app
import search_engine_manager 
import database_manager 
import time

app = Flask(__name__)

# Configuration
DATABASE_NAME = 'simplewiki100'
K_SVD_VALUE = 200 

SEARCH_ENGINE = search_engine_manager.Search_engine_manager(DATABASE_NAME, svd_on=True, k=K_SVD_VALUE)
DB_MANAGER = database_manager.DatabaseManager(DATABASE_NAME)
DEFAULT_NUM_RESULTS = 10
NUM_RESULTS_OPTIONS = [10, 25, 50] 
NUM_RESULTS_STEP = 5 

common_template_data = {
    "database_name": DATABASE_NAME,
    "k_value_svd": K_SVD_VALUE,
    "num_results_options": NUM_RESULTS_OPTIONS,
    "num_results_step": NUM_RESULTS_STEP 
}

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', 
                           **common_template_data,
                           current_num_results=DEFAULT_NUM_RESULTS)

@app.route('/flask_app')
def get_search():
    fraze = request.args.get("fraze")
    
    num_results = int(request.args.get("num_results", DEFAULT_NUM_RESULTS))

    if not fraze:
        app.logger.info("Search phrase is empty. Redirecting to index.")
        return render_template('index.html', 
                               error="Please enter a search phrase.",
                               **common_template_data,
                               current_num_results=num_results)
    start_time = time.time()
    raw_data = SEARCH_ENGINE.hendle_query(fraze, number_of_position=num_results) 
    results = []
    if raw_data and isinstance(raw_data, list):
        if raw_data: 
            indexes, rates_raw = zip(*raw_data)
            indexes = list(indexes)

            results_db = DB_MANAGER.get_data("url, title, intro", indexes)
            
            for i, db_row in enumerate(results_db):
                if i < len(rates_raw): 
                    url, title, intro = db_row
                    results.append({
                        "url": url,
                        "title": title,
                        "intro": intro,
                        "rate": round(rates_raw[i], 2) 
                    })
            results.sort(key=lambda x: x["rate"], reverse=True)

    total_time = time.time() - start_time
    query_time_formatted = "{:.3f}".format(total_time)

    return render_template("search_result.html", 
                            title=fraze, 
                            results=results, 
                            query_time=query_time_formatted, 
                            result_count=len(results),
                            **common_template_data,
                            current_num_results=num_results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)