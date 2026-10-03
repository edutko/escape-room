import random
from random import shuffle

from wiring_diagram import SwitchboardDiagram

all_groups = [i for i in range(8)]
num_points_per_group = 6


def random_groups():
    groups = [i for i in all_groups]
    shuffle(groups)
    return groups


def generate_route(num_wires: int):
    groups = random_groups()
    for i in range(num_wires * 2):
        yield groups[0], random.randint(0, num_points_per_group - 1)
        groups = groups[1:]
        if len(groups) == 0:
            groups = random_groups()


if __name__ == '__main__':
    points = list(generate_route(4))
    front_wires = list(zip(points[::2], points[1::2]))
    back_wires = list(zip(points[1::2], points[2::2]))
    back_ends = [points[0], points[-1]]

    d = SwitchboardDiagram()
    d.draw('front.svg', front_wires, monochrome=True)
    d.draw('back.svg', back_wires, back_ends, reverse=True, monochrome=True)
