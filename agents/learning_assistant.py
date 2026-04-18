"""
Learning Assistant Agent — suggests related knowledge and identifies gaps.
"""
from db.queries import get_user_topics, get_all_topics, get_knowledge_graph


# Define topic relationships: topic → [prerequisites, related, next_steps]
TOPIC_MAP = {
    "Python": {
        "prerequisites": [],
        "related": ["SQL", "APIs", "Data Structures"],
        "next_steps": ["Flask", "Django", "Automation"],
    },
    "AI": {
        "prerequisites": ["Python"],
        "related": ["Machine Learning", "LLMs", "NLP"],
        "next_steps": ["Prompt Engineering", "Fine-tuning"],
    },
    "Machine Learning": {
        "prerequisites": ["Python", "Math Basics"],
        "related": ["Deep Learning", "AI", "Data Science"],
        "next_steps": ["Neural Networks", "scikit-learn"],
    },
    "Deep Learning": {
        "prerequisites": ["Machine Learning", "Linear Algebra"],
        "related": ["Neural Networks", "AI"],
        "next_steps": ["Transformers", "Computer Vision"],
    },
    "Neural Networks": {
        "prerequisites": ["Deep Learning", "Linear Algebra"],
        "related": ["Deep Learning", "LLMs"],
        "next_steps": ["Transformers", "PyTorch"],
    },
    "LLMs": {
        "prerequisites": ["AI", "NLP"],
        "related": ["AI", "Prompt Engineering"],
        "next_steps": ["RAG", "Fine-tuning", "Agents"],
    },
    "SQL": {
        "prerequisites": [],
        "related": ["Databases", "PostgreSQL", "SQLite"],
        "next_steps": ["Database Design", "ORMs"],
    },
    "SQLite": {
        "prerequisites": ["SQL"],
        "related": ["SQL", "PostgreSQL"],
        "next_steps": ["Database Design"],
    },
    "PostgreSQL": {
        "prerequisites": ["SQL"],
        "related": ["SQL", "SQLite"],
        "next_steps": ["Database Design", "ORMs"],
    },
    "APIs": {
        "prerequisites": ["HTTP", "JSON"],
        "related": ["REST APIs", "Python"],
        "next_steps": ["Flask", "FastAPI", "Authentication"],
    },
    "JavaScript": {
        "prerequisites": ["HTML", "CSS"],
        "related": ["React", "Node.js", "TypeScript"],
        "next_steps": ["React", "Frontend"],
    },
    "React": {
        "prerequisites": ["JavaScript", "HTML", "CSS"],
        "related": ["JavaScript", "Frontend"],
        "next_steps": ["Next.js", "State Management"],
    },
}


def suggest_related() -> str:
    """Suggest topics related to what user has been learning."""
    user_topics = get_user_topics()
    if not user_topics:
        return "You haven't explored any topics yet! Ask me about anything."

    suggestions = []
    for ut in user_topics:
        topic = ut["topic_name"]
        if topic in TOPIC_MAP:
            for related in TOPIC_MAP[topic]["related"]:
                if related not in [t["topic_name"] for t in user_topics]:
                    suggestions.append(f"Since you studied {topic}, you might enjoy learning about {related}")

    if suggestions:
        return "\n".join([f"  • {s}" for s in suggestions[:8]])
    return "No specific suggestions yet — keep exploring and I'll find connections!"


def find_gaps() -> str:
    """Identify foundational gaps in user's knowledge."""
    user_topics = get_user_topics()
    user_topic_names = {t["topic_name"] for t in user_topics}

    gaps = []
    covered = set()

    # Find prerequisites of topics user has studied that they haven't covered
    for ut in user_topics:
        topic = ut["topic_name"]
        if topic in TOPIC_MAP:
            for prereq in TOPIC_MAP[topic]["prerequisites"]:
                if prereq not in user_topic_names and prereq not in covered:
                    gaps.append({
                        "topic": prereq,
                        "why": f"helps understand {topic}",
                        "how": "Ask me to explain it!"
                    })
                    covered.add(prereq)

    if gaps:
        lines = ["FOUNDATIONAL GAPS:"]
        for g in gaps[:5]:
            lines.append(f"  GAP: {g['topic']}")
            lines.append(f"    WHY IT MATTERS: {g['why']}")
            lines.append(f"    HOW TO START: {g['how']}")
            lines.append("")
        return "\n".join(lines)
    return "No obvious gaps — you're building a solid foundation! 🎉"


def suggest_next_steps() -> str:
    """Suggest concrete next steps based on what user has learned."""
    user_topics = get_user_topics()
    if not user_topics:
        return "Start by asking me about any topic you're curious about!"

    suggestions = []
    for ut in user_topics:
        topic = ut["topic_name"]
        if topic in TOPIC_MAP:
            for step in TOPIC_MAP[topic]["next_steps"]:
                if step not in [t["topic_name"] for t in user_topics]:
                    suggestions.append(f"After {topic}, try exploring: {step}")

    if suggestions:
        lines = ["NEXT STEPS:"]
        for s in suggestions[:5]:
            lines.append(f"  • {s}")
        return "\n".join(lines)
    return "Keep asking questions and we'll find your next direction!"
