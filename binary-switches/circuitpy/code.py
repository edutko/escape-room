import board
import digitalio
import time
import os
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
import tm1637_display

target_value = int(os.getenv('TARGET_VALUE'))
password = os.getenv('UNLOCK_PASSWORD')

display = tm1637_display.TM1637Display(clock=board.GP0, data=board.GP1)
kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)
switch_pins = [
    board.GP2,
    board.GP3,
    board.GP4,
    board.GP5,
    board.GP6,
    board.GP7,
    board.GP8,
    board.GP9,
    board.GP10,
    board.GP11,
]
switches = []
latched = False


def release_latch():
    global latched
    if latched:
        latched = False
        print("latch released")
        layout.write('{}\n'.format(password))


def engage_latch():
    global latched
    if not latched:
        latched = True
        print("latch engaged")


def init():
    display.clear()
    for i in range(0, len(switch_pins)):
        switches.append(digitalio.DigitalInOut(switch_pins[i]))
        switches[i].switch_to_input(pull=digitalio.Pull.UP)
    engage_latch()


def loop():
    value = 0
    for i in range(0, len(switches)):
        if not switches[i].value:
            value += 1 << i
    display.print('{:04}'.format(value))
    if value == target_value:
        release_latch()
        time.sleep(0.4)
    else:
        engage_latch()
    time.sleep(0.1)


init()
while True:
    loop()
