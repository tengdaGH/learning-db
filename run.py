#!/usr/bin/env python3
"""
Personal Learning System — Entry Point
"""
import sys
import argparse
import logging

from db.schema import init_schema, migrate_schema
from cli.chat import chat_loop
from services.logging_config import setup_logging

logger = logging.getLogger(__name__)


def main():
    setup_logging()
    
    # Always migrate first to handle schema changes
    migrate_schema()
    logger.info("Database schema migrated")

    parser = argparse.ArgumentParser(description="Personal Learning System")
    parser.add_argument("--init-db", action="store_true", help="Initialize the database schema")
    parser.add_argument("command", nargs="?", choices=["chat", "review"], default="chat",
                        help="Command to run (default: chat)")
    args = parser.parse_args()

    if args.init_db:
        logger.info("Initializing database...")
        init_schema()
        logger.info("Done! Run `python run.py chat` to start learning.")
        return

    if args.command == "chat":
        chat_loop()
    elif args.command == "review":
        from agents.review_agent import run_review
        run_review()


if __name__ == "__main__":
    main()
