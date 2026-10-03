import board
import digitalio
import time
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS

lock_command = '/usr/local/bin/lock-phone.sh'
unlock_command = '/usr/local/bin/lock-phone.sh unlock'

kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)
pin_a = digitalio.DigitalInOut(board.D0)
pin_b = digitalio.DigitalInOut(board.D1)
latched = False


def release_latch():
    global latched
    if latched:
        latched = False
        layout.write(f'{unlock_command}\n')


def engage_latch():
    global latched
    if not latched:
        latched = True
        layout.write(f'{lock_command}\n')


def init():
    pin_a.direction = digitalio.Direction.OUTPUT
    pin_a.value = True
    pin_b.switch_to_input(pull=digitalio.Pull.DOWN)
    time.sleep(0.5)
    engage_latch()


def loop():
    if pin_b.value:
        release_latch()
        time.sleep(0.4)
    else:
        engage_latch()
    time.sleep(0.1)


init()
while True:
    loop()
