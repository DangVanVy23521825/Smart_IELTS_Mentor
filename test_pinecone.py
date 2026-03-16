from pinecone import Pinecone
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load .env từ thư mục gốc project
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

query = "Task response band 7 criteria"

emb = client.embeddings.create(
    model=os.getenv("OPENAI_EMBEDDING_MODEL"),
    input=query
).data[0].embedding

res = index.query(
    vector=emb,
    top_k=5,
    include_metadata=True,
    namespace=os.getenv("PINECONE_NAMESPACE"),
)

for m in res.matches:
    print(m.metadata["criterion"], m.metadata["band"])
    print(m.metadata["text"][:200])
    print("----")