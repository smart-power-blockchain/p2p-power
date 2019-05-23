from flask import Flask, request, jsonify
from relay import Relay
from time import sleep
from gpiozero import LED


app = Flask(__name__)
provider = Relay(2)
provider.off()

@app.route("/")
def root():
	return "hello world"

@app.route("/transfer")
def transfer():
    energy = int(request.args['energy'])
    provider.on()
    sleep(energy)
    provider.off()
    return "did something"



if __name__ == '__main__':
	app.run(host='0.0.0.0')
