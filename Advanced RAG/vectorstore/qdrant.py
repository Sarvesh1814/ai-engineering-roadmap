from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
)
import traceback




class QdrantVectorStore:

    def __init__(
        self,
        host,
        port,
        collection_name,
        vector_size,
    ):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.client = None

    def connect(self):

        try:

            self.client = QdrantClient(
                host=self.host,
                port=self.port
            )

            self.client.get_collections()

            print("[+] Connected to Qdrant")

        except Exception as e:

            print("[-] Failed to connect")
            print(e)
            traceback.print_exc()
            raise

    def create_collection(self):

        collections = [
            c.name
            for c in self.client.get_collections().collections
        ]

        if self.collection_name not in collections:

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )

            print("[+] Collection created")

        else:

            print("[+] Collection already exists")