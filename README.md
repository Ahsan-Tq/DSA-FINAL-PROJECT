# Blockchain Ledger System (DSA Project)

This project is a Data Structures and Algorithms (DSA) based implementation of a simple blockchain ledger system.  
It demonstrates how blockchain concepts can be built using core data structures without relying on external frameworks.

## Objective
The goal of this project is to understand and apply:
- Linked data structures
- Hashing
- Data integrity and verification
- Transaction chaining

## Features
- Create and store blocks containing transactions
- Each block is linked using cryptographic hash values
- Ledger integrity verification
- Menu-driven interface for interaction
- Persistent storage using local files / SQLite (if applicable)

## Data Structures Used
- Linked List (block chaining)
- Strings and arrays
- Hashing for block validation

## How It Works
1. A block contains transaction data and a hash of the previous block
2. Each new block is linked to the last block in the ledger
3. Any change in data breaks the hash chain, ensuring integrity
4. Users interact through a simple frontend (CLI / GUI)

## How to Run
1. Clone the repository
   ```bash
   git clone <repository-link>
