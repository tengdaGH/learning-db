"""
Extracts topics and tags from a Q&A pair.
"""
import re

# Common topic keywords → normalize to a clean topic name
TOPIC_KEYWORDS = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "react": "React",
    "node": "Node.js",
    "html": "HTML",
    "css": "CSS",
    "sql": "SQL",
    "postgresql": "PostgreSQL",
    "sqlite": "SQLite",
    "git": "Git",
    "github": "GitHub",
    "api": "APIs",
    "rest": "REST APIs",
    "http": "HTTP",
    "json": "JSON",
    "html": "HTML",
    "css": "CSS",
    "ai": "AI",
    "artificial intelligence": "AI",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "deep learning": "Deep Learning",
    "neural network": "Neural Networks",
    "gpt": "LLMs",
    "llm": "LLMs",
    "large language model": "LLMs",
    "claude": "LLMs",
    "openai": "LLMs",
    "nlp": "NLP",
    "natural language": "NLP",
    "database": "Databases",
    "relational": "Databases",
    "web": "Web Development",
    "frontend": "Frontend",
    "backend": "Backend",
    "fullstack": "Full-Stack",
    "agile": "Agile",
    "scrum": "Scrum",
    "testing": "Testing",
    "docker": "Docker",
    "linux": "Linux",
    "bash": "Bash",
    "cloud": "Cloud Computing",
    "aws": "AWS",
    "azure": "Azure",
    "google cloud": "GCP",
}


def extract_primary_topic(question: str, answer: str = "") -> str:
    """Detect the main topic from question + answer text."""
    text = (question + " " + answer).lower()

    # Check for known topics
    matched = []
    for keyword, topic in TOPIC_KEYWORDS.items():
        if keyword in text:
            matched.append(topic)

    if matched:
        # Return most specific (longest keyword match wins)
        return matched[-1]

    # Fallback: first "noun phrase" — simplified
    words = text.split()
    for i in range(len(words) - 1, -1, -1):
        if len(words[i]) > 4 and words[i] not in {
            "what", "which", "about", "from", "with", "this", "that",
            "have", "been", "were", "they", "their", "would", "could",
        }:
            return words[i].capitalize()

    return "General"


def extract_tags(question: str, answer: str = "") -> str:
    """Extract comma-separated tags from question and answer."""
    text = (question + " " + answer).lower()

    tags = set()

    # Known tags
    for keyword, tag in TOPIC_KEYWORDS.items():
        if keyword in text:
            tags.add(tag.lower().replace(" ", "-"))

    # Extract capitalized terms (potential proper nouns / tech terms)
    combined = question + " " + answer
    caps = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", combined)
    for cap in caps:
        if len(cap) > 3 and cap.lower() not in {"what", "which", "where", "when", "how", "this", "that"}:
            tags.add(cap.lower().replace(" ", "-"))

    return ",".join(sorted(tags)) if tags else ""


def extract_sources(answer: str) -> str:
    """Find URLs or citations in the answer."""
    urls = re.findall(r"https?://[^\s\),\"]+", answer)
    return ",".join(urls) if urls else ""
