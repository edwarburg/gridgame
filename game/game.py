import random


class Grid(object):
    UP    = (-1,  0)
    DOWN  = ( 1,  0)
    LEFT  = ( 0, -1)
    RIGHT = ( 0,  1)

    DIRECTIONS = [UP, RIGHT, DOWN, LEFT]

    EDGE = -1
    EMPTY = 0

    def __init__(self, width, height):
        self.width = width
        self.height = height

        # Grid has a row/column of Grid.EDGE surrounding the actual values
        # This means there are two kinds of indices for an element: the index where it is in the backing 2D list, and
        # the index as it's presented to clients
        self._grid = self._makegrid(width, height, Grid.EMPTY)

    def _makegrid(self, width, height, initial_value):
        """Initialize the 2D list of cells, filling with initial_value."""
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be greater than 0 (got %s and %s)" % (width, height))

        grid = []
        real_width = width + 2
        blank = [Grid.EDGE for _ in range(real_width)]

        middle = []
        middle.append(Grid.EDGE)
        for j in range(width):
            middle.append(initial_value)
        middle.append(Grid.EDGE)

        grid.append(blank[:])
        for i in range(height):
            grid.append(middle[:])
        grid.append(blank[:])

        return grid

    def get(self, j, i):
        self._range_check(j, i)
        grid_j, grid_i = self._to_grid_indices(j, i)
        return self._grid[grid_j][grid_i]

    def set(self, j, i, it):
        self._range_check(j, i)
        grid_j, grid_i = self._to_grid_indices(j, i)
        self._grid[grid_j][grid_i] = it
        return it

    def _range_check(self, j, i):
        grid_j, grid_i = Grid._to_grid_indices(j, i)
        if not self._on_grid(grid_j, grid_i):
            raise IndexError("invalid index (width = %d, height = %d): (%d, %d) " % (self.height, self.width, j, i))

    def _on_grid(self, j, i):
        """Return True if passed grid indices are within the view grid"""
        return (0 < i <= self.width) and (0 < j <= self.height)

    def cell_values(self):
        """Iterator over cell values."""
        for row in self._rows():
            for cell in row:
                yield cell

    def available_cells(self):
        """Iterator over view indices of available cells."""
        for j, i in self._cell_indices():
            if self._grid[j][i] == Grid.EMPTY:
                yield Grid._to_view_indices(j, i)

    def occupied_cells(self):
        """Iterator over view indices of occupied cells."""
        for j, i in self._cell_indices():
            if self._grid[j][i] != Grid.EMPTY and self._grid[j][i] != Grid.EDGE:
                yield Grid._to_view_indices(j, i)

    def neighbors(self, j, i, directions=DIRECTIONS):
        """Iterator over indices of neighbors."""
        grid_j, grid_i = self._to_grid_indices(j, i)
        for dir_ in directions:
            n_j, n_i = Grid._apply_dir(grid_j, grid_i, dir_)
            if self._on_grid(n_j, n_i):
                yield Grid._to_view_indices(n_j, n_i)

    def _rows(self):
        """Iterator that returns row-wise iterators over cell values."""
        for j in range(1, self.height + 1):
            yield (self._grid[j][i] for i in range(1, self.width + 1))

    def _cell_indices(self):
        """Iterator over cell indices"""
        for j in range(1, self.height + 1):
            for i in range(1, self.width + 1):
                yield (j, i)

    @staticmethod
    def _to_grid_indices(j, i):
        return j + 1, i + 1

    @staticmethod
    def _to_view_indices(j, i):
        return j - 1, i - 1

    @staticmethod
    def _apply_dir(j, i, dir_):
        """Return cell in the passed direction relative to indices"""
        j2, i2 = dir_
        return j + j2, i + i2

    def __str__(self):
        s = ""

        for row in self._rows():
            for cell in row:
                s += "%5d" % cell
            s += "\n"

        return s


class Game(object):
    def __init__(self, width, height, goal, initial_value):
        self.grid = Grid(width, height)
        self.initial_value = initial_value
        self.goal = goal
        self._max = 0

    def start(self):
        for i in range(2):
            self._place_random()

    def slam(self, direction):
        """Perform a "slam" in the given direction.

        A slam encompasses all of the transformations that occur on the board
        when the player moves in a given direction: moving tiles in the direction they chose and combining adjacent
        tiles as needed.
        """
        Game._validate_direction(direction)

        # example algorithm for left slam. translates to right, up, down, etc.
        # for each row:
        #     move all values as far left as they will go
        #     from left to right, combine adjacent equal squares, replacing the one on the left with the doubled value
        #           and the right with empty
        #     move all values as far left as they will go
        params = self._get_params_for_direction(direction)
        self._squash(*params)
        self._combine(*params)
        self._squash(*params)

        self._place_random()
        self._max = max(self.grid.cell_values())

    @staticmethod
    def _validate_direction(direction):
        if direction not in Grid.DIRECTIONS:
            raise ValueError("Invalid direction: " + str(direction))

    def _get_params_for_direction(self, direction):
        """Gets the parameters to _squash and _combine according to the direction the slam is for.

        When iterating across rows, we need to know whether we're going right to left or left to right (start,
        delta). We need to know if our maximum value is relative to width (left/right) or height (up/down). We also
        need to transpose all of our coordinates if we're going up/down, since _squash and _combine are written as
        if they are operating on rows (get_/set_). By transposing at the get/set level, we "trick" the same method into
        handling both row-wise and column-wise operations.
        """
        if direction in (Grid.LEFT, Grid.RIGHT):
            max_ = self.grid.width
            get_ = self.grid.get
            set_ = self.grid.set
        elif direction in (Grid.UP, Grid.DOWN):
            max_ = self.grid.height
            # transpose for up/down
            get_ = lambda j, i : self.grid.get(i, j)
            set_ = lambda j, i, it: self.grid.set(i, j, it)
        else:
            raise ValueError("Invalid direction: " + str(direction))

        if direction in (Grid.LEFT, Grid.UP):
            delta = 1
            start = 0
        elif direction in (Grid.RIGHT, Grid.DOWN):
            delta = -1
            start = max_ - 1
        else:
            raise ValueError("Invalid direction: " + str(direction))

        return start, max_, delta, get_, set_

    @staticmethod
    def _squash(start, max_, delta, get_, set_):
        """Squash all tiles to one side of the grid.

        This transformation moves tiles as far to one side as they will go, but does not combine. eg:

        0 0 0        0 0 0
        0 1 0   ==>  1 0 0
        1 0 1        1 1 0

        for a left squash.
        """
        for row in range(max_):
            curr = last_empty = start

            # Iterates through row, keeping track of the empty spot farthest in the goal direction. Whenever we encounter
            # a non-empty cell, we move it to last_empty and make curr empty.
            while 0 <= curr < max_ and 0 <= last_empty < max_:
                if get_(row, last_empty) == Grid.EMPTY:
                    if get_(row, curr) > 0:
                        set_(row, last_empty, get_(row, curr))
                        set_(row, curr,       Grid.EMPTY)
                        last_empty += delta
                else:
                    last_empty += delta

                curr += delta

    @staticmethod
    def _combine(start, max_, delta, get_, set_):
        """Combine adjacent tiles in the slam direction. May leave empty gaps behind, as it does not re-squash the grid.

        1 1 0 0        2 0 0 0
        1 1 1 1   ==>  2 0 2 0
        1 1 1 0        2 0 1 0

        for a left combine.
        """
        bounds = (lambda x: x < max_ - 1) if start == 0 else (lambda x: x > 0)

        for row in range(max_):
            curr = start

            # Whenever we find two adjacent matching tiles, double curr cell and empty next cell.
            while bounds(curr):
                curr_val = get_(row, curr)
                next_val = get_(row, curr + delta)

                if curr_val != Grid.EMPTY and curr_val == next_val:
                    set_(row, curr,         curr_val * 2)
                    set_(row, curr + delta, Grid.EMPTY)
                    curr += delta * 2 # next is empty, so skip past it
                else:
                    curr += delta

    def is_over(self):
        """Return True if the game is over (either victory or defeat)."""
        return self.goal_met() or not self.any_can_move()

    def any_can_move(self, directions=Grid.DIRECTIONS):
        """Return True if any positions on the board have legal moves available to them."""
        for i in range(self.grid.width):
            for j in range(self.grid.height):
                if self.grid.get(j, i) == Grid.EMPTY or self._position_can_move(j, i, directions):
                    return True

        return False

    def goal_met(self):
        """Return True if the goal value has been met or exceeded on the grid."""
        return self._max >= self.goal

    def _place_random(self):
        """Place initial_value in a random empty cell."""
        try:
            i, j = random.choice(list(self.grid.available_cells()))
        except IndexError: # available_cells() was empty
            return
        self.grid.set(i, j, self.initial_value)


    def _position_can_move(self, j, i, directions):
        """Return True if a given position has anywhere it can legally move."""
        current = self.grid.get(j, i)
        for n_j, n_i in self.grid.neighbors(j, i, directions):
            neighbor_value = self.grid.get(n_j, n_i)
            if neighbor_value == Grid.EMPTY or neighbor_value == current:
                return True

        return False


