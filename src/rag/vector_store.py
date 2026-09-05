import chromadb

client = chromadb.PersistentClient(path="./chroma_data")
collection = client.get_or_create_collection("client_context")


async def search_client_context(client_name: str, query: str, top_k: int = 3) -> str:
    """
    Retrieve a client's profile as a single string.

    Returns a joined string, not a list. Callers interpolate this into LLM prompts and
    render it in the UI; a list produced a Python repr with escaped newlines in the
    prompt and unseparated concatenation in React.
    """
    results = collection.query(
        query_texts=[f"{client_name}: {query}"],
        n_results=top_k,
        where={"client_name": client_name},
    )
    documents = results["documents"][0] if results["documents"] else []
    return "\n\n---\n\n".join(documents)


async def search_client_context_with_metadata(client_name: str, query: str, top_k: int = 3) -> dict:
    """
    Same retrieval, but also returns the metadata stored alongside the document.

    Risk level and tier are read from metadata rather than sniffed out of the prose.
    The old code tested `"EXACT MATCH" not in context` against a list, a string that
    appears nowhere in the corpus, so every client was labelled HIGH risk.
    """
    results = collection.query(
        query_texts=[f"{client_name}: {query}"],
        n_results=top_k,
        where={"client_name": client_name},
    )
    documents = results["documents"][0] if results["documents"] else []
    metadatas = results["metadatas"][0] if results.get("metadatas") else []

    return {
        "context": "\n\n---\n\n".join(documents),
        "metadata": metadatas[0] if metadatas else {},
        "matched": bool(documents),
    }
