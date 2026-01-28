def calculate_hash(index, timestamp, data, previous_hash):
    hash_string = str(index) + timestamp + str(data) + previous_hash
    return str(hash(hash_string))
