import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize # Lepszy tokenizer

try:
    stopwords.words('english')
except LookupError:
    nltk.download('stopwords')
try:
    word_tokenize("test")
except LookupError:
    nltk.download('punkt') 
try:
    nltk.pos_tag(["test"])
except LookupError:
    nltk.download('averaged_perceptron_tagger') 
try:
    WordNetLemmatizer().lemmatize("cars")
except LookupError:
    nltk.download('wordnet')


class Simplifier:
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        # Mapa tagów POS dla lematyzatora
        self.pos_map = {
            'NN': 'n', 'NNS': 'n', 'NNP': 'n', 'NNPS': 'n', # Noun
            'VB': 'v', 'VBD': 'v', 'VBG': 'v', 'VBN': 'v', 'VBP': 'v', 'VBZ': 'v', # Verb
            'JJ': 'a', 'JJR': 'a', 'JJS': 'a', # Adjective
            'RB': 'r', 'RBR': 'r', 'RBS': 'r'  # Adverb
        }

    def simplify_words(self, content):
        words = word_tokenize(content)
        
        tagged_words = nltk.pos_tag(words)
        
        simplified_lemmas = []
        for word, tag in tagged_words:
            word_lower = word.lower()
            
            # Filtrowanie stop-wordów i tokenów niealfabetycznych
            if word_lower not in self.stop_words and word.isalpha():
                # Domyślnie użyj 'n' (rzeczownik), jeśli tag nie jest w mapie
                pos_tag_for_lemmatizer = self.pos_map.get(tag[:2], 'n')
                lemma = self.lemmatizer.lemmatize(word_lower, pos=pos_tag_for_lemmatizer)
                
                simplified_lemmas.append(lemma)
                    
        return simplified_lemmas