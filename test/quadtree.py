from collections import Counter

from numpy import array
from numpy._typing import ArrayLike
from numpy.array_api._array_object import Array


def quadtree_count_2(image, x, y, box_size, level, counter):
    if box_size == 1:
        if image[x][y] > level:
            counter[box_size] = counter.get(box_size, 0) + 1
            return 1
        return 0
    else:
        half_box_size = box_size // 2
        x1 = x + half_box_size
        y1 = y + half_box_size
        # Recursively count the number of boxes that contain at least one non-zero pixel
        count = sum([quadtree_count_2(image, x, y, half_box_size, level, counter),
                     quadtree_count_2(image, x, y1, half_box_size, level, counter),
                     quadtree_count_2(image, x1, y, half_box_size, level, counter),
                     quadtree_count_2(image, x1, y1, half_box_size, level, counter)])
        if count > 0:
            counter[box_size] = counter.get(box_size, 0) + 1
            return 1
        return 0


def quadtree_count_iterative(image, box_size, level):
    stack = [(0, 0, box_size)]
    counter = Counter()
    while stack:
        x, y, box_size = stack.pop()
        if box_size == 1:
            if image[x][y] > level:
                counter[box_size] = counter.get(box_size, 0) + 1
        else:
            half_box_size = box_size // 2
            x1, y1 = x + half_box_size, y + half_box_size
            # Push sub-boxes onto the stack
            stack.append((x, y, half_box_size))
            stack.append((x, y1, half_box_size))
            stack.append((x1, y, half_box_size))
            stack.append((x1, y1, half_box_size))
    return counter

def quadtree_count_iterative_2(image: Array, level):
    stack = [0]
    counter = Counter()
    box_size = 1
    size = image.shape[0]
    assert size == image.shape[1]
    while stack:
        for x in range(0, size, box_size):
            for y in range(0, size, box_size):
                if image[x][y] > level:
                    b = box_size
                    while b < size:
                        counter[b] += 1
                        b *= 2
    return counter