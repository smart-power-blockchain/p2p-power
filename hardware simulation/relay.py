from gpiozero import LED
from time import sleep

class Relay:
    def __init__(self, pin):
        self.pin = LED(pin)
    def on(self):
        self.pin.off()
    def off(self):
        self.pin.on()
    def toggle(self):
        self.pin.toggle()
