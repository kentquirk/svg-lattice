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

