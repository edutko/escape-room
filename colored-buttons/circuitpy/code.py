import board
import digitalio
import time
import os
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode


class ArcadeButton(object):
    def __init__(self, color: str, led_pin, switched_pin):
        self._color = color

        self._ledPin = digitalio.DigitalInOut(led_pin)
        self._ledPin.direction = digitalio.Direction.OUTPUT
        self._ledPin.value = False

        self._switchedPin = digitalio.DigitalInOut(switched_pin)
        self._switchedPin.switch_to_input(pull=digitalio.Pull.UP)

        self._inverted = True
        self._lastState = False
        self._on = False

    def color(self):
        return self._color

    def on(self):
        if not self._on:
            self.toggle_led()

    def off(self):
        if self._on:
            self.toggle_led()

    def pressed(self):
        p = (self._inverted ^ self._switchedPin.value)
        last_state = self._lastState
        self._lastState = p
        if p and not last_state:
            print(f'{self._color} pressed')
        return p and not last_state

    def toggle_led(self):
        if self._inverted:
            self._switchedPin.switch_to_input(pull=digitalio.Pull.DOWN)
            self._on = True
            print(f'{self._color} on')
        else:
            self._switchedPin.switch_to_input(pull=digitalio.Pull.UP)
            self._on = False
            print(f'{self._color} off')
        self._inverted = not self._inverted
        self._ledPin.value = not self._ledPin.value


kbd = Keyboard(usb_hid.devices)
buttons = [
    ArcadeButton('r', board.GP0, board.GP1),
    ArcadeButton('y', board.GP2, board.GP3),
    ArcadeButton('g', board.GP4, board.GP5),
    ArcadeButton('b', board.GP6, board.GP7),
    ArcadeButton('w', board.GP10, board.GP11)
]
latched = False


def release_latch():
    global latched
    if latched:
        latched = False
        print("latch released")
        kbd.press(Keycode.CONTROL, Keycode.SHIFT, Keycode.E)
        time.sleep(0.1)
        kbd.release_all()


def engage_latch():
    global latched
    if not latched:
        latched = True
        print("latch engaged")


def reset():
    for btn in buttons:
        btn.off()
    current_sequence.clear()


def init():
    engage_latch()
    reset()


def loop():
    global last_acton
    for btn in buttons:
        # btn.update()
        if btn.pressed():
            btn.on()
            current_sequence.append(btn.color())
            last_acton = time.monotonic()
            print(current_sequence)

    if current_sequence == target_sequence:
        release_latch()
    elif current_sequence == reset_sequence:
        engage_latch()

    time_since_action = time.monotonic() - last_acton
    if len(current_sequence) >= len(target_sequence) and time_since_action > 0.5 \
            or len(current_sequence) > 0 and time_since_action > 3.0:
        reset()


target_sequence = list(os.getenv('TARGET_SEQUENCE', ''))
reset_sequence = list(os.getenv('RESET_SEQUENCE', ''))
current_sequence = []
last_acton = time.monotonic()

init()
while True:
    loop()
