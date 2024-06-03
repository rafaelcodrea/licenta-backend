from flask import request, jsonify, current_app as app
from .models import User
from . import db
from .blockchain.blockchain import Blockchain, hash_password, Transaction, blockchain
from phe import paillier
import random

# Inițializăm blockchain-ul global și cheia publică/privată Paillier
public_key, private_key = paillier.generate_paillier_keypair()

def user_to_dict(user):
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'balance': user.balance,
        'public_key': user.public_key,
        'mail_box': user.mail_box
    }

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data['username']
    email = data['email']
    password = hash_password(data['password'])

    user = User(username=username, email=email, password=password,
                public_key={'n': str(public_key.n), 'g': str(public_key.g)},
                balance=100.0)
    db.session.add(user)
    db.session.commit()

    return jsonify(user_to_dict(user)), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data['username']
    password = hash_password(data['password'])

    user = User.query.filter_by(username=username).first()

    if user and user.password == password:
        return jsonify(user_to_dict(user)), 200

    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get(user_id)
    if user:
        return jsonify(user_to_dict(user)), 200
    return jsonify({'error': 'User not found'}), 404

@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    users_dict = [user_to_dict(user) for user in users]
    return jsonify(users_dict), 200

@app.route('/transaction', methods=['POST'])
def transaction():
    data = request.json
    sender_id = data['sender_id']
    recipient_id = data['recipient_id']
    amount = data['amount']

    sender = User.query.get(sender_id)
    recipient = User.query.get(recipient_id)

    if sender and recipient and sender.balance >= amount:
        sender.debit(amount)
        recipient.credit(amount)
        db.session.commit()

        transaction = Transaction("send", sender, recipient, amount)
        blockchain.add_transaction(transaction)

        return jsonify({'message': 'Transaction successful'}), 200
    return jsonify({'error': 'Transaction failed'}), 400

@app.route('/generate_random_transactions', methods=['POST'])
def generate_random_transactions():
    data = request.json
    num_transactions = data.get('num_transactions', 15)

    users = User.query.all()
    if len(users) < 2:
        return jsonify({'error': 'Not enough users to generate transactions'}), 400

    transactions = []
    for _ in range(num_transactions):
        sender, receiver = random.sample(users, 2)
        amount = 1  # Each transaction transfers 1 unit
        if sender.balance >= amount:
            sender.debit(amount)
            receiver.credit(amount)
            transaction = Transaction("send", sender, receiver, amount)
            blockchain.add_transaction(transaction)

    db.session.commit()

    return jsonify({'message': f'{num_transactions} transactions generated successfully'}), 200

@app.route('/blocks', methods=['GET'])
def get_blocks():
    def block_to_dict(block):
        return {
            'parent_root': block.parent_root,
            'state_root': block.state_root,
            'hash': block.hash,
            'body': {
                'graffiti': block.body.graffiti,
                'execution_payload': {
                    'transactions': [tx.to_dict() for tx in block.body.execution_payload.transactions],
                    'block_number': block.body.execution_payload.block_number,
                    'gas_used': block.body.execution_payload.gas_used,
                    'timestamp': block.body.execution_payload.timestamp.isoformat(),
                }
            }
        }
    blocks_dict = [block_to_dict(block) for block in blockchain.chain]
    return jsonify(blocks_dict), 200


@app.route('/blocks_encrypted', methods=['GET'])
def get_blocks_encrypted():
    def encrypt_transaction(tx):
        try:
            encrypted_sender = public_key.encrypt(tx['sender'])
            encrypted_receiver = public_key.encrypt(tx['receiver'])
            return {
                **tx,
                'sender': str(encrypted_sender.ciphertext()),
                'receiver': str(encrypted_receiver.ciphertext())
            }
        except Exception as e:
            print(f"Error encrypting transaction: {e}")
            return tx

    def block_to_dict_encrypted(block):
        return {
            'parent_root': block.parent_root,
            'state_root': block.state_root,
            'hash': block.hash,
            'body': {
                'graffiti': block.body.graffiti,
                'execution_payload': {
                    'transactions': [encrypt_transaction(tx.to_dict()) for tx in
                                     block.body.execution_payload.transactions],
                    'block_number': block.body.execution_payload.block_number,
                    'gas_used': block.body.execution_payload.gas_used,
                    'timestamp': block.body.execution_payload.timestamp.isoformat(),
                }
            }
        }

    encrypted_blocks_dict = [block_to_dict_encrypted(block) for block in blockchain.chain]
    return jsonify(encrypted_blocks_dict), 200
@app.route('/transactions/<int:user_id>', methods=['GET'])
def get_user_transactions(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user_transactions = []
    for block in blockchain.chain:
        for transaction in block.body.execution_payload.transactions:
            if transaction.sender.username == user.username or transaction.receiver.username == user.username:
                user_transactions.append(transaction.to_dict())

    # Criptăm expeditorul și destinatarul
    encrypted_transactions = []
    for tx in user_transactions:
        try:
            encrypted_sender = public_key.encrypt(tx['sender'])
            encrypted_receiver = public_key.encrypt(tx['receiver'])
            encrypted_tx = {
                **tx,
                'sender': str(encrypted_sender.ciphertext()),
                'receiver': str(encrypted_receiver.ciphertext())
            }
            encrypted_transactions.append(encrypted_tx)
        except Exception as e:
            print(f"Error encrypting transaction: {e}")
            continue

    return jsonify(encrypted_transactions), 200
