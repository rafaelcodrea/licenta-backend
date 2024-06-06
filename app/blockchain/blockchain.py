import hashlib
from datetime import datetime
import json
from phe import paillier
import random

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

class User:
    def __init__(self, id, username, password, email, balance=0):
        self.id = id
        self.username = username
        self.password = hash_password(password)
        self.balance = balance
        self.email = email
        self.mail_box = []

        self.public_key, self.private_key = paillier.generate_paillier_keypair()
        self.address = str(self.public_key.n)[:42]

    def credit(self, amount):
        self.balance += amount

    def debit(self, amount):
        if amount > self.balance:
            raise ValueError("Fonduri insuficiente pentru a efectua tranzactia.")
        self.balance -= amount

    def __str__(self):
        return (f"User {self.id}, Balance: {self.balance}, "
                f"Username: {self.username}, Password: {self.password}, Email: {self.email}, "
                f"Message log: {self.mail_box}, "
                f"Public Key: n={self.public_key.n}, g={self.public_key.g}, "
                f"Private Key: lambda={self.private_key.lambda_val}, mu={self.private_key.mu}")

class Transaction:
    def __init__(self, tx_type, sender, receiver, value=0, message="", data=None):
        self.tx_type = tx_type
        self.sender = sender
        self.receiver = receiver
        self.value = value
        #self.hashValue
        self.data = data
        self.message = message

    def __str__(self):
        return f"Transaction: {self.tx_type} from {self.sender.username} to {self.receiver.username}, value: {self.value}, data: {self.data}, message: {self.message}"

    def to_dict(self):
        return {
            'tx_type': self.tx_type,
            'sender': self.sender.username,
            'receiver': self.receiver.username,
            'value': self.value,
            'message': self.message,
            'data': self.data
        }

    def execute(self):
        if self.tx_type == "send":
            self.execute_send()
        elif self.tx_type == "smart_contract_call":
            self.execute_smart_contract_call()
        elif self.tx_type == "sign_message":
            self.execute_sign_message()

    def execute_send(self):
        if self.value > 0 and self.sender.balance >= self.value:
            self.sender.debit(self.value)
            self.receiver.credit(self.value)
            print(f"Tranzactie realizata cu succes: {self.value} trimisi de {self.sender.id} catre {self.receiver.id}.")
        else:
            print("Tranzactia a esuat: fonduri insuficiente!")

    def execute_smart_contract_call(self):
        pass

    def execute_sign_message(self):
        public_key_str = f"n={self.sender.public_key.n}, g={self.sender.public_key.g}"
        self.receiver.mail_box.append(f'"{self.message} Sent by: {public_key_str}"')

class ExecutionPayload:
    def __init__(self, transactions, block_number, gas_used):
        self.transactions = transactions
        self.block_number = block_number
        self.gas_limit = 10000
        self.gas_used = gas_used
        self.timestamp = datetime.now()

    def print_payload(self):
        print("Execution Payload:")
        print(f"Transactions: {[str(tx) for tx in self.transactions]}")
        print(f"Block Number: {self.block_number}")
        print(f"Gas Limit: {self.gas_limit}")
        print(f"Gas Used: {self.gas_used}")
        print(f"Timestamp: {self.timestamp}")

class Body:
    def __init__(self, graffiti, execution_payload):
        self.graffiti = graffiti
        self.execution_payload = execution_payload

    def print_body(self):
        print("Body:")
        print(f"Graffiti: {self.graffiti}")
        self.execution_payload.print_payload()

class Block:
    def __init__(self, parent_root, state_root, graffiti, transactions, block_number, gas_used):
        self.parent_root = parent_root
        self.state_root = state_root
        self.body = Body(graffiti, ExecutionPayload(transactions, block_number, gas_used))
        self.hash = self.compute_hash()

    def compute_hash(self):
        block_string = f"{self.parent_root}{self.state_root}{self.body.graffiti}{self.body.execution_payload.transactions}{self.body.execution_payload.block_number}{self.body.execution_payload.gas_used}{self.body.execution_payload.timestamp}".encode()
        return hashlib.sha256(block_string).hexdigest()

    def compute_state_hash(self):
        block_string = f"{self.state_root}{self.hash}".encode()
        return hashlib.sha256(block_string).hexdigest()

    def to_dict(self):
        return {
            'parent_root': self.parent_root,
            'state_root': self.state_root,
            'hash': self.hash,
            'body': {
                'graffiti': self.body.graffiti,
                'execution_payload': {
                    'transactions': [tx.to_dict() for tx in self.body.execution_payload.transactions],
                    'block_number': self.body.execution_payload.block_number,
                    'gas_used': self.body.execution_payload.gas_used,
                    'timestamp': self.body.execution_payload.timestamp.isoformat(),
                }
            }
        }

    def print_block(self):
        print("Hash Block:", self.hash)
        print("Hash Parinte:", self.parent_root)
        print("State Root:", self.state_root)
        self.body.print_body()
        print(" ")

def calculate_state_root(state):
    state_string = json.dumps(state, sort_keys=True)
    return hashlib.sha256(state_string.encode()).hexdigest()

class Blockchain:
    def __init__(self, difficulty=2):
        self.chain = [self.create_genesis_block()]
        self.current_block_transactions = []
        self.state = {}
        self.difficulty = difficulty
        self.transactions_per_block = 2  # Maxim 2 tranzacții pe block

    def create_genesis_block(self):
        return Block("0" * 64, "0" * 64, "Genesis", [], 0, 0)

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, transactions):
        latest_block = self.get_latest_block()
        new_block = Block(
            parent_root=latest_block.hash,
            state_root=calculate_state_root(self.state),
            graffiti="Block",
            transactions=transactions,
            block_number=len(self.chain),
            gas_used=1000
        )
        self.chain.append(new_block)
        print(f"Block {new_block.body.execution_payload.block_number} adaugat cu succes.")
        print(f"Block contine {len(new_block.body.execution_payload.transactions)} tranzactii.")
        for tx in new_block.body.execution_payload.transactions:
            print(f"   {tx}")

    def add_transaction(self, transaction):
        transaction.execute()  # Execute the transaction
        self.current_block_transactions.append(transaction)
        print(f"Tranzactie adaugata: {transaction}")
        if len(self.current_block_transactions) >= self.transactions_per_block:
            self.add_block(self.current_block_transactions)
            self.current_block_transactions = []  # Reset current block transactions

    def print_chain(self):
        for block in self.chain:
            block.print_block()
            print("#########################################################\n")

blockchain = Blockchain()

print("Blocul Genesis:")
blockchain.get_latest_block().print_block()

print("Reteaua Blockchain:")
blockchain.print_chain()

def verify_chain(blockchain):
    previous_block = blockchain.chain[0]
    for block in blockchain.chain[1:]:
        if block.parent_root != previous_block.hash:
            return False
        if block.hash != block.compute_hash():
            return False
        if block.body.execution_payload.gas_used > block.body.execution_payload.gas_limit:
            return False
        previous_block = block
    return True

valid = verify_chain(blockchain)
print(f"Integritatea Lanțului: {'Valid' if valid else 'Invalid'}")

############test###########

def generate_test_users(n):
    users = []
    for i in range(n):
        user = User(
            id=f"user{i}",
            username=f"testuser{i}",
            password=f"password{i}",
            email=f"user{i}@test.com",
            balance=10  # Toți utilizatorii încep cu un balance de 10 unități
        )
        users.append(user)
    return users

users = generate_test_users(10)

for user in users:
    blockchain.state[user.id] = user.balance

def generate_random_transactions(users, num_transactions):
    transactions = []
    for _ in range(num_transactions):
        sender, receiver = random.sample(users, 2)
        transaction = Transaction(
            tx_type="send",
            sender=sender,
            receiver=receiver,
            value=1
        )
        transactions.append(transaction)
    return transactions

random_transactions = generate_random_transactions(users, 15)

for transaction in random_transactions:
    blockchain.add_transaction(transaction)

print("Reteaua Blockchain dupa adaugarea tranzactiilor:")
blockchain.print_chain()