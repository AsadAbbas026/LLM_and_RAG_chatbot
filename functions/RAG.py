import os
import time
import shutil
import re
from typing import List, Dict, Any
from datetime import datetime
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma, Pinecone
from langchain.schema import Document
from langchain.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec

class RAGChatbot:
    def __init__(self):
        self.embedding_model = GoogleGenerativeAIEmbeddings(
            api_key=os.getenv("GOOGLE_API_KEY"), model="models/embedding-001"
        )
        self.chroma_db = None
        self.pinecone_instance = None
        self.id_to_text = {}
        self.setup_globals()
        self.chat_model = ChatGoogleGenerativeAI(api_key=os.getenv("GOOGLE_API_KEY"), model="gemini-1.5-flash")
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", "Write a concise summary of the following:\n\n{context}"),
                ("user", "Question: {question}")
            ]
        )

    def ensure_upload_folder_exists(self, upload_folder='uploads'):
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

    def load_latest_pdf(self, upload_folder='uploads'):
        pdf_files = [f for f in os.listdir(upload_folder) if f.endswith('.pdf')]
        if pdf_files:
            pdf_files.sort(key=lambda x: os.path.getmtime(os.path.join(upload_folder, x)), reverse=True)
            latest_pdf = pdf_files[0]
            filename = os.path.join(upload_folder, latest_pdf)
            loader = PyPDFLoader(filename)
            return loader, latest_pdf
        else:
            print("No PDF files found in the UPLOAD_FOLDER.")
            return None, None

    def clean_text(self, text):
        text = re.sub(r'\s+', ' ', text)  # Remove excessive whitespace
        text = re.sub(r'\d+\s*\|\s*Chapter.*', '', text)  # Remove headers/footers
        return text

    def split_text(self, texts):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=100,
            length_function=len,
            add_start_index=True,
        )
        chunks = text_splitter.split_documents([Document(page_content=text) for text in texts])
        return chunks

    def initialize_chroma_db(self, chunks, chroma_path="chroma"):
        if os.path.exists(chroma_path):
            # Skip reinitialization if already initialized
            print(f"ChromaDB at '{chroma_path}' already exists. Skipping reinitialization.")
            return Chroma(persist_directory=chroma_path, embedding_function=self.embedding_model)
        
        # Initialize and persist ChromaDB
        chroma_db = Chroma.from_documents(
            chunks, self.embedding_model, persist_directory=chroma_path
        )
        chroma_db.persist()
        return chroma_db

    def initialize_pinecone(self, api_key, index_name, embeddings, texts, user_name, document_name):
        pc = Pinecone(api_key=api_key)
        indexes = pc.list_indexes()

        if index_name in indexes.names():
            print(f"Pinecone index '{index_name}' already exists. Skipping reinitialization.")
            return pc

        # If the index doesn't exist, create it and upload the embeddings
        print(f"Creating index: {index_name}")
        try:
            pc.create_index(
                name=index_name,
                dimension=768,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1'
                )
            )
            time.sleep(30)  # Give some time for the index to be created
        except Exception as e:
            print(f"Error during index creation: {e}")
        
        vectors = []
        self.id_to_text = {}
        current_datetime = datetime.utcnow().isoformat()
        for i, emb in enumerate(embeddings):
            vector_id = f"vs-{i}"
            metadata = {
                "user_name": user_name,
                "document_name": document_name,
                "datetime": current_datetime
            }
            vectors.append((vector_id, emb, metadata))
            self.id_to_text[vector_id] = texts[i]
        
        try:
            index = pc.Index(index_name)
            index.upsert(vectors=vectors)
            print("Upsert successful.")
        except Exception as e:
            print(f"Error during upsert: {e}")

        return pc

    def setup_globals(self):
        # Load and process the latest PDF
        self.ensure_upload_folder_exists()
        loader, latest_pdf = self.load_latest_pdf()
        if loader:
            pages = loader.load_and_split()
            texts = [self.clean_text(page.page_content) for page in pages]
        else:
            texts = []
            latest_pdf = "N/A"

        # Initialize Chroma database if not already initialized
        chunks = self.split_text(texts)
        self.chroma_db = self.initialize_chroma_db(chunks)

        # Initialize Pinecone only once
        if self.pinecone_instance is None:
            user_name = input("Enter your name: ")
            self.pinecone_instance = self.initialize_pinecone(
                api_key=os.getenv("PINECONE_API_KEY"),
                index_name="my-index",
                embeddings=self.embedding_model.embed_documents(texts),
                texts=texts,
                user_name=user_name,
                document_name=latest_pdf
            )

    def generate_response(self, user_prompt):
        query_embedding = self.embedding_model.embed_query(user_prompt)
        print("Querying Pinecone index...")
        
        pinecone_results = self.pinecone_instance.Index("my-index").query(vector=query_embedding, top_k=5, include_metadata=True)
        best_match_text = None
        best_match_score = 0
        best_match_metadata = {}

        if pinecone_results.matches:
            for match in pinecone_results.matches:
                if match.score > best_match_score:
                    best_match_id = match.id
                    best_match_score = match.score
                    best_match_text = self.id_to_text.get(best_match_id, None)
                    best_match_metadata = match.metadata if match.metadata else {}

        # Threshold for Pinecone
        if not best_match_text or best_match_score < 0.8:
            print("Querying ChromaDB...")
            chroma_results = self.chroma_db.similarity_search_with_relevance_scores(user_prompt, k=5)
            if chroma_results and chroma_results[0][1] >= 0.5:
                best_match_text = chroma_results[0][0].page_content
                best_match_metadata = {}  # Clear metadata since Chroma doesn't provide it
            else:
                best_match_text = None  # Force fallback

        context = best_match_text or "Text not found"
        response = self.format_response(context, user_prompt, best_match_metadata)
        return response

    def format_response(self, context, question, metadata):
        prompt = self.prompt_template.format(context=context, question=question)
        response = self.chat_model.predict(prompt)

        if metadata:
            metadata_info = "\n\nAdditional Information:\n"
            for key, value in metadata.items():
                metadata_info += f"{key.capitalize()}: {value}\n"
            response += metadata_info

        return response

# Usage
# rag_bot = RAGChatbot()
# user_input = "Your question or input here"
# response = rag_bot.generate_response(user_input)
# print(response)
