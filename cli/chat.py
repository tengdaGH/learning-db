"""
CLI Chat interface for the learning system.
"""
import sys
import anthropic
from agents.research_agent import ResearchAgent
from agents.learning_assistant import suggest_related, find_gaps, suggest_next_steps
from db.queries import get_latest_review_summary, get_user_topics


COMMANDS = {
    "/help": "Show this help message",
    "/gaps": "Find gaps in your knowledge base",
    "/suggest": "Get suggestions for related topics",
    "/next": "Get recommended next steps",
    "/digest": "Show last week's learning digest",
    "/topics": "Show topics you've explored",
    "/quit": "Exit the chat",
}


def print_welcome():
    print("=" * 50)
    print("  Personal Learning Assistant")
    print("  Type /help for commands")
    print("=" * 50)
    print()


def print_help():
    print("\n📚 AVAILABLE COMMANDS:")
    for cmd, desc in COMMANDS.items():
        print(f"  {cmd:12} — {desc}")
    print()


def chat_loop():
    """Main interactive chat loop."""
    agent = ResearchAgent()

    print_welcome()

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye! Keep learning!")
            break

        if not question:
            continue

        # Handle commands
        if question.startswith("/"):
            cmd = question.split()[0].lower()
            if cmd == "/quit":
                print("Goodbye! Keep learning! 📚")
                break
            elif cmd == "/help":
                print_help()
            elif cmd == "/gaps":
                print("\n" + find_gaps() + "\n")
            elif cmd == "/suggest":
                print("\n" + suggest_related() + "\n")
            elif cmd == "/next":
                print("\n" + suggest_next_steps() + "\n")
            elif cmd == "/digest":
                digest = get_latest_review_summary()
                if digest:
                    print("\n" + digest["digest"] + "\n")
                else:
                    print("\nNo digest available yet — keep learning!\n")
            elif cmd == "/topics":
                topics = get_user_topics()
                if topics:
                    print("\n📂 Topics you've explored:")
                    for t in topics:
                        lvl = t.get("proficiency_level", 1)
                        bar = "█" * lvl + "░" * (4 - lvl)
                        print(f"  • {t['topic_name']:30} {bar}")
                    print()
                else:
                    print("\nNo topics yet — ask me something!\n")
            else:
                print(f"Unknown command: {cmd}. Type /help for options.")
            continue

        # Answer question
        print()
        answer, was_logged = agent.answer(question)

        # Display answer with formatting
        if was_logged:
            print(f"🤖 {answer}\n")
            print("   [📝 Logged to your learning database]\n")
        else:
            print(f"🤖 {answer}\n")


if __name__ == "__main__":
    chat_loop()
