# Insert embeddings and metadata into the vec0 table
import os
import sqlite3
from struct import pack

import sqlite_vec
from google import genai
from loguru import logger

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    msg = "GOOGLE_API_KEY environment variable not set."
    raise ValueError(msg)

client = genai.Client(api_key=GOOGLE_API_KEY)


# Helper function to serialize embeddings for sqlite-vec
def serialize_float32(vector):
    """Serializes a list of floats into the 'raw bytes' format sqlite-vec expects."""
    return pack(f"{len(vector)}f", *vector)


def get_embeddings(text):
    response = client.models.embed_content(model="gemini-embedding-001", contents=text)
    return response.embeddings[0].values


# Connect and load sqlite-vec extension
conn = sqlite3.connect("posts.db", timeout=5.0)
conn.enable_load_extension(True)
sqlite_vec.load(conn)
conn.enable_load_extension(False)

cur = conn.cursor()

# Create vec0 virtual table with auxiliary columns
# Auxiliary columns (+): Unindexed, SELECT-only columns for storing metadata
query = """
DROP TABLE IF EXISTS posts;

CREATE VIRTUAL TABLE posts USING vec0(
    id INTEGER PRIMARY KEY,
    embedding float[3072],

    -- Auxiliary columns (unindexed, for display only)
    +title TEXT,
    +content TEXT,
    +url TEXT,
    +tokens INTEGER
);
"""

cur.executescript(query)
conn.commit()

logger.info("✓ Database and vec0 table created successfully")


def main() -> None:

    # # Load the data from CSV

    # df_embeddings = pd.read_csv("blog_data_and_embeddings.csv")

    # # Insert each row into the vec0 table
    # for idx, row in df_embeddings.iterrows():
    #     # Parse embeddings from string to list if needed
    #     embedding = row["embeddings"]
    #     if isinstance(embedding, str):
    #         embedding = ast.literal_eval(embedding)

    #     # Serialize embedding to bytes
    #     embedding_bytes = serialize_float32(embedding)

    #     # Insert into vec0 table with metadata and auxiliary columns
    #     cur.execute(
    #         """
    #         INSERT INTO posts(embedding, tokens, title, content, url)
    #         VALUES (?, ?, ?, ?, ?)
    #         """,
    #         (embedding_bytes, row["tokens"], row["title"], row["content"], row["url"]),
    #     )

    # conn.commit()
    # logger.info(f"✓ Inserted {len(df_embeddings)} posts with embeddings into database")

    # Search function for similar embeddings
    def search_similar(query_text, top_k=5):
        """Search for similar embeddings.

        Args:
            query_text: The text to search for
            top_k: Number of results to return

        """
        # Get embedding for query
        query_embedding = get_embeddings(query_text)
        query_bytes = serialize_float32(query_embedding)

        # Search for similar vectors
        return cur.execute(
            """
            SELECT
                id,
                title,
                content,
                url,
                tokens,
                distance
            FROM posts
            WHERE embedding MATCH ?
            AND k = ?
            ORDER BY distance
            """,
            (query_bytes, top_k),
        ).fetchall()

    # Test search example
    results = search_similar("how tolmstudio build an weather station", top_k=5)

    # Display results:
    for _post_id, _title, _content, _url, _tokens, _distance in results:
        pass


if __name__ == "__main__":
    main()
