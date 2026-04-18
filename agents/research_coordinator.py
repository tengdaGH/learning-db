"""
Research Coordinator — orchestrates parallel research agents for deep investigation.
Decomposes complex questions into sub-questions, researches each, synthesizes results.
"""
import time
from typing import List, Dict, Any
from db.queries import (
    add_qa_entry,
    update_user_knowledge,
    get_user_topics,
    get_or_create_topic,
)
from services.auto_log import should_log, estimate_confidence
from services.topic_detector import extract_primary_topic, extract_tags

import os

# Tavily API keys from environment
def _get_tavily_keys():
    """Get Tavily API keys from environment variables."""
    keys = []
    key1 = os.environ.get('TAVILY_API_KEY_1')
    key2 = os.environ.get('TAVILY_API_KEY_2')
    if key1:
        keys.append(key1)
    if key2:
        keys.append(key2)
    return keys if keys else None


def _get_tavily_client():
    """Try each key until one works."""
    from tavily import TavilyClient
    keys = _get_tavily_keys()
    if not keys:
        return None
    for key in keys:
        try:
            client = TavilyClient(api_key=key)
            client.search("test", max_results=1)
            return client
        except Exception:
            continue
    return None


def _call_llm(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    """Call MiniMax via Anthropic-compatible SDK (routes to MiniMax internally)."""
    import anthropic

    client = anthropic.Anthropic()

    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                system=system,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            for block in response.content:
                if block.type == "text" and getattr(block, "text", None):
                    return block.text
            for block in response.content:
                if block.type == "thinking" and getattr(block, "thinking", None):
                    return block.thinking[:500]
            return "[No response content]"
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            return f"[Error: {e}]"


class ResearchCoordinator:
    def __init__(self):
        self.user_topics = get_user_topics()
        self._tavily = None

    @property
    def tavily(self):
        if self._tavily is None:
            self._tavily = _get_tavily_client()
        return self._tavily

    def deep_research(self, question: str) -> tuple[str, bool, List[str]]:
        """
        Returns (answer, was_logged, sources).
        Decomposes question into sub-questions and spawns parallel research.
        """
        log, _ = should_log(question)

        # Decompose the question
        sub_questions = self._decompose_question(question)

        # Run research on each sub-question
        sub_results = []
        for sq in sub_questions:
            result = self._research_sub_question(sq)
            sub_results.append(result)

        # Synthesize results
        synthesis = self._synthesize_results(question, sub_results)
        sources = self._collect_all_sources(sub_results)

        # Log if appropriate
        was_logged = False
        if log and synthesis:
            confidence = estimate_confidence(synthesis)
            topic_name, _ = extract_primary_topic(question, synthesis, self.user_topics)
            tags = extract_tags(question, synthesis)
            topic_id = get_or_create_topic(topic_name)

            add_qa_entry(
                question=question,
                answer=synthesis,
                topic_name=topic_name,
                topic_id=topic_id,
                tags=tags,
                confidence_level=confidence,
                sources=",".join(sources),
            )
            update_user_knowledge(topic_name, proficiency=min(confidence, 4))
            self.user_topics = get_user_topics()
            was_logged = True

        return synthesis, was_logged, sources

    def deep_research_stream(self, question: str):
        """
        Streaming version that yields (event_type, data) tuples for SSE.
        event_type can be: 'tool', 'answer', 'done'
        """
        log, _ = should_log(question)

        # Decompose the question
        yield ('tool', {'type': 'thinking', 'message': 'Analyzing your question...'})
        sub_questions = self._decompose_question(question)
        yield ('tool', {'type': 'thinking', 'message': f'Decomposed into {len(sub_questions)} research areas'})

        # Run research on each sub-question
        sub_results = []
        for i, sq in enumerate(sub_questions, 1):
            yield ('tool', {'type': 'agent', 'message': f'Researching area {i}/{len(sub_questions)}: {sq[:60]}...' if len(sq) > 60 else sq})
            result = self._research_sub_question(sq)
            sub_results.append(result)

        # Synthesize results
        yield ('tool', {'type': 'synthesize', 'message': 'Synthesizing findings into comprehensive answer...'})
        synthesis = self._synthesize_results(question, sub_results)
        sources = self._collect_all_sources(sub_results)

        # Log if appropriate
        was_logged = False
        if log and synthesis:
            try:
                confidence = estimate_confidence(synthesis)
                topic_name, _ = extract_primary_topic(question, synthesis, self.user_topics)
                tags = extract_tags(question, synthesis)
                topic_id = get_or_create_topic(topic_name)

                add_qa_entry(
                    question=question,
                    answer=synthesis,
                    topic_name=topic_name,
                    topic_id=topic_id,
                    tags=tags,
                    confidence_level=confidence,
                    sources=",".join(sources),
                )
                update_user_knowledge(topic_name, proficiency=min(confidence, 4))
                self.user_topics = get_user_topics()
                was_logged = True
            except Exception as e:
                print(f"Error logging to DB: {e}")

        yield ('tool', {'type': 'complete', 'message': 'Research complete'})
        yield ('done', {'was_logged': was_logged, 'sources': sources, 'answer': synthesis})

    def _decompose_question(self, question: str) -> List[str]:
        """Use LLM to decompose a complex question into sub-questions."""
        system = """You are a research coordinator. Your job is to decompose complex questions into 3-5 focused sub-questions that together will provide comprehensive coverage of the topic.

Output format: Just list the sub-questions, one per line. Each should be a self-contained, researchable question. Maximum 5 sub-questions.

Example:
Input: "What is the difference between React and Vue for building web apps?"
Output:
1. What are the core architectural differences between React and Vue?
2. How do React and Vue compare in performance and bundle size?
3. What are the main differences in developer experience and learning curve?
4. How do React and Vue compare in ecosystem and community support?
5. What are the pros and cons of each for different project types?"""

        response = _call_llm(question, system=system, max_tokens=500)

        # Parse sub-questions from response
        lines = response.strip().split('\n')
        sub_questions = []
        for line in lines:
            line = line.strip()
            for prefix in ['1.', '2.', '3.', '4.', '5.', '1:', '2:', '3:', '4:', '5:', '- ']:
                if line.startswith(prefix):
                    sub_questions.append(line[len(prefix):].strip())
                    break

        if not sub_questions:
            sub_questions = [question]

        return sub_questions[:5]

    def _research_sub_question(self, sub_question: str) -> Dict[str, Any]:
        """Research a single sub-question using Tavily and LLM."""
        web_results = []
        if self.tavily:
            try:
                results = self.tavily.search(query=sub_question, max_results=5)
                web_results = results.get("results", [])
            except Exception:
                pass

        extra_context = self._build_web_context(web_results) if web_results else ""

        user_context = self._build_user_context()
        system = f"""You are a research specialist. Answer the sub-question thoroughly using the web search context provided.

USER CONTEXT:
{user_context}

SUB-QUESTION: {sub_question}

{extra_context}

Provide a thorough, factual answer that could be used as part of a comprehensive report. Be specific and include details."""

        answer = _call_llm(sub_question, system=system, max_tokens=800)

        return {
            'question': sub_question,
            'answer': answer,
            'web_results': web_results,
            'sources': [r.get('url', '') for r in web_results if r.get('url')]
        }

    def _synthesize_results(self, original_question: str, sub_results: List[Dict]) -> str:
        """Synthesize all sub-results into a comprehensive answer."""
        user_context = self._build_user_context()

        sub_answers_text = "\n\n".join([
            f"SUB-QUESTION {i+1}: {r['question']}\n\nANSWER:\n{r['answer']}"
            for i, r in enumerate(sub_results)
        ])

        system = f"""You are a research synthesizer. Based on the sub-research results below, provide a comprehensive, well-structured answer to the original question.

ORIGINAL QUESTION: {original_question}

USER CONTEXT:
{user_context}

SUB-RESEARCH RESULTS:
{sub_answers_text}

INSTRUCTIONS:
1. Synthesize the findings into a cohesive, comprehensive answer
2. Organize with clear markdown headers (## for main sections)
3. Include specific details, examples, and data points from the research
4. Note any disagreements or nuances between sources
5. Use markdown formatting (lists, bold, code blocks) for readability
6. Keep it thorough but focused on answering the original question
7. Add [1], [2], etc. citations after key facts that come from specific sources
8. End with a Sources section listing all referenced URLs with their numbers"""

        synthesis = _call_llm(original_question, system=system, max_tokens=2000)
        return synthesis

    def _collect_all_sources(self, sub_results: List[Dict]) -> List[str]:
        """Collect all unique source URLs."""
        sources = []
        seen = set()
        for result in sub_results:
            for url in result.get('sources', []):
                if url and url not in seen:
                    seen.add(url)
                    sources.append(url)
        return sources

    def _build_web_context(self, results: list) -> str:
        """Build a web search context string from Tavily results."""
        if not results:
            return ""
        lines = ["\n\nWEB SEARCH RESULTS:"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            url = r.get("url", "")
            snippet = r.get("content", "")[:300]
            lines.append(f"[{i}] {title} — {url}")
            lines.append(f"    {snippet}")
        return "\n".join(lines)

    def _build_user_context(self) -> str:
        if not self.user_topics:
            return "They haven't learned any topics yet — this appears to be a new area."

        lines = ["They have explored these topics:"]
        for t in self.user_topics[:10]:
            lvl = t.get("proficiency_level", 1)
            lvl_words = {1: "just heard of it", 2: "understands basics", 3: "can apply it", 4: "can teach it"}
            lines.append(f"  - {t['topic_name']}: {lvl_words.get(lvl, 'unknown')}")
        return "\n".join(lines)
