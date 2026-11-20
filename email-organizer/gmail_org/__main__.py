"""python -m gmail_org <command> ...  (dispatches to the submodules)"""
import importlib
import sys

COMMANDS = {
    "classify": "classify", "inventory": "inventory", "review-page": "review_page",
    "filters": "filters_xml", "unsubscribe": "unsubscribe", "undo-log": "undo_log", "jobs": "jobs",
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("usage: python -m gmail_org {" + ",".join(COMMANDS) + "} ...")
        sys.exit(2)
    mod = importlib.import_module(f"gmail_org.{COMMANDS[sys.argv[1]]}")
    mod.main(sys.argv[2:])
