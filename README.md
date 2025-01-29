# csfle-Dockerfile

---

# Enhancing Data Security with MongoDB's Queryable Encryption  
   
With the increasing amount of sensitive information stored and processed by applications and "agents", ensuring that data remains confidential and secure is a top priority. One of the cutting-edge solutions to this challenge is **queryable encryption**. In this blog post, we'll explore what queryable encryption is, how it enhances privacy and security, and how you can implement it using MongoDB. We'll also touch upon the concept of envelope encryption to give you a comprehensive understanding of modern encryption practices.  
   
---  
   
## What is Queryable Encryption?  
   
Queryable encryption is an advanced encryption technique that allows applications to perform queries on encrypted data without decrypting it first. This means that sensitive data remains encrypted at all times, even during search operations, significantly reducing the risk of data exposure.  
   
Traditionally, when data is encrypted, it must be decrypted before a database can perform queries on it. This decryption process can create vulnerabilities, as the data is momentarily exposed in plaintext. Queryable encryption eliminates this risk by enabling encrypted queries, ensuring data remains secure throughout its lifecycle.  
   
---  
   
## Benefits of Queryable Encryption  
   
### Enhanced Privacy and Security  
   
- **Data Confidentiality**: Data remains encrypted both at rest and in use, preventing unauthorized access.  
- **Reduced Attack Surface**: By minimizing the need to decrypt data, you reduce the opportunities for attackers to intercept plaintext information.  
- **Regulatory Compliance**: Helps in meeting stringent data protection regulations like GDPR and HIPAA by providing robust data security measures.  
   
---  
   
## Understanding Envelope Encryption  
   
Before diving into the implementation, it's important to understand **envelope encryption**, a widely-used model in securing data.  
   
### What is Envelope Encryption?  
   
Envelope encryption is a method of encrypting data where the data itself is encrypted with a **data encryption key (DEK)**, and the DEK is then encrypted with a separate **key encryption key (KEK)**. This adds an extra layer of security and makes key management more flexible and secure.  
   
- **Data Encryption Key (DEK)**: A symmetric key used to encrypt the actual data.  
- **Key Encryption Key (KEK)**: A key used to encrypt the DEK. Often managed by a Key Management Service (KMS).  
   
By separating the encryption keys, you can securely manage and rotate keys without re-encrypting the entire dataset.  
   
---  
   
## Implementing Queryable Encryption with MongoDB  
   
MongoDB provides a powerful and flexible way to implement queryable encryption through client-side field-level encryption. Let's walk through how to set this up using Python and PyMongo.  
   
### Prerequisites  
   
### 1. Setting Up the Environment  
   
Use the provided Dockerfile to set up the environment:  
   
```dockerfile  
# Use Ubuntu 22.04 as the base image  
FROM ubuntu:22.04   
  
# Install necessary system packages and Python 3.10  
# Install MongoDB Enterprise and PyMongo with encryption support  
   
# Set the working directory  
WORKDIR /app  
   
# Copy the application code  
COPY . /app  
   
CMD ["python3.10", "queryable-encryption.py"]  
```

---

`docker build -t <image-name> .`

---

`docker run -it --rm <image-name>`

---
   
### 2. Configuring KMS Providers  
   
For this example, we'll use a local KMS provider with a local master key. Note that in production, you should use a secure KMS provider like AWS KMS, Azure Key Vault, or GCP KMS.  
   
```python  
# 1. Local Master Key (96 bytes). For testing only.  
local_master_key = b'\x00' * 96  # Using zeros for simplicity; do not use in production.  
   
# 2. KMS Providers Configuration  
kms_providers = {  
    "local": {  
        "key": local_master_key  
    }  
}  
```  
   
### 3. Setting up the Key Vault  
   
The key vault is a special collection where MongoDB stores the DEKs.  
   
```python  
# 3. Key Vault Namespace: Database and Collection to store the DEK  
key_vault_namespace = "encryption.__keyVault"  
   
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
```  
   
### 4. Creating Data Encryption Keys (DEKs)  
   
We need to create DEKs that will be used to encrypt specific fields in our documents.  
   
```python  
# Data Encryption Key (DEK) Setup  
   
# Check if a DEK with the specified key_alt_names exists  
key_alt_name1 = "demo-data-key1"  
existing_key1 = key_vault.find_one({"keyAltNames": key_alt_name1})  
key_alt_name2 = "demo-data-key2"  
existing_key2 = key_vault.find_one({"keyAltNames": key_alt_name2})  
   
if existing_key1 and existing_key2:  
    data_key_id1 = existing_key1["_id"]  
    data_key_id2 = existing_key2["_id"]  
    print("Using existing Data Encryption Key.")  
else:  
    # Create new DEKs  
    client_encryption = ClientEncryption(  
        kms_providers,  
        key_vault_namespace,  
        regular_client,  
        CodecOptions(uuid_representation=STANDARD),  
    )  
    data_key_id1 = client_encryption.create_data_key(  
        "local", key_alt_names=[key_alt_name1]      
    )  
    data_key_id2 = client_encryption.create_data_key(  
        "local", key_alt_names=[key_alt_name2]      
    )  
    client_encryption.close()  
    print("Created new Data Encryption Keys.")  
```  
   
### 5. Defining the Encrypted Fields Map  
   
The encrypted fields map specifies which fields in your collection should be encrypted and how.  
   
```python  
# Encrypted Fields Map Configuration  
encrypted_fields_map = {  
    "test.coll": {  
        "fields": [  
            {  
                "path": "email",  
                "bsonType": "string",  
                "keyId": data_key_id1,  
                "queries": {"queryType": "equality"},  # Enables queryable encryption  
            },  
            {  
                "path": "memory",  
                "bsonType": "string",  
                "keyId": data_key_id2,  
            },  
        ]  
    }  
}  
```  
   
In this example:  
   
- The `email` field is encrypted and supports equality queries.  
- The `memory` field is encrypted but not queryable.  
   
### 6. Setting Up Auto Encryption Options  
   
Configure the client to automatically handle encryption and decryption based on the encrypted fields map.  
   
```python  
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
```  
   
### 7. Working with the Encrypted Collection  
   
Create the collection with encryption enabled (if it doesn't exist) and insert documents.  
   
```python  
# Get the encrypted collection  
db = encrypted_client["test"]  
collection = db["coll"]  
   
# Create the encrypted collection (if it doesn't exist)  
try:  
    db.create_collection(  
        "coll",  
        encryptedFields=encrypted_fields_map["test.coll"]  
    )  
    print("Encrypted collection 'coll' created.")  
except errors.CollectionInvalid:  
    # Collection already exists  
    pass    
  
# Insert documents  
doc1 = {"_id": 1, "email": "demo@demo.com", "memory": "Confidential plan details..."}  
doc2 = {"_id": 2, "email": "user@example.com", "memory": "Password is `abc123`."}  
   
try:  
    collection.insert_one(doc1)  
    collection.insert_one(doc2)  
    print("Inserted documents into encrypted collection.")  
except errors.DuplicateKeyError:  
    # Documents already exist  
    pass  
```  
   
### 8. Querying Encrypted Data  
   
Now, you can perform queries on the encrypted `email` field.  
   
```python  
# Query the document using the encrypted field  
query_result = collection.find({"email": "demo@demo.com"})  
   
print("\nQueried Document:")  
for doc in query_result:  
    print(doc)  
```  
   
Since the `email` field is set up with `queryType: equality`, MongoDB handles the encryption of the query parameter and returns the matching documents, all while the data remains encrypted in the database.  
   
---  
   
## Conclusion  
   
Queryable encryption represents a significant advancement in data security, allowing applications to perform searches on encrypted data without compromising confidentiality. By leveraging MongoDB's client-side field-level encryption and envelope encryption practices, you can enhance the privacy and security of your applications.  
   
Implementing queryable encryption might seem complex at first, but as we've seen, with the right tools and understanding, it can be integrated seamlessly. By securing sensitive fields and enabling encrypted queries, you're taking a proactive step towards safeguarding your data against unauthorized access and potential breaches.  
   
---  
   
**Disclaimer**: The code examples provided are for educational purposes and use a local master key, which is not suitable for production environments. Always use a secure KMS provider and follow best practices for key management and encryption when deploying to production.  
   
---  
   
