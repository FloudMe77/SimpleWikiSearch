from collections import defaultdict
from scipy.sparse import csr_matrix, csc_matrix, diags, linalg
import numpy as np
import heapq
from sklearn.preprocessing import normalize
from scipy.sparse import save_npz, load_npz
import pickle
from scipy.sparse.linalg import svds
import simplifier
import hnswlib
import os

class Engine:

    def __init__(self, database_name = '', svd_on = False, k = None):
        # svd_on - determinuje, czy używamy svd przy wyszukiwaniu, czy nie
        # k - liczba największych wartości osobliwych (singular values) w SVD

        word_matrix_path = f"saved_data/csc_BOW_{database_name}.npz"
        word_structures_path = f"saved_data/word_structures_{database_name}.pkl"
        print(word_structures_path)
        self.is_matrix_saved = self.file_exist(word_matrix_path) and self.file_exist(word_structures_path)
        self.database_name = database_name

        if self.is_matrix_saved:
            self.read_BOW_from_file()
        else:
            print(self.file_exist(word_matrix_path))
            print(self.file_exist(word_structures_path))
            self.number_to_word = []
            self.word_to_number = dict()
            self.tuple_BOW = []
            self.n_articles = 0
            self.csc_BOW = None 
            self.articles_with_word = defaultdict(int)
            self.simplifier = simplifier.Simplifier()
        
        
        self.svd_on = svd_on
        self.k = k

    def file_exist(self,path_name):
        return os.path.exists(path_name) and os.path.isfile(path_name)

    def content_to_tuple_matrix(self, words, id):
        unique_words = set()
        counts = defaultdict(int)
        for word in words:
            if word not in self.word_to_number:
                # następny wolny numerek
                self.word_to_number[word] = len(self.number_to_word)
                self.number_to_word.append(word)

            if word not in unique_words:
                # inkrementacja liczby artykułów z tym słowem
                self.articles_with_word[word] += 1
                unique_words.add(word)
                
            counts[self.word_to_number[word]] += 1
            
        return [(id, col, val) for col, val in counts.items()]

    def add_article(self, id, content):
        words = self.simplifier.simplify_words(content)
        # indeksy w bazie danych zaczynają się od 1, a w macierzy od 0
        new_tuples = self.content_to_tuple_matrix(words, id-1)
        
        self.tuple_BOW.extend(new_tuples)
        self.n_articles += 1

    def create_csr_matrix(self):
        print("start_create_csr_matrix")
        
        if not self.tuple_BOW:
            return csr_matrix((0, 0))
        
        rows, cols, data = zip(*self.tuple_BOW)
        shape = (self.n_articles, max(cols) + 1)
        print("end_create_csr_matrix")
        return csr_matrix((data, (rows, cols)), shape=shape)

    def start_engine(self):
        if not self.is_matrix_saved:
            self.IDF_and_normalization()
            self.save_BOW_to_file()

        if self.svd_on:
            if self.file_exist(f"saved_svd/svd{self.k}_{self.database_name}.pkl"):
                self.read_SVD_from_file()
            else:
                self.lower_rank()

    def IDF_and_normalization(self):
        print("start idf")

        self.csc_BOW = self.create_csr_matrix()  # ustawia self.csc_BOW (TF)

        self.info()

        N = self.csc_BOW.shape[0]  # liczba dokumentów
        M = self.csc_BOW.shape[1]  # liczba słów

        idf = [np.log(N / self.articles_with_word[self.number_to_word[i]]) for i in range(M)]
        self.idf_diag = diags(idf)
        tf_idf = self.csc_BOW @ self.idf_diag

        # Transpozycja: wiersze = słowa, kolumny = dokumenty
        tf_idf = tf_idf.T

        # Normalizacja  dokumentów
        tf_idf = normalize(tf_idf, axis=0, norm='l2')
        self.csc_BOW = tf_idf 
        print("end idf")

    def handleQuery(self, query_vector, top):
        # w zależności czy svd
        return self.handleQueryUVD(query_vector, top) if self.svd_on else self.handleQueryNormal(query_vector, top)
    
    def handleQueryUVDClassic(self, query_vector, top=10):
        # query_vector: sparse (n_words,)
        # 1. Normalizacja zapytania
        normalized_query = query_vector / linalg.norm(query_vector)
        result = (normalized_query.T @ self.U @ self.D @ self.Vt).T  # (N, 1)
        similarities = result.flatten()
        top_indices = heapq.nlargest(top, range(len(similarities)), key=lambda i: similarities[i])

        return [(i, round(similarities[i]*100,1)) for i in top_indices]
    def handleQueryNormal(self, query_vector, top):
        normalized_query = query_vector / linalg.norm(query_vector)
        result = np.abs((normalized_query.T @ self.csc_BOW)).T  # (N, 1)
        similarities = result.flatten()
        top_indices = heapq.nlargest(top, range(len(similarities)), key=lambda i: similarities[i])

        return [(i, round(similarities[i]*100,1)) for i in top_indices]
    
    def lower_rank(self):
        print("start decomposition")
        U, D, Vt = svds(self.csc_BOW, k=self.k)

        self.U = U
        self.Vt = Vt
        self.D = diags(D)
        self.D_values = D.astype('float32')  # przyda się później

        # Przekształcamy dokumenty do przestrzeni zredukowanej
        X_reduced = (np.diag(D) @ Vt).T.astype('float32')  # shape: (n_docs, k)

        # Budujemy HNSW index
        dim = self.k
        self.index = hnswlib.Index(space='cosine', dim=dim)
        self.index.init_index(max_elements=X_reduced.shape[0], ef_construction=200, M=32)
        self.index.add_items(X_reduced)
        self.index.set_ef(200)

        print("end decomposition + HNSW")
        self.save_SVD_to_file()

    def handleQueryUVD(self, query_vector, top=10):
        # if self.idf_diag:
        #     query_vector = self.idf_diag @ query_vector

        norm = linalg.norm(query_vector)
        if norm == 0:
            return []

        normalized_query = query_vector / norm

        q = self.U.T @ normalized_query  
        q = self.D @ q
        q_dense = q.flatten().astype('float32').reshape(1, -1)

        # Szukanie przez HNSW
        labels, distances = self.index.knn_query(q_dense, k=top)

        return [(int(i), round((1 - d) * 100, 1)) for i, d in zip(labels[0], distances[0])]

    def info(self):
        print(self.csc_BOW.shape)
    
    def save_BOW_to_file(self):
        print("start saving BOW")

        save_npz(f"saved_data/csc_BOW_{self.database_name}.npz", self.csc_BOW)
        with open(f"saved_data/word_structures_{self.database_name}.pkl", "wb") as f:
            pickle.dump({
                "number_to_word": self.number_to_word,
                "word_to_number": self.word_to_number,
                "idf_diag": self.idf_diag
            }, f)
        print("end saving BOW")

    def read_BOW_from_file(self):
        print("start reading BOW")

        self.csc_BOW = load_npz(f"saved_data/csc_BOW_{self.database_name}.npz")
        with open(f"saved_data/word_structures_{self.database_name}.pkl", "rb") as f:
            data = pickle.load(f)
            self.number_to_word = data["number_to_word"]
            self.word_to_number = data["word_to_number"]
            if "idf_diag" in data:
                self.idf_diag = data["idf_diag"]
            else:
                self.idf_diag = None
        print("end reading BOW")

    def save_SVD_to_file(self):
        print("start saving SVD")

        with open(f"saved_svd/svd{self.k}_{self.database_name}.pkl", "wb") as f:
            pickle.dump({
                "U": self.U,
                "D": self.D,
                "Vt": self.Vt,
                "index": self.index
            }, f)
        print("end saving SVD")

    def read_SVD_from_file(self):
        print("start reading SVD")
        with open(f"saved_svd/svd{self.k}_{self.database_name}.pkl", "rb") as f:
            data = pickle.load(f)
            self.U = data["U"]
            self.D = data["D"]
            self.Vt = data["Vt"]
            self.index = data["index"]
        print("end reading SVD")