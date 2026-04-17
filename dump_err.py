import os
import traceback
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
uri = os.getenv('MONGO_URI')

try:
    client = MongoClient(uri, serverSelectionTimeoutMS=2000, tlsAllowInvalidCertificates=True)
    client.admin.command('ping')
    with open('err_out.txt', 'w', encoding='utf-8') as f:
        f.write('Success!\n')
except Exception as e:
    with open('err_out.txt', 'w', encoding='utf-8') as f:
        f.write(traceback.format_exc())
