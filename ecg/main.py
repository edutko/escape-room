#!/usr/bin/env python3
"""
ECG Monitor — pygame framebuffer version
Escape room prop. Runs on bare Debian 12, no desktop environment.
"""

import math, random, signal, subprocess, sys, time
import pygame

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

BASE_BPM   = 60
SPO2       = 98.0
TEMP_C     = 36.8
SYSTOLIC   = 118
DIASTOLIC  = 76
RESP_RATE  = 16

TARGET_FPS = 25

# Colors  (R, G, B)
BG          = (  2,   8,   2)   # near-black with green tint
GRID        = ( 10,  35,  10)   # very dark green grid
TRACE_CORE  = ( 57, 255,  57)   # bright phosphor green
TRACE_GLOW1 = ( 20, 180,  20)   # mid glow
TRACE_GLOW2 = (  8,  80,   8)   # outer glow
PANEL_BG    = (  4,  15,   4)
PANEL_BORDER= ( 20,  80,  20)
LABEL_DIM   = ( 60, 120,  60)
VALUE_GREEN = ( 80, 255,  80)
VALUE_CYAN  = ( 80, 230, 230)
VALUE_RED   = (255,  70,  70)
VALUE_WHITE = (200, 220, 200)
SEPARATOR   = ( 15,  50,  15)


def ecg_value(t):
    t = t % 1.0
    v = 0.0
    v += 0.03 * math.sin(2 * math.pi * t * 0.5)          # baseline wander
    v += 0.18 * math.exp(-((t - 0.18) ** 2) / 0.0018)    # P wave
    v -= 0.12 * math.exp(-((t - 0.31) ** 2) / 0.0004)    # Q dip
    v += 1.00 * math.exp(-((t - 0.34) ** 2) / 0.00025)   # R spike
    v -= 0.22 * math.exp(-((t - 0.37) ** 2) / 0.0004)    # S dip
    v += 0.04 * math.exp(-((t - 0.45) ** 2) / 0.005)     # ST elevation
    v += 0.28 * math.exp(-((t - 0.58) ** 2) / 0.0045)    # T wave
    return v


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def draw_aa_line(surf, col, p1, p2, width=2):
    """Anti-aliased line; falls back gracefully for width > 1."""
    pygame.draw.aaline(surf, col, p1, p2)
    if width > 1:
        # draw extra parallel lines offset by 1px for thickness
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length == 0:
            return
        nx, ny = -dy / length, dx / length   # normal vector
        for off in range(1, width):
            ox, oy = nx * off, ny * off
            pygame.draw.aaline(surf, col,
                               (p1[0] + ox, p1[1] + oy),
                               (p2[0] + ox, p2[1] + oy))
            pygame.draw.aaline(surf, col,
                               (p1[0] - ox, p1[1] - oy),
                               (p2[0] - ox, p2[1] - oy))


def draw_glow_trace(surf, points, glow_surf):
    """
    Draw the ECG trace with three-layer glow:
      outer glow → mid glow → bright core
    Uses a dedicated surface for the blurred glow layers.
    """
    if len(points) < 2:
        return

    # Outer glow (wide, dark)
    glow_surf.fill((0, 0, 0, 0))
    for i in range(1, len(points)):
        draw_aa_line(glow_surf, TRACE_GLOW2, points[i-1], points[i], width=6)
    surf.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    # Mid glow
    glow_surf.fill((0, 0, 0, 0))
    for i in range(1, len(points)):
        draw_aa_line(glow_surf, TRACE_GLOW1, points[i-1], points[i], width=3)
    surf.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    # Core (bright, thin, anti-aliased)
    for i in range(1, len(points)):
        pygame.draw.aaline(surf, TRACE_CORE, points[i-1], points[i])


def draw_grid(surf, rect, cell_px=40):
    """Draw a faint ECG-style grid inside rect."""
    x0, y0, w, h = rect
    for x in range(x0, x0 + w, cell_px):
        pygame.draw.line(surf, GRID, (x, y0), (x, y0 + h))
    for y in range(y0, y0 + h, cell_px):
        pygame.draw.line(surf, GRID, (x0, y0 + y - y0), (x0 + w, y0 + y - y0))
    # Slightly brighter major gridlines every 5 cells
    major = GRID[0] * 3, GRID[1] * 3, GRID[2] * 3
    for x in range(x0, x0 + w, cell_px * 5):
        pygame.draw.line(surf, major, (x, y0), (x, y0 + h))
    for y in range(y0, y0 + h, cell_px * 5):
        pygame.draw.line(surf, major, (x0, y0 + y - y0), (x0 + w, y0 + y - y0))


def draw_panel_box(surf, rect, title, font_sm):
    x, y, w, h = rect
    pygame.draw.rect(surf, PANEL_BG,    rect)
    pygame.draw.rect(surf, PANEL_BORDER, rect, 1)
    # Title bar
    title_surf = font_sm.render(title, True, LABEL_DIM)
    surf.blit(title_surf, (x + 8, y + 6))
    pygame.draw.line(surf, PANEL_BORDER, (x, y + 28), (x + w, y + 28), 1)


def draw_vital(surf, x, y, label, value_str, unit_str, value_col,
               font_sm, font_lg):
    """Draw one vital-sign block: label / big value / unit."""
    lbl  = font_sm.render(label,      True, LABEL_DIM)
    val  = font_lg.render(value_str,  True, value_col)
    unt  = font_sm.render(unit_str,   True, LABEL_DIM)
    surf.blit(lbl, (x, y))
    surf.blit(val, (x, y + 20))
    surf.blit(unt, (x + val.get_width() + 5, y + 28))


def eject_cd():
    try:
        subprocess.Popen(['/usr/bin/eject'])
    except Exception:
        pass


def main():
    pygame.display.init()   # must come before Info() or set_mode()
    pygame.font.init()
    pygame.mixer.quit()     # no audio needed; skip to avoid driver errors

    try:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME)
    except Exception:
        screen = pygame.display.set_mode((1280, 720))

    W, H = screen.get_size()

    pygame.display.set_caption("ECG Monitor")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    # ── Fonts ─────────────────────────────────────────────────────────────────
    font_path = pygame.font.match_font("dejavusansmono,liberationmono,freemono")
    font_sm  = pygame.font.Font(font_path, 16)
    font_md  = pygame.font.Font(font_path, 22)
    font_lg  = pygame.font.Font(font_path, 42)
    font_xl  = pygame.font.Font(font_path, 28)

    # ── Layout ────────────────────────────────────────────────────────────────
    HEADER_H  = 50
    FOOTER_H  = 36
    PANEL_W   = 220
    PADDING   = 12

    graph_x = PADDING
    graph_y = HEADER_H + PADDING
    graph_w = W - PANEL_W - PADDING * 3
    graph_h = H - HEADER_H - FOOTER_H - PADDING * 2

    panel_x = W - PANEL_W - PADDING
    panel_y = HEADER_H + PADDING

    # Glow surface (same size as screen, blended additively)
    glow_surf = pygame.Surface((W, H))
    glow_surf.set_colorkey((0, 0, 0))

    # ── State ─────────────────────────────────────────────────────────────────
    t           = 0.0
    bpm         = float(BASE_BPM)
    spo2        = float(SPO2)
    temp        = float(TEMP_C)
    sys_bp      = float(SYSTOLIC)
    dia_bp      = float(DIASTOLIC)
    resp        = float(RESP_RATE)
    bpm_target  = bpm

    # Pixel-level waveform history — one entry per horizontal pixel in graph
    num_samples = graph_w
    history     = [0.0] * num_samples

    last_beat_t  = 0.0
    last_drift   = time.time()
    start_wall   = time.time()

    # ── Main loop ─────────────────────────────────────────────────────────────
    def _quit(signum, frame):
        global running
        running = False
    signal.signal(signal.SIGTERM, _quit)
    signal.signal(signal.SIGINT, _quit)

    global running
    running = True
    while running:
        dt = clock.tick(TARGET_FPS) / 1000.0   # seconds since last frame
        now = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_CTRL and event.key == pygame.K_c:
                    running = False
                elif mods & pygame.KMOD_CTRL and mods & pygame.KMOD_SHIFT and event.key == pygame.K_e:
                    eject_cd()

        if now - last_drift > 4.0:
            bpm_target = BASE_BPM + random.uniform(-3, 3)
            spo2       = clamp(SPO2  + random.uniform(-0.5, 0.5), 95, 100)
            sys_bp     = clamp(SYSTOLIC  + random.uniform(-4, 4), 100, 140)
            dia_bp     = clamp(DIASTOLIC + random.uniform(-3, 3), 60,  90)
            resp       = clamp(RESP_RATE + random.uniform(-1, 1), 12,  22)
            last_drift = now

        bpm += (bpm_target - bpm) * 0.02
        beat_period = 60.0 / bpm

        # Advance phase — scroll by however many pixels represent dt seconds
        # At 25 mm/s and ~3.5 px/mm that's ~87.5 px/s; we use graph_w / (beat_period * 2.5)
        pixels_per_sec = graph_w / (beat_period * 2.8)
        pixels_this_frame = pixels_per_sec * dt
        steps = max(1, int(round(pixels_this_frame)))

        for _ in range(steps):
            t += (1.0 / beat_period) / (pixels_per_sec if pixels_per_sec > 0 else 1)
            raw = ecg_value(t) + random.gauss(0, 0.006)
            history.append(raw)

        history = history[-num_samples:]

        # Beep on R-peak crossing
        beat_phase = t % 1.0
        if 0.33 <= beat_phase <= 0.36 and (t - last_beat_t) > 0.5:
            # pygame beep via simple tone synthesis would need numpy;
            # fall back to terminal bell which works on fbcon too
            sys.stdout.write('\a')
            sys.stdout.flush()
            last_beat_t = t

        # ─── Draw ─────────────────────────────────────────────────────────────
        screen.fill(BG)

        # Grid
        draw_grid(screen, (graph_x, graph_y, graph_w, graph_h), cell_px=40)

        # ── Convert history → pixel coords
        mid_y  = graph_y + graph_h // 2
        scale  = graph_h * 0.36   # R-peak reaches ~36% of half-height

        points = []
        for xi, v in enumerate(history):
            px = graph_x + xi
            py = int(mid_y - v * scale)
            py = clamp(py, graph_y + 2, graph_y + graph_h - 2)
            points.append((px, py))

        draw_glow_trace(screen, points, glow_surf)

        pygame.draw.line(screen, GRID,
                         (graph_x, mid_y), (graph_x + graph_w, mid_y), 1)

        # ── Header ────────────────────────────────────────────────────────────
        pygame.draw.rect(screen, PANEL_BG, (0, 0, W, HEADER_H))
        pygame.draw.line(screen, PANEL_BORDER, (0, HEADER_H - 1), (W, HEADER_H - 1), 1)

        title = font_xl.render("♥  CARDIOSCOPE III  —  PATIENT MONITOR", True, VALUE_CYAN)
        screen.blit(title, (PADDING, (HEADER_H - title.get_height()) // 2))

        elapsed  = int(now - start_wall)
        hh, rem  = divmod(elapsed, 3600)
        mm, ss   = divmod(rem, 60)
        time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"
        ts       = font_md.render(time_str, True, LABEL_DIM)
        screen.blit(ts, (W - ts.get_width() - PADDING,
                         (HEADER_H - ts.get_height()) // 2))

        # ── Vitals panel ──────────────────────────────────────────────────────
        panel_h = H - HEADER_H - FOOTER_H - PADDING * 2
        draw_panel_box(screen, (panel_x, panel_y, PANEL_W, panel_h),
                       "VITAL SIGNS", font_sm)

        vy = panel_y + 38
        vpad = 12

        def vital_block(label, val_str, unit, col):
            nonlocal vy
            draw_vital(screen, panel_x + 10, vy,
                       label, val_str, unit, col, font_sm, font_lg)
            vy += font_lg.get_height() + 20 + vpad
            pygame.draw.line(screen, SEPARATOR,
                             (panel_x + 6, vy - vpad),
                             (panel_x + PANEL_W - 6, vy - vpad), 1)

        vital_block("HEART RATE",   f"{int(round(bpm))}",         "bpm",    VALUE_RED)
        vital_block("SpO\u2082",    f"{spo2:.1f}",                "%",      VALUE_GREEN)
        vital_block("NIBP",         f"{int(sys_bp)}/{int(dia_bp)}","mmHg",  VALUE_CYAN)
        vital_block("TEMP",         f"{temp:.1f}",                "\u00b0C",VALUE_WHITE)
        vital_block("RESP",         f"{int(round(resp))}",        "br/min", VALUE_GREEN)

        # Lead / speed / gain labels
        meta = font_sm.render("Lead II   25 mm/s   10 mm/mV", True, LABEL_DIM)
        screen.blit(meta, (panel_x + 6, panel_y + panel_h - 24))

        # ── Footer ────────────────────────────────────────────────────────────
        fy = H - FOOTER_H
        pygame.draw.rect(screen, PANEL_BG, (0, fy, W, FOOTER_H))
        pygame.draw.line(screen, PANEL_BORDER, (0, fy), (W, fy), 1)

        fps_str  = f"FPS: {clock.get_fps():.0f}"
        fps_surf = font_sm.render(fps_str, True, GRID)
        screen.blit(fps_surf, (W - fps_surf.get_width() - PADDING,
                               fy + (FOOTER_H - fps_surf.get_height()) // 2))

        footer_txt = font_sm.render(
            "CONTINUOUS CARDIAC MONITORING  |  ALARM LIMITS: HR 50-120  SpO\u2082 >94%",
            True, LABEL_DIM)
        screen.blit(footer_txt, (PADDING, fy + (FOOTER_H - footer_txt.get_height()) // 2))

        pygame.display.flip()

    try:
        screen.fill((0, 0, 0))
        pygame.display.flip()
    except Exception:
        pass

    pygame.display.quit()
    time.sleep(0.2)
    pygame.quit()

running = False

if __name__ == "__main__":
    main()
