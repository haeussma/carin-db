from backend.db.db_connect import Database

db = Database(uri="bolt://localhost:7692", user="neo4j", password="12345678")


print(db.get_db_structure)
