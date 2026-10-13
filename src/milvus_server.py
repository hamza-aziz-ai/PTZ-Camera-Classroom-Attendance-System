"""
This module is created to connect to milvus vector database service and store the embeddings which will then be
retrieved to compare them with the live stream face embeddings for facial recognition software

Reference: https://github.com/milvus-io/milvus

Date: 7 August 2023
Script Template Creator: Anubhav Patrick
Authors: Hamza Aziz and Kshitij Parashar
"""

# Import Dependencies
from pymilvus import (
    connections,
    utility,
    FieldSchema, CollectionSchema, DataType,
    Collection
)

from custom_logging import multicam_server_logger
from parameters import MILVUS_HOST, \
    MILVUS_PORT, \
    MILVUS_COLLECTION_NAME, \
    INDEX_TYPE, \
    METRIC_TYPE


# PART 1: CONNECTING TO MILVUS
def create_connection(host: str = MILVUS_HOST, port: str = MILVUS_PORT):
    try:
        connections.connect("default", host=host, port=port)
        multicam_server_logger.info("Successfully connected to Milvus Server")
    except Exception as exception:
        multicam_server_logger.error(f"Error connecting to Milvus server due to exception: {exception}")


# PART 2: CREATE COLLECTION
def create_collection(collection_name: str = MILVUS_COLLECTION_NAME):
    if utility.has_collection(collection_name):
        multicam_server_logger.info(f"Collection {collection_name} already exists.")
        return Collection(collection_name)

    fields = [
        FieldSchema(name="name_id", dtype=DataType.VARCHAR, is_primary=True, max_length=60),
        FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=512)
    ]
    schema = CollectionSchema(fields=fields, collection_name=collection_name)

    embeddings_collection = Collection(name=collection_name, schema=schema)
    multicam_server_logger.info(f"Collection '{collection_name}' created successfully.")

    return embeddings_collection


# PART 3: INSERTING DATA
def insert_data(collection: Collection, entities: list):
    collection.insert(data=entities)

    collection.flush()

    # print(collection_name.num_entities)

    # create index
    # We are going to create an IVF_FLAT index for hello_milvus collection.
    # create_index() can only be applied to `FloatVector` and `BinaryVector` fields.
    multicam_server_logger.info(f"Start Creating index {INDEX_TYPE} for {METRIC_TYPE}")
    index = {
        "index_type": INDEX_TYPE,
        "metric_type": METRIC_TYPE,
        "params": {"nlist": 128}
    }

    collection.create_index("embeddings", index)

    print(f"Embeddings successfully inserted and the length is {collection.num_entities}")
    multicam_server_logger.info(f"Embeddings successfully inserted and the length is {collection.num_entities}")


# PART 4: SEARCHING THE CURRENT (DESIRED) EMBEDDING FROM THE EMBEDDING DATABASE
def search_embedding(collection: Collection, current_face_embeddings):
    vectors_to_search = current_face_embeddings
    search_params = {
        "metric_type": METRIC_TYPE,
        "params": {"nprobe": 10}
    }

    result = collection.search(
        data=vectors_to_search,
        anns_field="embeddings",
        param=search_params,
        limit=1,
        output_fields=["name_id"]
    )

    return result


# PART 5: DELETING A COLLECTION IF IT ALREADY EXISTS
def delete_collection(collection_name: str):
    if utility.has_collection(collection_name):
        user_input = input(f"Collection {collection_name} already exists. Do you want to delete it and create new collection? (Y for yes / N for No)")
        if user_input.lower() == "y":
            utility.drop_collection(collection_name)
            multicam_server_logger.warning(f"Collection {collection_name} already exists, so deleting it...")
            print(f"Collection {collection_name} already exists, so deleting it...")
        else:
            multicam_server_logger.info(f"User prompted to cancel the deletion of collection {collection_name}")
            print(f"User prompted to cancel the deletion of collection {collection_name}")
