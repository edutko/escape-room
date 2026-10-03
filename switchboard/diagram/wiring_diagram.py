#!/usr/bin/env python3

GAP_X, GAP_Y = 40, 40  # gap between rectangles
MARGIN = 40  # outer margin

CIRCLE_R = 30  # circle radius
CIRCLE_PAD_X = 20  # padding inside rect (left/right)
CIRCLE_PAD_Y = 20  # padding inside rect (top/bottom)

BACKGROUND_FILL = 'none'

RECT_FILL = 'none'
RECT_STROKE = '#000000'
RECT_STROKE_W = 2
RECT_RX = 8  # corner radius

CIRCLE_FILL_EMPTY = 'none'
CIRCLE_STROKE = '#000000'
CIRCLE_STROKE_W = 2
WIRE_W = round(CIRCLE_R / 2.0, 1)
DEFAULT_WIRE_COLORS = [
    '#ff4444', '#44aaff', '#44ff88', '#ffaa00',
    '#ff44ff', '#00ffff', '#ffff44', '#ff8844',
]


class SwitchboardDiagram(object):
    def __init__(self, group_cols=4, group_rows=2, terminal_cols=2, terminal_rows=3, wire_colors=None):
        self._group_cols = group_cols
        self._group_rows = group_rows
        self._terminal_cols = terminal_cols
        self._terminal_rows = terminal_rows
        self._rect_w = CIRCLE_R * 2 * terminal_cols + CIRCLE_PAD_Y * (terminal_cols + 1)
        self._rect_h = CIRCLE_R * 2 * terminal_rows + CIRCLE_PAD_Y * (terminal_rows + 1)
        self._wire_colors = wire_colors if wire_colors is not None else DEFAULT_WIRE_COLORS

    def _rect_origin(self, rect_idx):
        col = rect_idx % self._group_cols
        row = rect_idx // self._group_cols
        x = MARGIN + col * (self._rect_w + GAP_X)
        y = MARGIN + row * (self._rect_h + GAP_Y)
        return x, y

    def _circle_center(self, rect_idx, circle_idx):
        rx, ry = self._rect_origin(rect_idx)

        col = circle_idx % self._terminal_cols
        row = circle_idx // self._terminal_cols

        cx = rx + (CIRCLE_PAD_X + CIRCLE_R * 2) * col + CIRCLE_PAD_X + CIRCLE_R
        cy = ry + (CIRCLE_PAD_Y + CIRCLE_R * 2) * row + CIRCLE_PAD_Y + CIRCLE_R
        return cx, cy

    def _svg_rect(self, rect_idx):
        x, y = self._rect_origin(rect_idx)
        return (
            f'  <rect x="{x}" y="{y}" width="{self._rect_w}" height="{self._rect_h}" '
            f'rx="{RECT_RX}" '
            f'fill="{RECT_FILL}" stroke="{RECT_STROKE}" stroke-width="{RECT_STROKE_W}"/>'
        )

    def _svg_empty_circle(self, rect_idx, circle_idx):
        cx, cy = self._circle_center(rect_idx, circle_idx)
        return (
            f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{CIRCLE_R}" '
            f'fill="{CIRCLE_FILL_EMPTY}" stroke="{CIRCLE_STROKE}" stroke-width="{CIRCLE_STROKE_W}"/>'
        )

    def _svg_filled_circle(self, rect_idx, circle_idx, color):
        cx, cy = self._circle_center(rect_idx, circle_idx)
        return (
            f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{CIRCLE_R}" '
            f'fill="{color}" stroke="{color}" stroke-width="{CIRCLE_STROKE_W}" opacity="1.0"/>'
        )

    def _svg_wire(self, rect_a, circle_a, rect_b, circle_b, color):
        x1, y1 = self._circle_center(rect_a, circle_a)
        x2, y2 = self._circle_center(rect_b, circle_b)
        # Simple curved wire using a cubic bezier
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        bend = max(dx, dy) * 0.1
        cx1, cy1 = x1, y1 - bend
        cx2, cy2 = x2, y2 - bend
        return (
            f'  <path d="M {x1:.1f},{y1:.1f} C {cx1:.1f},{cy1:.1f} {cx2:.1f},{cy2:.1f} {x2:.1f},{y2:.1f}" '
            f'fill="none" stroke="{color}" stroke-width="{WIRE_W}" '
            f'stroke-opacity="1.0" stroke-linecap="round"/>'
        )

    def reverse(self, p):
        gc = self._group_cols - (p[0] % self._group_cols) - 1
        gr = p[0] // self._group_cols
        tc = self._terminal_cols - (p[1] % self._terminal_cols) - 1
        tr = p[1] // self._terminal_cols
        return gc + gr * self._group_cols, tc + tr * self._terminal_cols

    def draw(self, output_file: str, connections: list, ends=None, reverse=False, monochrome=False):
        if reverse:
            rev_conn = []
            for conn in connections:
                a, b = conn
                ra = self.reverse(a)
                rb = self.reverse(b)
                # print(f'({a}, {b}) -> ({ra}, {rb})')
                rev_conn.append((ra, rb))
            connections = rev_conn

            rev_ends = []
            for end in ends:
                re = self.reverse(end)
                rev_ends.append(re)
            ends = rev_ends

        wire_colors = ['#999999'] if monochrome else self._wire_colors

        total_w = MARGIN * 2 + self._group_cols * self._rect_w + (self._group_cols - 1) * GAP_X
        total_h = MARGIN * 2 + self._group_rows * self._rect_h + (self._group_rows - 1) * GAP_Y

        # Which circles are filled, and what colour
        filled = {}  # (rect_idx, circle_idx) -> color
        for i, ((ra, ca), (rb, cb)) in enumerate(connections):
            color = wire_colors[i % len(wire_colors)]
            filled[(ra, ca)] = color
            filled[(rb, cb)] = color

        if ends is not None:
            for i, (ra, ca) in enumerate(ends):
                color = wire_colors[i % len(wire_colors)]
                filled[(ra, ca)] = color

        lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{total_h}" fill="{BACKGROUND_FILL}">', '']

        lines.append("  <!-- Rectangles -->")
        for r in range(self._group_rows * self._group_cols):
            lines.append(self._svg_rect(r))
        lines.append("")

        # Empty circles first (so wires and filled circles render on top)
        lines.append("  <!-- Empty circles -->")
        for r in range(self._group_rows * self._group_cols):
            for c in range(self._terminal_rows * self._terminal_cols):
                if (r, c) not in filled:
                    lines.append(self._svg_empty_circle(r, c))
        lines.append("")

        lines.append("  <!-- Wires -->")
        for i, ((ra, ca), (rb, cb)) in enumerate(connections):
            color = wire_colors[i % len(wire_colors)]
            lines.append(self._svg_wire(ra, ca, rb, cb, color))
        lines.append("")

        # Filled circles go on top of wires
        lines.append("  <!-- Filled circles -->")
        for (r, c), color in filled.items():
            lines.append(self._svg_filled_circle(r, c, color))
        lines.append("")

        lines.append("</svg>")

        svg_text = "\n".join(lines)
        with open(output_file, "w") as f:
            f.write(svg_text)
        return svg_text
