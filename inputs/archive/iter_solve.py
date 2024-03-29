import numpy as np
from src import var

params = var.obj()

params.fn_grid = "/home/ray/git-projects/spec_appx/data/icon_compact.nc"
params.fn_topo = "/home/ray/git-projects/spec_appx/data/topo_compact.nc"

params.merit_cg = 10
params.merit_path = "/home/ray/Documents/orog_data/MERIT/"

params.output_fn = "test_selected"

params.lat_extent = [52.0, 64.0, 64.0]
params.lon_extent = [-141.0, -158.0, -127.0]

params.delaunay_xnp = 16
params.delaunay_ynp = 11
params.rect_set = np.sort([156, 154, 32, 72, 68, 160, 96, 162, 276, 60])
# rect_set = np.sort([52,62,110,280,296,298,178,276,244,242])
# rect_set = np.sort([276])


# MERIT 8x coarse-graining corresponding selected rect set (approx USGS GMTED2010 resolution).
# params.rect_set = np.sort([188, 204, 280, 102, 78, 162, 160, 146, 106, 164])
params.rect_set = np.sort([156, 152, 130, 78, 20, 174, 176, 64, 86, 228])


# MERIT 10x coarse-graining corresponding selected rect set (better approximation of the USGS GMTED2010 resolution).
params.rect_set = np.sort([66, 182, 20, 216, 246, 244, 240, 152, 278, 22])

# all the main MERIT x10 offenders. To test implementation of correction strategy.
# params.rect_set = [20, 66, 182, 240]
# params.rect_set = [182]

# MERIT full LAM top underestimators AFTER correction... Why does correction not work?
# params.rect_set = np.sort([98, 210, 286, 80, 266])

# MERIT full LAM top overestimators AFTER correction
# params.rect_set = np.sort([0, 6, 212, 84, 174])
# params.rect_set = np.sort([212, 174])

params.lxkm, params.lykm = 120, 120

# Setup the Fourier parameters and object.
params.nhi = 24
params.nhj = 48

params.n_modes = 100

params.U, params.V = 10.0, 0.1

params.cg_spsp = False  # coarse grain the spectral space?
params.rect = False if params.cg_spsp else True

params.lmbda_fg = 0.0
params.lmbda_sg = 0.0

params.tapering = True
params.taper_first = False
params.taper_full_fg = False
params.taper_second = True
params.taper_both = False

params.rect = False
params.padding = 50

params.debug = False
params.debug_writer = True
params.dfft_first_guess = False

params.no_corrections = True
params.refine = False

params.verbose = False
params.plot = True
