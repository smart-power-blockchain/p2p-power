import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
PIN = 4

GPIO.setup(PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

state = GPIO.input(PIN)
print(state)
while(True):
    if(state != GPIO.input(PIN)):
        state = GPIO.input(PIN)
        print(state)
