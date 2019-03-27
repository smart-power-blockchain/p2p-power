from collections import OrderedDict
import binascii
import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
import requests
from flask import Flask, jsonify, request, render_template


DEFAULT_WALLET_VALUE = 50


class Transaction:

    def __init__(self, sender_address, sender_private_key, recipient_address, value):
        self.sender_address = sender_address
        self.sender_private_key = sender_private_key
        self.recipient_address = recipient_address
        self.value = value

    def __getattr__(self, attr):
        return self.data[attr]

    def to_dict(self):
        return OrderedDict({'sender_address': self.sender_address,
                            'recipient_address': self.recipient_address,
                            'value': self.value})

    def sign_transaction(self):
        # sign transaction with an private key
        private_key = RSA.importKey(
            binascii.unhexlify(self.sender_private_key))
        signer = PKCS1_v1_5.new(private_key)
        h = SHA.new(str(self.to_dict()).encode('utf8'))
        return binascii.hexlify(signer.sign(h)).decode('ascii')


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('./index.html')


@app.route('/make/transaction')
def make_transaction():
    return render_template('./make_transaction.html')


@app.route('/view/transactions')
def view_transaction():
    return render_template('./view_transactions.html')


@app.route('/make/error')
def make_error():
    return render_template('./not_enough_coins.html')


@app.route('/wallet/new', methods=['POST'])
def new_wallet():
    random_gen = Crypto.Random.new().read
    private_key = RSA.generate(1024, random_gen)
    public_key = private_key.publickey()
    username = request.form['username']
    surplus_energy = request.form['surplus_energy']

    user_exists = False

    with open('saveWallet.txt', 'r+') as f:
        for user in f.readlines():
            if(user.split(',')[0] == username):
                user_exists = True

    with open('saveWallet.txt', 'a') as f:
        if(user_exists != True):
            f.write("{},{},{},{},{}\n".format(username,
                                              binascii.hexlify(private_key.exportKey(
                                                  format='DER')).decode('ascii'),
                                              binascii.hexlify(public_key.exportKey(
                                                  format='DER')).decode('ascii'),
                                              DEFAULT_WALLET_VALUE, surplus_energy))
        else:
            return 'error', 500

    response = {
        'username': username,
        'private_key': binascii.hexlify(private_key.exportKey(format='DER')).decode('ascii'),
        'public_key': binascii.hexlify(public_key.exportKey(format='DER')).decode('ascii'),
        'wallet_value': 50,
        'surplus_energy': surplus_energy
    }

    return jsonify(response), 200


@app.route('/generate/transaction', methods=['POST'])
def generate_transaction():

    sender_address = request.form['sender_address']
    sender_private_key = request.form['sender_private_key']
    recipient_address = request.form['recipient_address']
    value = request.form['amount']

    with open('saveWallet.txt', 'w') as f:
        walletAmount = f.readline().split(',')[3]
        if int(value) > int(walletAmount):
            return 'error', 500
        else:
            f.readline().split(',')[3] -= value

    transaction = Transaction(
        sender_address, sender_private_key, recipient_address, value)

    response = {'transaction': transaction.to_dict(
    ), 'signature': transaction.sign_transaction()}

    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=8080,
                        type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='127.0.0.1', port=port, debug=True)
