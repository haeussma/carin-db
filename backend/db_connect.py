from typing import Any

from neo4j import GraphDatabase
from pydantic import BaseModel


class Database(BaseModel):
    uri: str
    user: str
    password: str
    driver: Any = None

    def __init__(self, **data):
        super().__init__(**data)
        self.driver = self.connect()

    def connect(self):
        return GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        if self.driver:
            self.driver.close()
