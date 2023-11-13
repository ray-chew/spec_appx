# %%
import sys
import os
# set system path to find local modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pandas as pd
import importlib
import matplotlib.pyplot as plt

from src import io, var, utils, fourier, physics, delaunay
from runs import interface, diagnostics
from vis import plotter, cart_plot

%load_ext autoreload
%autoreload

# %%
# from runs.lam_run import params
from runs.selected_run_dfft import params
# from runs.debug_run import params
from copy import deepcopy

# print run parameters, for sanity check.
if params.self_test():
    params.print()

# %%
# initialise data objects
grid = var.grid()
topo = var.topo_cell()

# read grid
reader = io.ncdata(padding=params.padding, padding_tol=(60-params.padding))
reader.read_dat(params.fn_grid, grid)
grid.apply_f(utils.rad2deg) 

# writer object
writer = io.writer(params.output_fn, params.rect_set, debug=params.debug_writer)

# we only keep the topography that is inside this lat-lon extent.
lat_verts = np.array(params.lat_extent)
lon_verts = np.array(params.lon_extent)

# read topography
if not params.enable_merit:
    reader.read_dat(params.fn_topo, topo)
    reader.read_topo(topo, topo, lon_verts, lat_verts)
else:
    reader.read_merit_topo(topo, params)
    topo.topo[np.where(topo.topo < -500.0)] = -500.0

topo.gen_mgrids()

tri = delaunay.get_decomposition(topo, xnp=params.delaunay_xnp, ynp=params.delaunay_ynp, padding = reader.padding)
writer.write_all('decomposition', tri)
writer.populate('decomposition', 'rect_set', params.rect_set)


# %%
if params.run_full_land_model:
    params.rect_set = delaunay.get_land_cells(tri, topo, height_tol=0.5)
    print(params.rect_set)

params_orig = deepcopy(params)
writer.write_all_attrs(params)

# %%
# Plot the loaded topography...
%autoreload
# cart_plot.lat_lon(topo, int=1)

levels = np.linspace(-500.0, 3500.0, 9)
cart_plot.lat_lon_delaunay(topo, tri, levels, label_idxs=True, fs=(20,12), highlight_indices=params.rect_set, output_fig=True, fn='../manuscript/delaunay.pdf', int=1, raster=True)

# %%
# del topo.lat_grid
# del topo.lon_grid

# %%
%autoreload

nhi = params.nhi
nhj = params.nhj

fa = interface.first_appx(nhi, nhj, params, topo)
sa = interface.second_appx(nhi, nhj, params, topo, tri)
# diagnostics object
diag = diagnostics.delaunay_metrics(params, tri, writer=writer)
dplot = diagnostics.diag_plotter(params, nhi, nhj)

if not params.no_corrections:
    rel_errs_orig = []

for rect_idx in params.rect_set:

    #################################################
    #
    # compute DFFT over reference quadrilateral cell.
    #
    print("computing reference quadrilateral cell: ", (rect_idx, rect_idx+1))

    cell_ref = var.topo_cell()
    
    simplex_lat = tri.tri_lat_verts[rect_idx]
    simplex_lon = tri.tri_lon_verts[rect_idx]

    if params.taper_ref:
        interface.taper_quad(params, simplex_lat, simplex_lon, cell_ref, topo)
    else:
        utils.get_lat_lon_segments(simplex_lat, simplex_lon, cell_ref, topo, rect=params.rect)    

    ref_run = interface.get_pmf(nhi,nhj,params.U,params.V)
    ampls_ref, uw_ref, fft_2D_ref, kls_ref = ref_run.dfft(cell_ref)

    if params.debug_writer:
        writer.populate(rect_idx, 'topo_ref', cell_ref.topo)
        writer.populate(rect_idx, 'spectrum_ref', ampls_ref)
        writer.populate(rect_idx, 'pmf_ref', uw_ref)

    v_extent = [fft_2D_ref.min(), fft_2D_ref.max()]
    sols = (cell_ref, ampls_ref, uw_ref, fft_2D_ref)
    dplot.show(rect_idx, sols, kls=kls_ref, v_extent = v_extent, dfft_plot=True)

    # if params.plot:
    #     fs = (15,5.0)
    #     fig, axs = plt.subplots(1,3, figsize=fs)
    #     fig_obj = plotter.fig_obj(fig, nhi, nhj)
    #     axs[0] = fig_obj.phys_panel(axs[0], fft_2D_ref, title='T%i + T%i: Reference FFT reconstruction' %(rect_idx, rect_idx+1), xlabel='longitude [km]', ylabel='latitude [km]', extent=[cell_ref.lon.min(), cell_ref.lon.max(), cell_ref.lat.min(), cell_ref.lat.max()], v_extent=v_extent)

    #     axs[1] = fig_obj.fft_freq_panel(axs[1], ampls_ref, kls_ref[0], kls_ref[1], typ='real')
    #     axs[2] = fig_obj.fft_freq_panel(axs[2], uw_ref, kls_ref[0], kls_ref[1], title="FFT PMF spectrum", typ='real')
    #     plt.tight_layout()
    #     plt.show()


    ###################################
    #
    # Do first approximation
    # 
    if params.dfft_first_guess:
        nhi = len(cell_ref.lon)
        nhj = len(cell_ref.lat)

        ampls_fa, uw_fa, dat_2D_fa, kls_fa = np.copy(ampls_ref), np.copy(uw_ref), np.copy(fft_2D_ref), np.copy(kls_ref)

        cell_fa = cell_ref
    else:
        cell_fa, ampls_fa, uw_fa, dat_2D_fa = fa.do(simplex_lat, simplex_lon)

    diag.update_quad(rect_idx, uw_ref, uw_fa)

    if params.debug_writer:
        writer.populate(rect_idx, 'spectrum_fg', ampls_fa)
        writer.populate(rect_idx, 'recon_fg', dat_2D_fa)
        writer.populate(rect_idx, 'pmf_fg', uw_fa)

    sols = (cell_fa, ampls_fa, uw_fa, dat_2D_fa)
    dplot.show(rect_idx, sols, v_extent=v_extent)

    # if params.plot:
    #     fs = (15.0,4.0)
    #     fig, axs = plt.subplots(1,3, figsize=fs)
    #     fig_obj = plotter.fig_obj(fig, nhi, nhj)
    #     axs[0] = fig_obj.phys_panel(axs[0], dat_2D_fa, title='T%i+T%i: FF reconstruction' %(rect_idx,rect_idx+1), xlabel='longitude [km]', ylabel='latitude [km]', extent=[cell_fa.lon.min(), cell_fa.lon.max(), cell_fa.lat.min(), cell_fa.lat.max()], v_extent=v_extent)

    #     if params.dfft_first_guess:
    #         axs[1] = fig_obj.fft_freq_panel(axs[1], ampls_fa, kls_fa[0], kls_fa[1], typ='real')
    #         axs[2] = fig_obj.fft_freq_panel(axs[2], uw_fa, kls_fa[0], kls_fa[1], title="PMF spectrum", typ='real')
    #     else:
    #         axs[1] = fig_obj.freq_panel(axs[1], ampls_fa)
    #         axs[2] = fig_obj.freq_panel(axs[2], uw_fa, title="PMF spectrum")

    #     plt.tight_layout()
    #     plt.show()
    

    ###################################
    #
    # Do second approximation over non-
    # quadrilateral grid cells
    # 
    triangle_pair = np.zeros(2, dtype='object')

    for cnt, idx in enumerate(range(rect_idx, rect_idx+2)):
        
        cell, ampls_sa, uw_sa, dat_2D_sa = sa.do(idx, ampls_fa)

        sols = (cell, ampls_sa, uw_sa, dat_2D_sa)
        dplot.show(idx, sols, v_extent=v_extent)
        # if params.plot:
        #     fs = (15,4.0)
        #     fig, axs = plt.subplots(1,3, figsize=fs)
        #     fig_obj = plotter.fig_obj(fig, nhi, nhj)
        #     axs[0] = fig_obj.phys_panel(axs[0], dat_2D_sa, title='T%i: Reconstruction' %idx, xlabel='longitude [km]', ylabel='latitude [km]', extent=[cell.lon.min(), cell.lon.max(), cell.lat.min(), cell.lat.max()], v_extent=v_extent)
        #     if params.dfft_first_guess:
        #         axs[1] = fig_obj.fft_freq_panel(axs[1], ampls_sa, kls_fa[0], kls_fa[1], typ='real')
        #         axs[2] = fig_obj.fft_freq_panel(axs[2], uw_sa, kls_fa[0], kls_fa[1], title="PMF spectrum", typ='real')
        #     else:
        #         axs[1] = fig_obj.freq_panel(axs[1], ampls_sa)
        #         axs[2] = fig_obj.freq_panel(axs[2], uw_sa, title="PMF spectrum")
        #     plt.tight_layout()
        #     # plt.savefig('../output/T%i.pdf' %idx)
        #     plt.show()

        cell.uw = uw_sa
        triangle_pair[cnt] = cell

        writer.write_all(idx, cell, cell.analysis)
        writer.populate(idx, 'pmf_sg', uw_sa)
        del cell

    ###################################
    #
    # Do iterative refinement?
    # 

    ref_topo = np.copy(cell_ref.topo)
    topo_sum = np.zeros_like(ref_topo)
    rel_err = diag.get_rel_err(triangle_pair)
    rel_errs_orig.append(rel_err)
    print(rel_err)
    print(diag)
    corrected = False

    # while (rel_err > 0.2) and (not params.no_corrections):
    #     sa.n_modes = int(sa.n_modes / 2)
 
    #     print("correcting overestimation... with n_modes=", sa.n_modes)

    #     refinement_pair = np.zeros(2, dtype='object')

    #     cell_fa, ampls_fa, uw_fa, dat_2D_fa = fa.do(simplex_lat, simplex_lon)

    #     v_extent = [dat_2D_fa.min(), dat_2D_fa.max()]

    #     if params.plot:
    #         fs = (15.0,4.0)
    #         fig, axs = plt.subplots(1,3, figsize=fs)
    #         fig_obj = plotter.fig_obj(fig, nhi, nhj)
    #         axs[0] = fig_obj.phys_panel(axs[0], dat_2D_fa, title='T%i+T%i: FF reconstruction' %(rect_idx,rect_idx+1), xlabel='longitude [km]', ylabel='latitude [km]', extent=[cell_fa.lon.min(), cell_fa.lon.max(), cell_fa.lat.min(), cell_fa.lat.max()], v_extent=v_extent)

    #         if params.dfft_first_guess:
    #             axs[1] = fig_obj.fft_freq_panel(axs[1], ampls_fa, kls_fa[0], kls_fa[1], typ='real')
    #             axs[2] = fig_obj.fft_freq_panel(axs[2], uw_fa, kls_fa[0], kls_fa[1], title="PMF spectrum", typ='real')
    #         else:
    #             axs[1] = fig_obj.freq_panel(axs[1], ampls_fa)
    #             axs[2] = fig_obj.freq_panel(axs[2], uw_fa, title="PMF spectrum")

    #         plt.tight_layout()
    #         plt.show()

    #     for cnt, idx in enumerate(range(rect_idx, rect_idx+2)):

    #         cell, ampls_rf, uw_rf, dat_2D_rf = sa.do(idx, ampls_fa)

    #         cell.uw = uw_pmf_refined
    #         refinement_pair[cnt] = cell

    #         if params.plot:
    #             fs = (15,4.0)
    #             fig, axs = plt.subplots(1,3, figsize=fs)
    #             fig_obj = plotter.fig_obj(fig, nhi, nhj)
    #             axs[0] = fig_obj.phys_panel(axs[0], dat_2D_rf, title='T%i: Reconstruction' %idx, xlabel='longitude [km]', ylabel='latitude [km]', extent=[cell.lon.min(), cell.lon.max(), cell.lat.min(), cell.lat.max()], v_extent=v_extent)
    #             if params.dfft_first_guess:
    #                 axs[1] = fig_obj.fft_freq_panel(axs[1], ampls_rf, kls_fa[0], kls_fa[1], typ='real')
    #                 axs[2] = fig_obj.fft_freq_panel(axs[2], uw_rf, kls_fa[0], kls_fa[1], title="PMF spectrum", typ='real')
    #             else:
    #                 axs[1] = fig_obj.freq_panel(axs[1], ampls_rf)
    #                 axs[2] = fig_obj.freq_panel(axs[2], uw_rf, title="PMF spectrum")
    #             plt.tight_layout()
    #             # plt.savefig('../output/T%i.pdf' %idx)
    #             plt.show()


    #     corrected = True
    #     rel_err = diag.get_rel_err(refinement_pair)
    #     print(rel_err)
    #     print(diag)

    # sa.n_modes = params.n_modes
        
    
    while np.abs(rel_err) > 0.2 and (not params.no_corrections): 
        print("correcting underestimation... with n_modes=", sa.n_modes)

        refinement_pair = np.zeros(2, dtype='object')

        sa.params.lmbda_sa = 1e-1

        topo_sum += dat_2D_fa
        res_topo = -np.sign(rel_err) * (ref_topo - topo_sum)
        res_topo -= res_topo.mean()
        # ref_topo = np.copy(res_topo)

        cell_fa, ampls_fa, uw_fa, dat_2D_fa = fa.do(simplex_lat, simplex_lon, res_topo=res_topo)

        v_extent = [dat_2D_fa.min(), dat_2D_fa.max()]

        for cnt, idx in enumerate(range(rect_idx, rect_idx+2)):
            # res_topo = cell_ref.topo - triangle_pair[cnt].analysis.recon

            cell, ampls_rf, uw_rf, dat_2D_rf = sa.do(idx, ampls_fa, res_topo = res_topo)

            ampls_sum = triangle_pair[cnt].analysis.ampls - np.sign(rel_err) * ampls_rf

            cutoff = np.sort(ampls_sum.ravel())[::-1][params.n_modes-1]
            ampls_sum[np.where(ampls_sum < cutoff)] = 0.0

            print((ampls_sum > 0.0).sum())

            cell.analysis.ampls = ampls_sum
            triangle_pair[cnt].analysis.ampls = ampls_sum

            ideal = physics.ideal_pmf(U=params.U, V=params.V)
            uw_pmf_refined = ideal.compute_uw_pmf(cell.analysis, summed=True)

            print("uw_pmf_refined", uw_pmf_refined)

            cell.uw = uw_pmf_refined
            refinement_pair[cnt] = cell

            sols = (cell, ampls_rf, uw_rf, dat_2D_rf)
            dplot.show(idx, sols, v_extent=v_extent)

            # if params.plot:
            #     fs = (15,4.0)
            #     fig, axs = plt.subplots(1,3, figsize=fs)
            #     fig_obj = plotter.fig_obj(fig, nhi, nhj)
            #     axs[0] = fig_obj.phys_panel(axs[0], dat_2D_rf, title='T%i: Reconstruction' %idx, xlabel='longitude [km]', ylabel='latitude [km]', extent=[cell.lon.min(), cell.lon.max(), cell.lat.min(), cell.lat.max()], v_extent=v_extent)
            #     if params.dfft_first_guess:
            #         axs[1] = fig_obj.fft_freq_panel(axs[1], ampls_rf, kls_fa[0], kls_fa[1], typ='real')
            #         axs[2] = fig_obj.fft_freq_panel(axs[2], uw_rf, kls_fa[0], kls_fa[1], title="PMF spectrum", typ='real')
            #     else:
            #         axs[1] = fig_obj.freq_panel(axs[1], ampls_rf)
            #         axs[2] = fig_obj.freq_panel(axs[2], uw_rf, title="PMF spectrum")
            #     plt.tight_layout()
            #     # plt.savefig('../output/T%i.pdf' %idx)
            #     plt.show()

        corrected = True
        rel_err = diag.get_rel_err(refinement_pair)
        print(rel_err)
        print(diag)

        # sa.n_modes /= 2
        sa.params.lmbda_sa = 1e-1

    if corrected:
        triangle_pair = refinement_pair
    # print(rel_err)

    diag.update_pair(triangle_pair)


diag.end(verbose=True)



# %%
print(rel_errs_orig)
print(diag.rel_errs)
%autoreload
plotter.error_bar_plot(params.rect_set, diag.rel_errs, params, comparison=np.array(rel_errs_orig)*100, gen_title=True)



# %%
importlib.reload(io)
importlib.reload(cart_plot)

errors = np.zeros((len(tri.simplices)))
errors[:] = np.nan
errors[params.rect_set] = pmf_percent_diff
errors[np.array(params.rect_set)+1] = pmf_percent_diff

levels = np.linspace(-1000.0, 3000.0, 5)
cart_plot.error_delaunay(topo, tri, label_idxs=False, fs=(12,8), highlight_indices=params.rect_set, output_fig=False, iint=1, errors=errors, alpha_max=0.6)

# %%