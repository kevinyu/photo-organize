import numpy as np


def line2d_seg_dist(p1, p2, p0):
    """distance(s) from line defined by p1 - p2 to point(s) p0

    p0[0] = x(s)
    p0[1] = y(s)

    intersection point p = p1 + u*(p2-p1)
    and intersection point lies within segment if u is between 0 and 1

    from matplotlib < 3.1
    """

    x21 = p2[0] - p1[0]
    y21 = p2[1] - p1[1]
    x01 = np.asarray(p0[0]) - p1[0]
    y01 = np.asarray(p0[1]) - p1[1]

    u = (x01*x21 + y01*y21) / (x21**2 + y21**2)
    u = np.clip(u, 0, 1)
    d = np.hypot(x01 - u*x21, y01 - u*y21)

    return d

