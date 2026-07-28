from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INGESTION_DIR = Path(__file__).resolve().parent

for path in [PROJECT_ROOT, INGESTION_DIR]:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from mysql_loader import load_view, VIEW_NAME
from preprocessing import TicketCleaner
from config.llm import get_llm


def run_ingestion():
    """
    This function runs the ingestion process by loading data from a MySQL view in chunks.
    Each chunk is processed and can be ingested into a vector database or any other storage.
    """
    llm = get_llm()
    ticket_cleaner = TicketCleaner(llm)

    for chunk_no, df in enumerate(load_view(VIEW_NAME), start=1):
        print(f"Processing chunk {chunk_no}")
        




if __name__ == "__main__":
    run_ingestion()