from . import db
from sqlalchemy.dialects.postgresql import JSON

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    balance = db.Column(db.Float, default=100.0)
    public_key = db.Column(db.JSON, nullable=False)
    mail_box = db.Column(db.JSON, default=[])

    def __init__(self, username, email, password, public_key, balance=100.0):
        self.username = username
        self.email = email
        self.password = password
        self.public_key = public_key
        self.balance = balance
        self.mail_box = []

    def credit(self, amount):
        self.balance += amount

    def debit(self, amount):
        if amount > self.balance:
            raise ValueError("Fonduri insuficiente pentru a efectua tranzactia.")
        self.balance -= amount
