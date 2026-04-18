"""
Review Agent — weekly review of learning database.
"""
from services.digest_generator import generate_weekly_digest
from agents.research_agent import ResearchAgent


def run_review():
    """Run the weekly review process."""
    print("🔍 Running weekly review...")

    # Check for stale content
    agent = ResearchAgent()
    flagged = agent.check_and_flag_stale_entries()
    print(f"  Flagged {len(flagged)} stale entries")

    # Generate digest
    digest = generate_weekly_digest()
    print("\n" + digest)

    return digest


if __name__ == "__main__":
    run_review()
