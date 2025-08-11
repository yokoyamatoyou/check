from typing import List, Dict
from .chunk_processor import ChunkProcessor
from ..parsers.doc_parser import DocumentParser

class MainProcessor:
    def __init__(self):
        self.document_parser = DocumentParser()
        self.chunk_processor = ChunkProcessor()

    def process(self, file_path: str, metadata: Dict) -> List[Dict]:
        parsed_data = self.document_parser.parse(file_path)
        all_chunks = []
        for item in parsed_data:
            chunks = self.chunk_processor.process_chunks(item['content'], metadata)
            all_chunks.extend(chunks)
        return all_chunks
