"""
utils/subject_detect.py
Keyword-based subject detection used as a fast, free first pass — and as the
fallback when OPENAI_API_KEY isn't set, so subject detection still works
without an AI key. When a key IS configured, routes/study_coach.py asks the
model to confirm/override this guess (the model sees the actual note content,
so it catches subjects this keyword list doesn't).
"""
import re

SUBJECT_KEYWORDS: dict[str, list[str]] = {
    "Java": ["java", "jvm", "jdk", "bytecode", "extends", "implements"],
    "Advanced Java": ["servlet", "jsp", "jdbc", "spring boot", "hibernate"],
    "JavaScript": ["javascript", "settimeout", "===", "const ", "let ", "dom manipulation"],
    "Python": ["python", "def ", "self.", "import numpy", "pandas", "list comprehension"],
    "C Programming": ["printf", "scanf", "malloc(", "#include <stdio", "pointer arithmetic"],
    "C++": ["c++", "cout <<", "cin >>", "namespace std", "virtual function"],
    "DBMS": ["dbms", "sql query", "normalization", "primary key", "foreign key", "relational database", "er diagram"],
    "Operating System": ["operating system", "deadlock", "process scheduling", "semaphore", "page replacement", "paging", "thread"],
    "Data Communication & Networking": ["osi model", "tcp/ip", "data communication", "bandwidth", "network topology"],
    "Computer Networks": ["computer network", "router", "subnet", "ip address", "switching"],
    "Network Security & Management": ["network security", "firewall", "encryption", "cryptography", "intrusion detection"],
    "Artificial Intelligence": ["artificial intelligence", "heuristic search", "knowledge representation", "turing test"],
    "Machine Learning": ["machine learning", "supervised learning", "regression", "overfitting", "training data", "neural network"],
    "Deep Learning": ["deep learning", "cnn", "convolutional", "backpropagation", "gradient descent", "tensorflow", "pytorch"],
    "Emerging Trends & Technology": ["blockchain", "iot", "internet of things", "quantum computing", "edge computing"],
    "Software Engineering": ["software engineering", "sdlc", "agile", "waterfall model", "requirement analysis"],
    "Data Structures & Algorithms": ["data structure", "linked list", "binary tree", "time complexity", "big o", "stack", "queue"],
    "Web Development": ["web development", "frontend", "backend", "http request", "rest api"],
    "HTML": ["<html", "<div", "<body", "html tag"],
    "CSS": ["css", "flexbox", "grid-template", "stylesheet"],
    "React.js": ["react", "usestate", "useeffect", "jsx", "component"],
    "Mathematics": ["derivative", "integral", "theorem", "matrix", "eigenvalue", "differential equation"],
    "Statistics": ["standard deviation", "regression analysis", "probability distribution", "hypothesis testing"],
    "Physics": ["newton's law", "velocity", "thermodynamics", "electric field", "quantum mechanics"],
    "Chemistry": ["chemical reaction", "molecule", "periodic table", "covalent bond", "acid base"],
    "Biology": ["cell membrane", "photosynthesis", "dna", "mitochondria", "evolution"],
    "Economics": ["supply and demand", "gdp", "inflation", "market equilibrium", "macroeconomics"],
    "Accounting": ["balance sheet", "debit", "credit", "ledger", "trial balance"],
    "Business Management": ["management", "organizational behavior", "marketing strategy", "human resource"],
    "Law": ["legal", "jurisdiction", "plaintiff", "defendant", "statute"],
}


def detect_subject(text: str) -> tuple[str, float]:
    """Returns (best_guess_subject, confidence 0-1). Falls back to 'Custom Subject' when nothing matches."""
    if not text or not text.strip():
        return "Custom Subject", 0.0

    lowered = text.lower()
    scores: dict[str, int] = {}
    for subject, keywords in SUBJECT_KEYWORDS.items():
        hits = sum(len(re.findall(re.escape(kw), lowered)) for kw in keywords)
        if hits:
            scores[subject] = hits

    if not scores:
        return "Custom Subject", 0.0

    best = max(scores, key=scores.get)
    total_hits = sum(scores.values())
    confidence = min(0.95, round(scores[best] / max(total_hits, 1) * 0.6 + min(scores[best] / 5, 0.35), 2))
    return best, confidence
