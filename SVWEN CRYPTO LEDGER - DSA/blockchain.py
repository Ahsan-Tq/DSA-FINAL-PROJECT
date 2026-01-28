from datetime import datetime
import hashlib
from database import (
    get_all_blocks,
    init_database,
    insert_block,
    is_database_empty,
    update_block_hashes,
)

class Block:
    
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.current_hash = self.calculate_hash()
        self.next = None
    
    def calculate_hash(self):
        payload = f"{self.index}|{self.timestamp}|{self.data}|{self.previous_hash}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

class Blockchain:
    
    def __init__(self):
        self.head = None
        self.is_valid = True
        init_database()
        self.load_blocks_from_db()
    
    def load_blocks_from_db(self):
        blocks_data = get_all_blocks()
        if not blocks_data:
            return
        
        prev_block = None
        expected_prev_hash = "0"
        needs_migration = False

        for index, timestamp, data, previous_hash_db, hash_db in blocks_data:
            block = Block(index, timestamp, data, expected_prev_hash)

            if previous_hash_db != expected_prev_hash or hash_db != block.current_hash:
                needs_migration = True

            if prev_block:
                prev_block.next = block
            else:
                self.head = block

            prev_block = block
            expected_prev_hash = block.current_hash

        if needs_migration and self.head is not None:
            current = self.head
            while current is not None:
                update_block_hashes(current.index, current.previous_hash, current.current_hash)
                current = current.next
    
    def create_genesis_block(self):
        if self.head is not None:
            print("Genesis block already exists!")
            return
        
        if not is_database_empty():
            self.load_blocks_from_db()
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        genesis = Block(0, timestamp, "Genesis Block", "0")
        self.head = genesis
        
        insert_block(genesis.index, genesis.timestamp, genesis.data, 
                    genesis.previous_hash, genesis.current_hash)
        print(f"Genesis block created! Hash: {genesis.current_hash}")
    
    def add_block(self, data):
        if not self.is_valid:
            print("Cannot add transactions: Blockchain integrity is compromised!")
            return False
        
        if self.head is None:
            print("Please create genesis block first!")
            return False
        
        current = self.head
        while current.next is not None:
            current = current.next
        
        index = current.index + 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_block = Block(index, timestamp, data, current.current_hash)
        
        current.next = new_block
        
        insert_block(new_block.index, new_block.timestamp, new_block.data,
                    new_block.previous_hash, new_block.current_hash)
        print(f"Block {index} added! Hash: {new_block.current_hash}")
        return True
    
    def get_block_by_index(self, index):
        current = self.head
        while current is not None:
            if current.index == index:
                return current
            current = current.next
        return None
    
    def verify_chain(self):
        if self.head is None:
            print("Blockchain is empty!")
            self.is_valid = False
            return False
        
        current = self.head
        prev_hash = "0"
        
        while current is not None:
            if current.previous_hash != prev_hash:
                print(f"Block {current.index}: Previous hash mismatch!")
                print("⚠ Blockchain integrity check: FAILED")
                print("Ledger is compromised!")
                self.is_valid = False
                return False
            
            calculated_hash = current.calculate_hash()
            if calculated_hash != current.current_hash:
                print(f"Block {current.index}: Hash mismatch!")
                print("⚠ Blockchain integrity check: FAILED")
                print("Ledger is compromised!")
                self.is_valid = False
                return False
            
            prev_hash = current.current_hash
            current = current.next
        
        print("Blockchain verification: VALID")
        self.is_valid = True
        return True
    
    def search_by_name(self, name):
        if self.head is None:
            print("Blockchain is empty!")
            return
        
        found = False
        current = self.head
        
        if current.index == 0:
            current = current.next
        
        while current is not None:
            data_parts = current.data.split('|')
            from_name = ""
            to_name = ""
            
            for part in data_parts:
                part = part.strip()
                if part.startswith("From="):
                    from_name = part.split("=", 1)[1].strip()
                elif part.startswith("To="):
                    to_name = part.split("=", 1)[1].strip()
            
            if name.lower() in from_name.lower() or name.lower() in to_name.lower():
                print(f"\nBlock Index: {current.index}")
                print(f"Transaction Data: {current.data}")
                print(f"Block Hash: {current.current_hash}")
                print("-" * 60)
                found = True
            
            current = current.next
        
        if not found:
            print(f"No transactions found for name: {name}")
    
    def display_chain(self):
        if self.head is None:
            print("Blockchain is empty!")
            return
        
        print("\n=== ALL TRANSACTIONS ===")
        current = self.head
        while current is not None:
            print(f"\nBlock Index: {current.index}")
            print(f"Timestamp: {current.timestamp}")
            print(f"Data: {current.data}")
            print(f"Previous Hash: {current.previous_hash[:30]}...")
            print(f"Current Hash: {current.current_hash[:30]}...")
            print("-" * 60)
            current = current.next
        print()
