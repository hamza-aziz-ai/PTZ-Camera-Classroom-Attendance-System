import multiprocessing
import threading

from milvus_server import create_connection, create_collection
from multicam_stream_consumer import consumer_main
from consumer_for_counting_students import consumer_main as count_main
from ptzcam_multistream_producer import producer_main
from multiprocessing_shared_buffer import MULTIPROCESS_SHARED_BUFFER, MULTIPROCESS_COUNT_BUFFER
from parameters import MILVUS_COLLECTION_NAME

if __name__ == "__main__":
    ####################################################################################################################
    # ESTABLISH CONNECTION WITH MILVUS SERVER
    ####################################################################################################################
    # Establishing connection and creating collection
    create_connection()
    embeddings_collection = create_collection(MILVUS_COLLECTION_NAME)

    # load the known faces and embeddings
    embeddings_collection.load()
    ####################################################################################################################

    producer_process = multiprocessing.Process(target=producer_main, args=(MULTIPROCESS_SHARED_BUFFER, MULTIPROCESS_COUNT_BUFFER))
    producer_process.start()

    count_thread = threading.Thread(target=count_main, args=(MULTIPROCESS_COUNT_BUFFER,))
    count_thread.start()

    consumer_main(MULTIPROCESS_SHARED_BUFFER, embeddings_collection)

    producer_process.join()
    count_thread.join()
