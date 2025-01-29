from pymongo import MongoClient  
from pymongo.encryption import ClientEncryption, Algorithm  
from pymongo.encryption_options import AutoEncryptionOpts  
from bson.codec_options import CodecOptions  
from bson.binary import STANDARD  
import os  
  
# Connection string to your MongoDB instance  
connection_string = ""  
  
# Namespace for the key vault (database and collection)  
key_vault_namespace = "encryption.__keyVault"  
  
# Generate a 96-byte local master key (must be kept secure in production)  
local_master_key = os.urandom(96)  
  
# Define KMS providers  
kms_providers = {  
    "local": {  
        "key": local_master_key  
    }  
}  
  
# Create a MongoClient without encryption options  
client = MongoClient(connection_string)  
  
# Get references to the key vault collection  
key_vault_db, key_vault_coll = key_vault_namespace.split(".", 1)  
key_vault = client[key_vault_db][key_vault_coll]  
  
# Ensure the key vault collection has a unique index on keyAltNames  
key_vault.create_index(  
    "keyAltNames",  
    unique=True,  
    partialFilterExpression={"keyAltNames": {"$exists": True}}  
)  
  
# Import CodecOptions and set UUID representation to STANDARD  
codec_options = CodecOptions(uuid_representation=STANDARD)  
  
# Create a ClientEncryption instance  
client_encryption = ClientEncryption(  
    kms_providers=kms_providers,  
    key_vault_namespace=key_vault_namespace,  
    key_vault_client=client,  
    codec_options=codec_options  
)  
  
# Check if a DEK with the keyAltName "memories-data-key" already exists  
dek_alt_name = "memories-data-key"  
existing_dek = key_vault.find_one({"keyAltNames": dek_alt_name})  
  
if existing_dek:  
    # Use the existing DEK  
    data_key_id = existing_dek["_id"]  
    print(f"Using existing data key with ID: {data_key_id}")  
else:  
    # Create a new DEK  
    data_key_id = client_encryption.create_data_key(  
        "local",  
        key_alt_names=[dek_alt_name]  
    )  
    print(f"Created new data key with ID: {data_key_id}")  
  
# Define the encrypted fields map  
encrypted_fields_map = {  
    "users.memories": {  
        "fields": [  
            {  
                "keyId": data_key_id,  
                "path": "memory",  
                "bsonType": "string",  
                "queries": {"queryType": "equality"}  
            }  
        ]  
    }  
}  
  
# Set up automatic encryption options  
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
  
# Get a reference to the encrypted collection  
db = encrypted_client["users"]  
collection = db["memories"]  
  
# Drop the collection if it exists (for demonstration purposes)  
collection.drop()  
  
# Sample document to insert  
document = {  
    "email": "user@example.com",  
    "memory": "I remember visiting the Grand Canyon last summer.",  
    "timestamp": "2023-10-01T12:00:00Z"  
}  
  
# Insert the document  
insert_result = collection.insert_one(document)  
print(f"Inserted document with ID: {insert_result.inserted_id}")  
  
# Retrieve the document  
retrieved_doc = collection.find_one({"email": "user@example.com"})  
print("Retrieved document:")  
print(retrieved_doc)  
  
# Create an unencrypted client  
unencrypted_client = MongoClient(connection_string)  
  
# Access the collection without encryption  
unencrypted_collection = unencrypted_client["users"]["memories"]  
  
# Retrieve the raw document  
raw_doc = unencrypted_collection.find_one({"email": "user@example.com"})  
print("Raw document retrieved without decryption:")  
print(raw_doc)  
  
# Close the clients  
encrypted_client.close()  
client_encryption.close()  
client.close()  
unencrypted_client.close()  
