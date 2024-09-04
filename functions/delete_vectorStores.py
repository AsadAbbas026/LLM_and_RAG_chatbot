import shutil
import os
from pinecone import Pinecone, ServerlessSpec

def delete_chroma_db(directory='chroma'):
    if os.path.exists(directory):
        shutil.rmtree(directory)
        print(f"ChromaDB at '{directory}' deleted successfully.")
    else:
        print(f"ChromaDB at '{directory}' does not exist.")

def delete_pinecone_index(index_name='my-index'):
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    # Check if the index exists and delete it
    if index_name in pc.list_indexes().names():
        pc.delete_index(index_name)
        print(f"Pinecone index '{index_name}' deleted successfully.")
    else:
        print(f"Pinecone index '{index_name}' does not exist.")

