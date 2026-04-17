import os, sys
from dotenv import load_dotenv

# Load .env from project root (where uvicorn runs)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

uri = os.getenv('MONGO_URI')
print(f"MONGO_URI found: {bool(uri)}")
if uri:
    print(f"URI prefix: {uri[:40]}...")

from pymongo import MongoClient
print("Trying MongoClient with 5s timeout...")
try:
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client['companion_ai']
    result = db.command('ping')
    print(f"MongoDB ping: {result}")
    user = db['users'].find_one({'email': 'shardul@gmail.com'})
    print(f"User found: {bool(user)}")
    if user:
        print(f"User role: {user.get('role')}")
except Exception as e:
    print(f"MongoDB error: {type(e).__name__}: {e}")

