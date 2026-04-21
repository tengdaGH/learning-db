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


def extract_tags_from_content(question: str, answer: str) -> list[str]:
    """
    Extract meaningful tags from question and answer content.
    Returns a list of normalized tag names.
    """
    text = question + " " + answer
    tags = set()

    # Extract framework/library/tech patterns (case-insensitive)
    tech_patterns = [
        r'\b(python|java|javascript|typescript|rust|go|golang|ruby|php|swift|kotlin|cpp|csharp|perl|scala|kotlin)\b',
        r'\b(django|flask|fastapi|express|koa|socket\.?io|redux|graphql|rxjs|axios|rails|sinatra|play|bottle)\b',
        r'\b(react|vue|angular|svelte|nextjs|nuxt|remix|gatsby|ember|backbone|lit|alpine)\b',
        r'\b(tailwind|bootstrap|material-ui|chakra|bulma|foundation|styled-components|emotion)\b',
        r'\b(sequelize|typeorm|prisma|sqlalchemy|hibernate|jpa|entity|drizzle)\b',
        r'\b(jwt|oauth|oauth2|ssl|tls|https?|ssh|ftp|sftp|cors|csrf|xss|same-origin)\b',
        r'\b(docker|docker-compose|kubernetes|k8s|helm|terraform|ansible|puppet|chef|vagrant)\b',
        r'\b(git|github|gitlab|bitbucket|sourcetree|github-actions|cicd|jenkins|travis|circleci)\b',
        r'\b(redis|memcached|elasticsearch|s3|dynamodb|cassandra|mongodb|postgresql|mysql|sqlite|mssql|oracle|sql)\b',
        r'\b(rabbitmq|kafka|zeromq|sqs|activemq|pulsar)\b',
        r'\b(rest|restful|graphql|grpc|websocket|http|http2|websockets|soap|xmlrpc|jsonrpc)\b',
        r'\b(json|xml|yaml|toml|ini|env|protobuf|avro|thrift|html|css|scss|sass|less)\b',
        r'\b(linux|unix|macos|windows|debian|ubuntu|centos|alpine|redhat|fedora|arch|freebsd)\b',
        r'\b(vim|emacs|vscode|jetbrains|pycharm|webstorm|intellij|sublime|atom|notepad\+\+)\b',
        r'\b(aws|azure|gcp|google-cloud|heroku|netlify|vercel|cloudflare|digitalocean|linode)\b',
        r'\b(tcp|udp|ip|dns|dhcp|ntp|bgp|ospf|vpn|tunnel|proxy|load-?balancer|cdn)\b',
        r'\b(api|cli|gui|sdk|ide|debug|profiler|linter|formatter|bundler|package-manager)\b',
        r'\b(orm|odm|mvc|mvvm|microservice|monolith|serverless|faas|paas|iaas|saas|baas)\b',
        r'\b(oop|functional|procedural|imperative|declarative|reactive|lazy|eager|concurrency|parallelism)\b',
        r'\b(algorithm|datastructure|array|list|map|dictionary|set|tree|graph|heap|stack|queue|hash|linked-list)\b',
        r'\b(agile|scrum|kanban|waterfall|devops|sre|platform-engineering|ci/cd|test-driven)\b',
        r'\b(testing|tdd|bdd|unittest|pytest|jest|mocha|cypress|selenium|e2e|integration-test|unit-test)\b',
        r'\b(typescript|javascript|node|nodejs|npm|yarn|pnpm|bun|deno)\b',
        r'\b(react|vue|angular|preact|mithril|alpine|petite-vue|qwik|solid)\b',
        r'\b(postgres|mysql|mariadb|sqlite|mssql|oracle|redis|memcached|mongodb|couchdb|neo4j|graph db)\b',
        r'\b(socket|websocket|server-sent-events|sse|webhook|webtransport|quic)\b',
        r'\b(auth|authentication|authorization|permission|role|encryption|hash|bcrypt|argon)\b',
        r'\b(cache|caching|invalidation|cdn|edge|cdn)\b',
        r'\b(container|containerization|orchestration|service-mesh|sidecar|init-container)\b',
        r'\b(linux|bash|shell|script|automation|cron|systemd|init)\b',
        r'\b(python|flask|django|fastapi|pyramid|bottle|tornado|sanic)\b',
        r'\b(git|branch|merge|rebase|cherry-pick|stash|workflow|pull-request|code-review)\b',
    ]

    for pattern in tech_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            tags.add(normalize_tag(match if isinstance(match, str) else match[0]))

    # Extract version numbers as tags (e.g., "python3", "es6", "node14")
    versions = re.findall(r'\b(python|es6|es2020|nodejs|node|postgres|postgresql|redis|mysql|mongodb|react|vue|angular)(\d*)', text, re.IGNORECASE)
    for base, version in versions:
        tag = normalize_tag(base)
        if version:
            tag = normalize_tag(base + version.replace('.', ''))
        tags.add(tag)

    # Filter out any generic words that slipped through
    generic_words = {
        'what', 'which', 'where', 'when', 'how', 'this', 'that', 'these', 'those',
        'would', 'could', 'should', 'might', 'must', 'need', 'want', 'know', 'think',
        'make', 'take', 'come', 'just', 'get', 'got', 'let', 'you', 'your',
        'have', 'has', 'had', 'does', 'doing', 'done', 'been', 'being',
        'from', 'with', 'about', 'into', 'over', 'under', 'again', 'then', 'once',
        'here', 'there', 'why', 'who', 'whom', 'whose',
        'simple', 'great', 'easy', 'hard', 'difficult', 'best', 'better', 'good', 'bad',
        'new', 'old', 'first', 'last', 'long', 'short', 'big', 'small', 'large', 'tiny',
        'use', 'using', 'used', 'useful', 'useless', 'help', 'helpful',
        'example', 'question', 'answer', 'problem', 'issue', 'error', 'bug', 'fix',
        'work', 'working', 'works', 'did', 'does', 'done', 'thing', 'things',
        'stuff', 'matter', 'part', 'piece', 'bit', 'kind', 'sort', 'type',
        'way', 'ways', 'case', 'point', 'fact', 'idea', 'reason',
        'real', 'really', 'actually', 'basically', 'essentially', 'simply',
        'understand', 'know', 'learn', 'learned', 'learning', 'teach', 'taught',
        'people', 'person', 'man', 'woman', 'child', 'company', 'team', 'group',
        'like', 'unlike', 'similar', 'different', 'same', 'equal',
        'run', 'running', 'runs', 'start', 'stop', 'starts', 'stops', 'starting',
        'write', 'writing', 'written', 'reads', 'reading', 'read',
        'look', 'looking', 'looks', 'saw', 'seen', 'see', 'show', 'showing', 'shows',
        'name', 'named', 'call', 'called', 'telling', 'told', 'say', 'said', 'says',
        'explain', 'explains', 'explained', 'explanation',
        # Generic tech terms that are too ambiguous
        'go', 'set', 'list', 'tree', 'map', 'less', 'stack', 'queue', 'heap',
        'node', 'edge', 'link', 'path', 'state', 'prop', 'props', 'hook', 'hooks',
        'service', 'client', 'server', 'request', 'response', 'header', 'body',
        'method', 'class', 'function', 'object', 'array', 'key', 'value',
        'string', 'number', 'boolean', 'integer', 'float', 'double', 'array',
        'file', 'folder', 'directory', 'path', 'route', 'url', 'uri',
        'user', 'users', 'admin', 'role', 'permission', 'auth', 'token',
        'cache', 'caching', 'memory', 'storage', 'disk', 'file', 'stream',
        'event', 'message', 'data', 'struct', 'record', 'row', 'column',
        'config', 'setting', 'option', 'mode', 'level', 'mode',
        'simple', 'basic', 'core', 'main', 'primary', 'secondary',
        'general', 'common', 'standard', 'default', 'custom', 'special',
        'real', 'virtual', 'local', 'remote', 'global', 'public', 'private',
    }
    tags = {t for t in tags if t not in generic_words and len(t) > 2 and not t.isdigit()}

    return list(tags)


def tag_entry(qa_entry_id: int, question: str, answer: str):
    """
    Automatically tag a Q&A entry based on its content.
    Called when a new entry is created.
    """
    tags = extract_tags_from_content(question, answer)
    set_tags_for_entry(qa_entry_id, tags)
    return tags


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
