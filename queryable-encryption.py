import os  
from pymongo import MongoClient, errors  
from pymongo.encryption import ClientEncryption  
from pymongo.encryption_options import AutoEncryptionOpts  
from bson import json_util  
from bson.codec_options import CodecOptions  
from bson.binary import STANDARD  
from bson import Binary, UUID_SUBTYPE  
from datetime import datetime  
  
# ---------------------------  
# Configuration Parameters  
# ---------------------------  
  
# Define a hardcoded local master key (96 bytes)  
# In production, securely manage your master key  
local_master_key = bytes.fromhex(  
    "a1b2c3d4e5f60718293a4b5c6d7e8f90" * 6  
)  
  
# KMS Provider Configuration  
kms_providers = {  
    "local": {"key": local_master_key}  
}  
  
# Key Vault Namespace  
key_vault_namespace = "encryption.__keyVault"  
  
# MongoDB Connection String  
connection_string = ""  
  
# Data Encryption Key (DEK) Key Alt Name  
key_alt_name = "csfle_demo_data_key"  
  
# ---------------------------  
# Setup and Initialization  
# ---------------------------  
  
# Create a MongoDB client for the key vault (without encryption)  
key_vault_client = MongoClient(connection_string)  
  
# Access the key vault collection  
key_vault_coll = key_vault_client.get_database(  
    key_vault_namespace.split(".")[0]  
).get_collection(key_vault_namespace.split(".")[1])  
  
# Ensure a unique index on keyAltNames in the key vault collection  
try:  
    key_vault_coll.create_index(  
        "keyAltNames",  
        unique=True,  
        partialFilterExpression={"keyAltNames": {"$exists": True}},  
        name="keyAltNames_1"  
    )  
except errors.OperationFailure as e:  
    if 'already exists' in str(e):  
        pass  # Index already exists; do nothing  
    else:  
        raise  # Re-raise other exceptions  
  
# ---------------------------  
# Data Encryption Key (DEK)  
# ---------------------------  
  
# Check if a DEK with the specified keyAltName already exists  
existing_key = key_vault_coll.find_one({"keyAltNames": key_alt_name})  
  
if existing_key:  
    # Use the existing key  
    data_key_id = existing_key["_id"]  
    print(f"Using existing data key with _id: {data_key_id}")  
else:  
    # Create a new data encryption key (DEK)  
    client_encryption = ClientEncryption(  
        kms_providers,  
        key_vault_namespace,  
        key_vault_client,  
        CodecOptions(uuid_representation=STANDARD),  
    )  
    try:  
        data_key_id = client_encryption.create_data_key(  
            "local", key_alt_names=[key_alt_name]  
        )  
        print(f"Created new data key with _id: {data_key_id}")  
    except errors.DuplicateKeyError:  
        # Retrieve the existing key if another process created it  
        existing_key = key_vault_coll.find_one({"keyAltNames": key_alt_name})  
        if existing_key:  
            data_key_id = existing_key["_id"]  
            print(f"Key was created by another process. Using data key with _id: {data_key_id}")  
        else:  
            raise  # Re-raise exception if key still doesn't exist  
    finally:  
        client_encryption.close()  
  
# ---------------------------  
# Encrypted Fields Map  
# ---------------------------  
  
# Encrypted Fields Map with Queryable Encryption  
encrypted_fields_map = {  
    "csfle_demo.memories": {  
        "escCollection": "enxcol_.memories.esc",  
        "ecocCollection": "enxcol_.memories.ecoc",  
        "fields": [  
            {  
                "path": "email",  
                "bsonType": "string",  
                "keyId": data_key_id,  
                "queries": {"queryType": "equality"},  
            },  
            {  
                "path": "memory",  
                "bsonType": "string",  
                "keyId": data_key_id,  
            },  
            {  
                "path": "preferences",  
                "bsonType": "object",  
                "keyId": data_key_id,  
            },  
            {  
                "path": "password",  
                "bsonType": "string",  
                "keyId": data_key_id,  
            },  
        ]  
    }  
}  
  
# ---------------------------  
# Encrypted MongoDB Client  
# ---------------------------  
  
# Configure auto-encryption  
auto_encryption_opts = AutoEncryptionOpts(  
    kms_providers=kms_providers,  
    key_vault_namespace=key_vault_namespace,  
    encrypted_fields_map=encrypted_fields_map  
)  
  
# Create an encrypted MongoClient  
encrypted_client = MongoClient(  
    connection_string,  
    auto_encryption_opts=auto_encryption_opts  
)  
  
# Access the database and collection  
db = encrypted_client.get_database("csfle_demo")  
collection = db.get_collection("memories")  
  
# ---------------------------  
# Create Encrypted Collection  
# ---------------------------  
  
# Create the encrypted collection if it doesn't exist  
try:  
    db.create_collection(  
        "memories",  
        encrypted_fields=encrypted_fields_map["csfle_demo.memories"]  
    )  
    print("Encrypted collection 'memories' created.")  
except errors.CollectionInvalid:  
    # Collection already exists  
    print("Encrypted collection 'memories' already exists.")  
  
# ---------------------------  
# Insert Sample Data  
# ---------------------------  
  
# Sample memory data  
memory_document = {  
    "email": "user@example.com",  
    "memory": "Today I chatted with the assistant about Queryable Encryption.",  
    "preferences": {  
        "theme": "dark",  
        "notifications": True  
    },  
    "password": "super_secret_password",  
    "timestamp": datetime.utcnow()  
}  
  
# Insert the memory document  
try:  
    result = collection.insert_one(memory_document)  
    print(f"Inserted memory document with _id: {result.inserted_id}")  
except errors.DuplicateKeyError:  
    print("Memory document already exists.")  
  
# ---------------------------  
# Retrieve and Display Data  
# ---------------------------  
  
# Retrieve the memory document  
retrieved_doc = collection.find_one({"email": "user@example.com"})  
  
print("\nRetrieved Memory Document (Decrypted):")  
print(json_util.dumps(retrieved_doc, indent=2))  
  
# The 'email', 'memory', 'preferences', and 'password' fields are automatically decrypted  
  
# ---------------------------  
# Query on Encrypted Field  
# ---------------------------  
  
# Attempt to find the document using an encrypted field (email)  
query = {"email": "user@example.com"}  
queried_doc = collection.find_one(query)  
  
print("\nQueried Document by Encrypted Field (Decrypted):")  
print(json_util.dumps(queried_doc, indent=2))  
  
# ---------------------------  
# Close Clients  
# ---------------------------  
  
encrypted_client.close()  
key_vault_client.close()  
