import chromadb

client = chromadb.PersistentClient(path="./chroma_data")
collection = client.get_or_create_collection("client_context")

async def search_client_context(client_name: str, query: str, top_k: int = 3) -> list[str]:
    results = collection.query(
        query_texts=[f"{client_name}: {query}"],
        n_results=top_k,
        where={"client_name": client_name}
    )
    return results["documents"][0] if results["documents"] else []
