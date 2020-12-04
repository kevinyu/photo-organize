import datetime
import numpy as np


class CalendarMonthGrid(object):
    """Object for creating and storing month data as a grid

    We want to go from the convenient representation (int)day
    to a position in a 7xn grid ((int)row, (int)col)
    """
    def __init__(
                self,
                month,
                year=1980,
                default=None,
                null=None,
                dtype=np.object,
            ):
        self.month = month
        self.dtype = dtype
        self.default = default
        self.null = null

        first_day = datetime.date(year, month, 1)

        mapping = {}
        curr_row = 0
        curr_day = first_day
        while curr_day.month == month:
            mapping[curr_day.day] = curr_row, curr_day.weekday()
            curr_day += datetime.timedelta(days=1)
            if curr_day.weekday() == 0:
                curr_row += 1

        self.mapping = mapping
        self._inverse_lookup = dict([(val, key) for key, val in mapping.items()])
        print(self._inverse_lookup)
        self.dimensions = (np.max([x[0] for x in mapping.values()]) + 1, 7)

        self._init_grid()

    def _init_grid(self):
        self.grid = np.full(self.dimensions, self.null, dtype=self.dtype)
        for key in self.mapping.keys():
            self.set(key, self.default)

    def set(self, day, val):
        row, col = self.mapping[day]
        self.grid[row][col] = val
        return self.grid[row][col]

    def clear(self, day):
        row, col = self.mapping[day]
        self.grid[row][col] = self.default
        return self.grid[row][col]

    def get(self, day):
        row, col = self.mapping[day]
        return self.grid[row][col]

    def reverse(self, row, col):
        return self._inverse_lookup.get((row, col))

    def prepare_3d(self):
        """Prepare grid data for 3-d plotting"""
        n = len(self.mapping)
        X = np.zeros(n)
        Y = np.zeros(n)
        Z = np.full(n, self.default, dtype=self.dtype)
        for i, (row, col) in enumerate(self.mapping.values()):
            X[i] = row
            Y[i] = col
            Z[i] = self.grid[row][col]

        return X, Y, Z

    def iter_coordinates(self):
        """Iterate over days and coordinate pairs

        Iterates over each day of the month in order,
        yielding (int)day, ((int)row, (int) col)
        """
        return sorted(self.mapping.items())

