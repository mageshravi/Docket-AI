import tiktoken
from django.conf import settings
from openai import OpenAI


def create_chunks_for_vector_embedding(text_content: str) -> list:
    """
    Splits the text content into chunks of approximately 8000 tokens.

    Args:
        text_content (str): The text content to be split into chunks.

    Returns:
        list: A list of text chunks.
    """
    chunk_size = 8000

    encoding = tiktoken.encoding_for_model("gpt-4o")
    tokens = encoding.encode(text_content)

    if len(tokens) <= chunk_size:
        return [text_content]

    chunks = []
    # split into chunks of approximately 8000 tokens with some overlap
    for i in range(0, len(tokens), chunk_size):
        chunk = tokens[i : i + chunk_size]

        if i > 0:
            # Add overlap of 100 tokens
            chunk = tokens[i - 100 : i + chunk_size]

        text_chunk = encoding.decode(chunk)
        chunks.append(text_chunk)

    return chunks


def create_vector_embedding(chunks: list) -> list[dict]:
    """
    Creates vector embeddings for the provided text chunks using OpenAI's API.

    Args:
        chunks (list): A list of text chunks to be embedded.

    Raises:
        OpenAIError: If there is an error with the OpenAI API.

    Returns:
        list: A list of dictionaries containing the text and its corresponding embedding.
    """
    openai = OpenAI(api_key=settings.OPENAI_API_KEY)
    embeddings = []

    for chunk in chunks:
        response = openai.embeddings.create(input=chunk, model="text-embedding-3-small")
        embeddings.append({"text": chunk, "embedding": response.data[0].embedding})

    return embeddings
