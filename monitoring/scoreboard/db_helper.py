import pymongo


class DBHelper:
    def __init__(self, config):
        self._mongo_client = pymongo.MongoClient(config.db_uri())
        self._db = self._mongo_client.scoreboard

    def get(self):
        return self._db
