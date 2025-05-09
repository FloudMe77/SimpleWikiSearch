import sqlite3

class DatabaseManager:
    def __init__(self,database_name):
        self.database_name = database_name
    
    def get_connection(self):
        return sqlite3.connect(f"{self.database_name}.db")

    def get_all_content(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            return cursor.execute('SELECT content FROM articles').fetchall()
    
    def get_data(self,items, index_tab):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ','.join(str(i + 1) for i in index_tab)
            query = f"SELECT {items} FROM articles WHERE id IN ({placeholders})"
            return cursor.execute(query).fetchall()
