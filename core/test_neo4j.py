import os
from dotenv import load_dotenv
from neo4j import GraphDatabase, exceptions

def test_neo4j_connection():
    """
    A simple script to test the connection to the Neo4j database
    and create a single node.
    """
    try:
        load_dotenv()
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")

        if not all([uri, user, password]):
            print("Error: Database credentials not found in .env file. Please check the file.")
            return

        driver = GraphDatabase.driver(uri, auth=(user, password))
        print("Attempting to connect to Neo4j...")

        with driver.session() as session:
            session.run("MERGE (n:TestNode {name: 'Hello World'})")

        driver.close()
        print("\n✅ Success! Connected to Neo4j and created a test node.")
        print("You can verify by running 'MATCH (n:TestNode) RETURN n' in the Neo4j Browser.")

    except exceptions.AuthError:
        print("\n❌ Error: Neo4j authentication failed. Please double-check your username and password in the .env file.")
    except exceptions.ServiceUnavailable:
        print("\n❌ Error: Could not connect to Neo4j. Please ensure the database is running and the URI in your .env file is correct.")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    test_neo4j_connection()