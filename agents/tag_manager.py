"""
TagManager Agent - automatically maintains and organizes tags for Q&A entries.
"""
import re
from typing import Optional

from db.queries import (
    get_or_create_tag,
    get_all_tags,
    get_tags_for_entry,
    set_tags_for_entry,
    delete_unused_tags,
    find_similar_tags,
    merge_tags,
    get_qa_entries_by_topic_id,
)


# Tech terms that should be normalized to their canonical form
TAG_CANONICAL = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "node": "nodejs",
    "node.js": "nodejs",
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "next.js": "nextjs",
    "nextjs": "nextjs",
    "postgresql": "postgres",
    "pg": "postgres",
    "kubernetes": "k8s",
    "k8s": "k8s",
    "llm": "llm",
    "gpt": "openai",
    "claude": "anthropic",
    "openai's": "openai",
    "anthropic's": "anthropic",
    "aws": "aws",
    "gcp": "gcp",
    "azure": "azure",
}


def normalize_tag(tag: str) -> str:
    """Normalize a tag to its canonical form."""
    tag_lower = tag.lower().strip()
    return TAG_CANONICAL.get(tag_lower, tag_lower)


def extract_tags_from_content(question: str, answer: str, existing_tags: list[str] = None) -> list[str]:
    """
    Extract meaningful tags from question and answer content.
    Returns a list of normalized tag names.
    """
    text = (question + " " + answer).lower()
    tags = set()

    # Extract capitalized terms (potential proper nouns, tech terms)
    combined = question + " " + answer
    caps = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", combined)
    for cap in caps:
        if len(cap) > 2:
            normalized = normalize_tag(cap)
            if normalized not in {"what", "which", "where", "when", "how", "this", "that", "aristotle", "braun", "example", "using", "with"}:
                tags.add(normalized)

    # Extract significant lowercase words (4+ chars)
    words = re.findall(r'\b[a-z]{4,}\b', text)
    stopwords = {
        'what', 'which', 'about', 'from', 'with', 'this', 'that', 'have', 'been',
        'were', 'they', 'their', 'would', 'could', 'should', 'when', 'where',
        'there', 'here', 'about', 'using', 'being', 'after', 'before', 'these',
        'those', 'other', 'another', 'every', 'each', 'still', 'also', 'just',
        'like', 'more', 'most', 'some', 'such', 'only', 'very', 'into', 'over',
        'under', 'again', 'then', 'once', 'your', 'have', 'has', 'had', 'does',
        'doing', 'will', 'would', 'could', 'should', 'might', 'must', 'need',
        'want', 'know', 'think', 'make', 'take', 'come', 'just', 'get', 'got'
    }
    for word in words:
        if word not in stopwords and len(word) > 3:
            tags.add(normalize_tag(word))

    # Extract version numbers as tags (e.g., "python3", "es6")
    versions = re.findall(r'\b(python|es6|es2020|nodejs|postgres|redis|mysql|mongodb)(\d*\.?\d*)\b', text, re.IGNORECASE)
    for base, version in versions:
        if version:
            tags.add(normalize_tag(base + version.replace('.', '')))
        else:
            tags.add(normalize_tag(base))

    # Extract framework/library patterns
    framework_patterns = [
        r'\b(django|flask|fastapi|express|koa|socket\.io|redux|graphql|rxjs|axios)\b',
        r'\b(react|vue|angular|svelte|nextjs|nuxt|remix|gatsby)\b',
        r'\b(tailwind|bootstrap|material-ui|chakra)\b',
        r'\b(sequelize|typeorm|prisma|sqlalchemy)\b',
        r'\b(jwt|oauth|ssl|tls|https?|ssh|ftp|sftp)\b',
        r'\b(docker|kubernetes|helm|terraform|ansible)\b',
        r'\b(git|github|gitlab|bitbucket)\b',
        r'\b(redis|memcached|elasticsearch|s3|dynamodb)\b',
        r'\b(postgres|mysql|mongodb|sqlite|mssql|oracle)\b',
        r'\b(rabbitmq|kafka|zeromq|sqs)\b',
        r'\b(rest|graphql|grpc|websocket|http|websockets)\b',
        r'\b(json|xml|yaml|toml|ini|env)\b',
        r'\b(linux|unix|macos|windows|debian|ubuntu|centos|alpine)\b',
        r'\b(vim|emacs|vscode|jetbrains|pycharm|webstorm)\b',
    ]

    for pattern in framework_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            tags.add(normalize_tag(match if isinstance(match, str) else match[0]))

    # Remove tags that are too generic or too short
    filtered = []
    generic_tags = {
        'example', 'question', 'answer', 'problem', 'issue', 'error', 'bug',
        'fix', 'solution', 'help', 'work', 'working', 'code', 'file', 'line',
        'function', 'method', 'class', 'object', 'variable', 'data', 'type',
        'string', 'number', 'array', 'list', 'dict', 'map', 'set', 'tree',
        'node', 'value', 'key', 'name', 'text', 'word', 'line', 'content',
        'information', 'result', 'output', 'input', 'parameter', 'return',
        'create', 'update', 'delete', 'read', 'write', 'open', 'close',
        'start', 'stop', 'run', 'execute', 'call', 'send', 'receive', 'get', 'set'
    }
    for tag in tags:
        if tag not in generic_tags and len(tag) > 1 and not tag.isdigit():
            filtered.append(tag)

    return sorted(list(set(filtered)))


def tag_entry(qa_entry_id: int, question: str, answer: str):
    """
    Automatically tag a Q&A entry based on its content.
    Called when a new entry is created.
    """
    existing = [t["name"] for t in get_tags_for_entry(qa_entry_id)]
    new_tags = extract_tags_from_content(question, answer, existing)

    # Merge with any existing tags
    all_tags = list(set(existing + new_tags))
    set_tags_for_entry(qa_entry_id, all_tags)

    return new_tags


def cleanup_tags() -> dict:
    """
    Run tag maintenance: remove orphaned tags and merge similar tags.
    Returns a report of actions taken.
    """
    report = {"removed_orphans": 0, "merged": []}

    # Remove tags with no entries
    deleted = delete_unused_tags()
    report["removed_orphans"] = deleted

    # Find and suggest similar tags
    similar = find_similar_tags()

    # Auto-merge obvious duplicates
    for tag1, tag2 in similar:
        # Skip if they share a common prefix but aren't really the same
        if tag1["name"][:4] == tag2["name"][:4]:
            # Merge smaller into larger
            smaller = tag1 if tag1["name"] < tag2["name"] else tag2
            larger = tag2 if smaller == tag1 else tag1
            merge_tags(smaller["id"], larger["id"])
            report["merged"].append(f"{smaller['name']} -> {larger['name']}")

    return report


def get_tag_suggestions(question: str, answer: str, limit: int = 5) -> list[str]:
    """
    Get tag suggestions for content without applying them.
    Useful for preview before tagging.
    """
    return extract_tags_from_content(question, answer)[:limit]
