# Lattice Generator

This program is a lattice generator.

It starts with an grid, then seeds the grid with a number of randomly-placed starting points. Each of these will be the seed
for a neighborhood.

It then iterates, choosing random grid elements; for each empty one it finds, it tries to connect it to a neighboring full one. It continues until it finds too many full squares, after which it switches to an iterative search.

The result is a grid where every square is full, and most (or all) of them are connected to some neighborhood of other squares. The
neighbors, however, are disjoint.

If you use only one neighborhood, the algorithm generates a "perfect" maze (a maze that connects every square in the grid without loops).

Once the grid is generated, it turns it into an SVG file where each neighborhood is drawn with a single continuous outline stroke.
This svg is intended for use with a laser cutter (or other vector plotting device).

To run it, check out this repository, make sure you have a relatively recent 3.x version of python, and run it with

`python3 lattice.py` and your choice of arguments (see below).

Help:

```
usage: lattice.py [-h] [--width WIDTH] [--height HEIGHT] [--cellsize CELLSIZE] [--bordersize BORDERSIZE] [--n N] [--seed SEED] [--printboard] [--filename FILENAME] [--fillcolor FILLCOLOR] [--nosolo] [--style {wide,medium,thin}]

Generate a lattice.

optional arguments:
  -h, --help            show this help message and exit
  --width WIDTH         the number of lattice cells horizontally
  --height HEIGHT       the number of lattice cells vertically
  --cellsize CELLSIZE   the size of each cell in mm
  --bordersize BORDERSIZE
                        the size of the border in mm
  --n N                 the number of neighborhoods to use (default is area/5)
  --seed SEED           a seed for randomness (default time.now)
  --printboard          ascii-print the board after generation
  --filename FILENAME   filename in which to store the resulting svg (lattice.svg)
  --fillcolor FILLCOLOR
                        fill color of the strokes (none)
  --nosolo              don't allow neighborhoods of only one cell
  --style {wide,medium,thin}
                        style of the strokes
```