class Block:
    
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.current_hash = self.calculate_hash()
        self.next = None
    
    def calculate_hash(self):
        hash_string = str(self.index) + self.timestamp + str(self.data) + self.previous_hash
        return str(hash(hash_string))
    
    def __str__(self):
        return f"Block {self.index}: Hash={self.current_hash[:10]}..., Data={self.data}"
