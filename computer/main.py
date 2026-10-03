#!/usr/bin/env python3
"""
Escape Room Final Challenge
----------------------------
Flow:
  1. BLANK / PASSWORD stage
     - Screen is completely blank (black).
     - Keystrokes are buffered silently (not echoed).
     - If Enter is pressed and the buffer exactly matches the master
       password, we move on to the reset-question stage.
     - If Enter is pressed and it does NOT match, the buffer is cleared
       immediately and we keep listening.
     - If no Enter is pressed within `expire_seconds` of the last
       keystroke, the buffer silently clears itself so stray typing by
       participants can't "gum up" the real password entry.

  2. PASSWORD RESET stage
     - Three questions asked in sequence: date of birth, favorite pet
       name, mother's maiden name.
     - Input IS echoed here (it behaves like a normal form).
     - Wrong answers show a brief "Incorrect" flash, then clear the
       field so the participants can try again (no lockouts, since the
       whole point is they have to find the right answer via clues).

  3. CONGRATULATIONS stage
     - Final screen. Stays up forever. The only way out is Ctrl+C from
       a terminal (SIGINT), which is caught and exits cleanly.

Configuration lives in config.json next to this script -- edit that
file to set the real password and the three reset answers.
"""

import json
import os
import time
import argparse

import pygame

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

# ---- states ----
STATE_PASSWORD = "password"
STATE_DOB = "dob"
STATE_PET = "pet"
STATE_MAIDEN = "maiden"
STATE_CONGRATS = "congrats"

RESET_ORDER = [STATE_DOB, STATE_PET, STATE_MAIDEN]

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (60, 220, 90)
RED = (220, 60, 60)
GRAY = (140, 140, 140)

INCORRECT_FLASH_SECONDS = 1.3


def load_config():
    defaults = {
        "master_password": "CHANGEME",
        "date_of_birth": {"question": "Enter date of birth (MM/DD/YYYY):", "answer": "01/01/2000"},
        "pet_name": {"question": "Enter favorite pet's name:", "answer": "Whiskers"},
        "maiden_name": {"question": "Enter mother's maiden name:", "answer": "Smith"},
        "expire_seconds": 10.0,
        "congrats_message": "ACCESS GRANTED",
        "congrats_submessage": "Congratulations!",
        "windowed_width": 1024,
        "windowed_height": 768,
    }
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            user_cfg = json.load(f)
        defaults.update(user_cfg)
        for key in ("date_of_birth", "pet_name", "maiden_name"):
            if key in user_cfg:
                merged = dict(defaults[key])
                merged.update(user_cfg[key])
                defaults[key] = merged
    return defaults


def normalize(s):
    return s.strip().lower()


class EscapeRoomApp:
    def __init__(self, windowed=False):
        self.cfg = load_config()
        pygame.init()
        pygame.mouse.set_visible(False)

        if windowed:
            size = (self.cfg["windowed_width"], self.cfg["windowed_height"])
            self.screen = pygame.display.set_mode(size)
        else:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

        pygame.display.set_caption("System")

        w, h = self.screen.get_size()
        self.width, self.height = w, h

        # scale fonts relative to screen height
        self.font_question = pygame.font.SysFont("dejavusansmono", max(24, h // 18))
        self.font_input = pygame.font.SysFont("dejavusansmono", max(24, h // 16))
        self.font_big = pygame.font.SysFont("dejavusansmono", max(40, h // 8), bold=True)
        self.font_small = pygame.font.SysFont("dejavusansmono", max(18, h // 30))

        self.clock = pygame.time.Clock()

        self.state = STATE_PASSWORD
        self.buffer = ""
        self.last_key_time = time.time()
        self.expire_seconds = self.cfg.get("expire_seconds", 10)

        self.error_until = 0.0

        self.reset_questions = {
            STATE_DOB: self.cfg["date_of_birth"],
            STATE_PET: self.cfg["pet_name"],
            STATE_MAIDEN: self.cfg["maiden_name"],
        }

        self.cursor_visible = True
        self.cursor_toggle_time = time.time()

    # ---------------------------------------------------------------
    def run(self):
        try:
            while True:
                self.handle_events()
                self.update()
                self.draw()
                self.clock.tick(30)
        except KeyboardInterrupt:
            pass
        finally:
            pygame.quit()

    # ---------------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Ignore window-close requests; this box is meant to be
                # left running until Ctrl+C is sent from a terminal.
                continue

            if event.type == pygame.KEYDOWN:
                self.handle_keydown(event)

    def handle_keydown(self, event):
        if self.state == STATE_CONGRATS:
            return  # nothing to do; wait for Ctrl+C

        # Currently showing an "Incorrect" flash: any key dismisses it early
        if self.error_until and time.time() < self.error_until:
            if event.key not in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return

        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.submit()
            return

        if event.key == pygame.K_BACKSPACE:
            self.buffer = self.buffer[:-1]
            self.last_key_time = time.time()
            return

        if event.key == pygame.K_ESCAPE:
            # Do not allow escape to close/skip anything.
            return

        ch = event.unicode
        if ch and ch.isprintable():
            self.buffer += ch
            self.last_key_time = time.time()

    def submit(self):
        if self.state == STATE_PASSWORD:
            if self.buffer == self.cfg["master_password"]:
                self.buffer = ""
                self.state = RESET_ORDER[0]
            else:
                self.buffer = ""
            return

        if self.state in RESET_ORDER:
            expected = self.reset_questions[self.state]["answer"]
            if normalize(self.buffer) == normalize(expected):
                self.buffer = ""
                idx = RESET_ORDER.index(self.state)
                if idx + 1 < len(RESET_ORDER):
                    self.state = RESET_ORDER[idx + 1]
                else:
                    self.state = STATE_CONGRATS
            else:
                self.buffer = ""
                self.error_until = time.time() + INCORRECT_FLASH_SECONDS

    # ---------------------------------------------------------------
    def update(self):
        now = time.time()

        if self.state == STATE_PASSWORD:
            if self.buffer and (now - self.last_key_time) > self.expire_seconds:
                self.buffer = ""

        if now - self.cursor_toggle_time > 0.5:
            self.cursor_visible = not self.cursor_visible
            self.cursor_toggle_time = now

    # ---------------------------------------------------------------
    def draw(self):
        self.screen.fill(BLACK)

        if self.state == STATE_PASSWORD:
            pass  # completely blank, on purpose

        elif self.state in RESET_ORDER:
            self.draw_reset_question()

        elif self.state == STATE_CONGRATS:
            self.draw_congrats()

        pygame.display.flip()

    def draw_reset_question(self):
        q = self.reset_questions[self.state]["question"]
        showing_error = self.error_until and time.time() < self.error_until

        q_surf = self.font_question.render(q, True, WHITE)
        q_rect = q_surf.get_rect(center=(self.width // 2, self.height // 2 - 60))
        self.screen.blit(q_surf, q_rect)

        if showing_error:
            e_surf = self.font_input.render("Incorrect - try again", True, RED)
            e_rect = e_surf.get_rect(center=(self.width // 2, self.height // 2 + 20))
            self.screen.blit(e_surf, e_rect)
        else:
            display_text = self.buffer + ("_" if self.cursor_visible else " ")
            i_surf = self.font_input.render(display_text, True, GREEN)
            i_rect = i_surf.get_rect(center=(self.width // 2, self.height // 2 + 20))
            self.screen.blit(i_surf, i_rect)

        idx = RESET_ORDER.index(self.state) + 1
        progress = f"Question {idx} of {len(RESET_ORDER)}"
        p_surf = self.font_small.render(progress, True, GRAY)
        p_rect = p_surf.get_rect(center=(self.width // 2, self.height - 60))
        self.screen.blit(p_surf, p_rect)

    def draw_congrats(self):
        msg = self.cfg.get("congrats_message", "ACCESS GRANTED")
        sub = self.cfg.get("congrats_submessage", "Congratulations!")

        m_surf = self.font_big.render(msg, True, GREEN)
        m_rect = m_surf.get_rect(center=(self.width // 2, self.height // 2 - 30))
        self.screen.blit(m_surf, m_rect)

        s_surf = self.font_question.render(sub, True, WHITE)
        s_rect = s_surf.get_rect(center=(self.width // 2, self.height // 2 + 50))
        self.screen.blit(s_surf, s_rect)


def main():
    parser = argparse.ArgumentParser(description="Escape room final challenge")
    parser.add_argument("--windowed", action="store_true", help="Run in a window instead of fullscreen (for testing)")
    args = parser.parse_args()

    app = EscapeRoomApp(windowed=args.windowed)
    app.run()


if __name__ == "__main__":
    main()
