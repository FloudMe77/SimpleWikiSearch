import search_engine
import sqlite3
from collections import defaultdict
from scipy.sparse import csc_matrix
import simplifier

class Search_engine_manager:
    def __init__(self, database_name, start = True, svd_on = True, k = 300):
        self.simplifier = simplifier.Simplifier()
        self.database_name = database_name
        self.en = search_engine.Engine(database_name = database_name, svd_on = svd_on, k = k)
        if not start:
            self.press_db_in_engine()
        self.en.start_engine()

    def parse_query(self, query):
        words = self.simplifier.simplify_words(query)
        counts = defaultdict(int)
        for word in words:
            if word in self.en.word_to_number:
                counts[self.en.word_to_number[word]] += 1
        indices, values = zip(*counts.items()) if counts else ([], [])
        n_words = len(self.en.number_to_word)
        return csc_matrix((values, (indices, [0] * len(indices))), shape=(n_words, 1))
    
    def hendle_query(self, query, number_of_position = 10):
        query_vector = self.parse_query(query)
        return self.en.handleQuery(query_vector, number_of_position)

    def press_db_in_engine(self):
        print("start parsing database")
        conn = sqlite3.connect(f"{self.database_name}.db")
        cursor = conn.cursor()
        cursor.execute('SELECT id, content FROM articles ')
        for id,content in cursor.fetchall():
            self.en.add_article(id,content)
        print("Matrix built")
