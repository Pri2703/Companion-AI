import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)

db = client["companion_ai"]

logs_collection = db["logs"]
status_collection = db["status"]
location_collection = db["location"]
users_collection = db["users"]
relation_collection = db["relations"]