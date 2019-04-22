from collections import OrderedDict
import binascii
import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
import requests
from flask import Flask, jsonify, request, render_template, flash, redirect, session, url_for, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, IntegerField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from tempfile import mkstemp
from shutil import move
from os import fdopen, remove

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


class SignupForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=30)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    surplus_energy = IntegerField('Surplus Energy Units')
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message="Passwords do not match")
    ])
    confirm = PasswordField('Confirm Password')


app = Flask(__name__)


## CONFIGURATION FOR MYSQL DATABASE ##
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'akhil'
app.config['MYSQL_DB'] = 'jhoncoin'
app.config['MYSQL_PASSWORD'] = 'akhil@user'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

app.secret_key = "super secret key"

# initialize mysql
mysql = MySQL(app)


@app.route('/')
def start_page():
    return render_template('./index.html')


@app.route('/signup', methods=['GET', 'POST'])
def register():
    form = SignupForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        password = sha256_crypt.hash(str(form.password.data))

        # Create cursor
        cur1 = mysql.connection.cursor()
        cur2 = mysql.connection.cursor()

        # Execute query
        result = cur2.execute("SELECT  * from users where name = %s", [name])

        if result > 0:
            return render_template('signup.html', form=form, error='Username Already Exists Try A Diffrent Username')
        else:
            cur1.execute("INSERT INTO users(name, email, password) VALUES(%s, %s, %s)",
                         (name, email, password))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur1.close()
        cur2.close()

        # redirect to login page with success
        return render_template('/login.html', msg='Signup Successful You May Login Now')

    return render_template('signup.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute query
        result = cur.execute(
            "SELECT * FROM users WHERE name = %s", [username])

        if result > 0:
            data = cur.fetchone()
            password = data['password']

            if sha256_crypt.verify(password_candidate, password):
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('trading_center'))
            else:
                return render_template('/login.html', error='Password Does Not Match')

            # Close connection
            cur.close()
        else:
            return render_template('/login.html', error='Username Not Found')

    return render_template('/login.html')

# Check if user logged in


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))

    return wrap


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))


@app.route('/trading_center')
@is_logged_in
def trading_center():
    return render_template('./trading_center.html')


@app.route('/generate/wallet')
@is_logged_in
def generate_wallet():
    return render_template('./generate_wallet.html')


@app.route('/make/transaction')
@is_logged_in
def make_transaction():
    return render_template('./make_transaction.html')


@app.route('/view/transactions')
@is_logged_in
def view_transaction():
    return render_template('./view_transactions.html')


@app.route('/make/error')
@is_logged_in
def make_error():
    return render_template('./not_enough_coins.html')


@app.route('/update_energy', methods=['GET', 'POST'])
@is_logged_in
def update_energy():
    if request.method == 'POST':
        cur = mysql.connection.cursor()
        result = cur.execute("UPDATE users SET surplus_energy = surplus_energy + %s where name = %s", [
                             request.form['updated_energy'], request.form['username']])
        mysql.connection.commit()
        cur.close()
        if result > 0:
            return render_template('./update_energy.html', msg="Updated value has been successfully added")
        else:
            return render_template('./update_energy.html', error="ERROR ! Try Again")

    return render_template('./update_energy.html')


@app.route('/buy_energy', methods=['GET', 'POST'])
@is_logged_in
def buy_energy():
    cur = mysql.connection.cursor()
    result = cur.execute(
        "SELECT name, surplus_energy, public_key FROM users WHERE surplus_energy > 0")
    sellers = cur.fetchall()

    if result > 0:
        return render_template('./buy_energy.html', sellers=sellers)
    else:
        return render_template('./buy_energy.html', error="No sellers available")

    if request.method == 'POST':
        print(request.form)


@app.route('/wallet/new', methods=['POST'])
@is_logged_in
def new_wallet():
    random_gen = Crypto.Random.new().read
    private_key = RSA.generate(1024, random_gen)
    public_key = private_key.publickey()
    username = request.form['username']
    surplus_energy = request.form['surplus_energy']

    curWalletExist = mysql.connection.cursor()
    resultWalletExist = curWalletExist.execute(
        "SELECT * FROM users where name = %s and wallet_exist = %s", [username, 1])

    if(resultWalletExist == 0):
        cur = mysql.connection.cursor()
        result = cur.execute(
            "UPDATE users SET public_key = %s, private_key = %s, surplus_energy = %s, wallet_value = %s, wallet_exist = %s WHERE name = %s", [binascii.hexlify(public_key.exportKey(
                format='DER')).decode('ascii'), binascii.hexlify(private_key.exportKey(
                    format='DER')).decode('ascii'), surplus_energy, DEFAULT_WALLET_VALUE, 1, username])

        mysql.connection.commit()
        cur.close()
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
@is_logged_in
def generate_transaction():

    sender_address = request.form['sender_address']
    sender_private_key = request.form['sender_private_key']
    recipient_address = request.form['recipient_address']
    value = request.form['amount']

    cur1 = mysql.connection.cursor()
    result = cur1.execute(
        "UPDATE users set wallet_value = wallet_value - %s and surplus_energy = surplus_energy + %s where public_key = %s", [value, value, sender_address])
    mysql.connection.commit()
    cur1.close()

    cur2 = mysql.connection.cursor()
    result = cur2.execute(
        "UPDATE users set wallet_value = wallet_value + %s and surplus_energy = surplus_energy - %s where public_key = %s", [value, value, recipient_address])
    mysql.connection.commit()
    cur2.close()

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
