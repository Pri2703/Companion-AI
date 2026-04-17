from backend.database.mongo import users_collection, relation_collection

users_collection.delete_many({})
relation_collection.delete_many({})

users_collection.insert_many([
    {"user_id": "user_1", "email": "user@gmail.com", "password": "password123", "role": "blind"},
    {"user_id": "caretaker_1", "email": "caretaker@gmail.com", "password": "password123", "role": "caretaker"}
])

relation_collection.insert_one({
    "caretaker_id": "caretaker_1",
    "linked_users": ["user_1"]
})

print("Database successfully seeded with demo users!")
