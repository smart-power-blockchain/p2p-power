from gpiozero import LED
from time import sleep

led = LED(3)

while(True):
    led.on()
    print("ON")
    sleep(1)
    led.off()
    print("OFF")
    sleep(1)