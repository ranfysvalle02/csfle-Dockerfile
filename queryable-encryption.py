import os  
from pymongo import MongoClient, errors  
from pymongo.encryption_options import AutoEncryptionOpts  
from pymongo.encryption import ClientEncryption  
from bson.codec_options import CodecOptions  
from bson.binary import STANDARD  
from bson import json_util  
  
# Configuration Parameters  
  
# 1. Local Master Key (96 bytes). For testing only. In production, use a secure KMS provider.  
local_master_key = b'\x00' * 96  # Using zeros for simplicity; do not use in production.  
  
# 2. KMS Providers Configuration  
kms_providers = {  
    "local": {  
        "key": local_master_key  
    }  
}  
  
# 3. Key Vault Namespace: Database and Collection to store the DEK  
key_vault_namespace = "encryption.__keyVault"  
  
# 4. MongoDB Connection String  
connection_string = ""  
  
# Create a regular (non-encrypted) MongoClient  
regular_client = MongoClient(connection_string)  
  
# Create the Key Vault (if it doesn't exist)  
key_vault_db, key_vault_coll = key_vault_namespace.split(".")  
key_vault = regular_client[key_vault_db][key_vault_coll]  
  
# Ensure a unique index on keyAltNames to prevent duplicate DEKs  
key_vault.create_index(  
    "keyAltNames",  
    unique=True,  
    partialFilterExpression={"keyAltNames": {"$exists": True}}  
)  
  
# Data Encryption Key (DEK) Setup  
  
# Check if a DEK with the specified key_alt_names exists  
key_alt_name = "demo-data-key"  
existing_key = key_vault.find_one({"keyAltNames": key_alt_name})  
  
if existing_key:  
    data_key_id = existing_key["_id"]  
    print("Using existing Data Encryption Key.")  
else:  
    # Create a new DEK  
    client_encryption = ClientEncryption(  
        kms_providers,  
        key_vault_namespace,  
        regular_client,  
        CodecOptions(uuid_representation=STANDARD),  
    )  
    data_key_id = client_encryption.create_data_key(  
        "local", key_alt_names=[key_alt_name]  # Corrected parameter name  
    )  
    client_encryption.close()  
    print("Created new Data Encryption Key.")  
  
# Encrypted Fields Map Configuration  
# Specify the field to encrypt and enable queryable encryption  
encrypted_fields_map = {  
    "test.coll": {  
        "fields": [  
            {  
                "path": "secretField",  
                "bsonType": "string",  
                "keyId": data_key_id,  
                "queries": {"queryType": "equality"},  
            }  
        ]  
    }  
}  
  
# Auto Encryption Options  
auto_encryption_opts = AutoEncryptionOpts(  
    kms_providers=kms_providers,  
    key_vault_namespace=key_vault_namespace,  
    encrypted_fields_map=encrypted_fields_map  
)  
  
# Create an Encrypted MongoClient  
encrypted_client = MongoClient(  
    connection_string,  
    auto_encryption_opts=auto_encryption_opts  
)  
  
# Get the encrypted collection  
db = encrypted_client["test"]  
collection = db["coll"]  
  
# Create the encrypted collection (if it doesn't exist)  
try:  
    db.create_collection(  
        "coll",  
        encryptedFields=encrypted_fields_map["test.coll"]  # Corrected parameter name  
    )  
    print("Encrypted collection 'coll' created.")  
except errors.CollectionInvalid:  
    # Collection already exists  
    pass  
  
# Insert a document with an encrypted field  
doc = {"_id": 1, "secretField": "mySecretData"}  
  
try:  
    collection.insert_one(doc)  
    print("Inserted document into encrypted collection.")  
except errors.DuplicateKeyError:  
    # Document already exists  
    pass  
  
# Query the document using the encrypted field  
query_result = collection.find_one({"secretField": "mySecretData"})  
  
print("\nQueried Document:")  
print(json_util.dumps(query_result, indent=2))  
  
# Clean up  
encrypted_client.close()  
regular_client.close()  
