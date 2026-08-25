import matplotlib as mpl
import numpy as np


def make_discrete_color_dict(
    d_params,
    cmap_name="tab10",
):
    # d_params = list(set(discrete_params))
    # d_params.sort()
    n_clusters = len(d_params)
    if isinstance(mpl.colormaps[cmap_name], mpl.colors.LinearSegmentedColormap):
        cmap_colors = mpl.colormaps[cmap_name](np.linspace(0, 1, int(n_clusters)))
    else:
        if len(mpl.colormaps[cmap_name].colors) < 256:
            cmap_colors = mpl.colormaps[cmap_name].colors[: int(n_clusters)]
        else:
            cmap_colors = mpl.colormaps[cmap_name](np.linspace(0, 1, int(n_clusters)))

    return dict(zip(d_params, cmap_colors))


def area_to_point_size(fig_dim):
    ref_fig_dim = 12
    ref_s = 0.125
    a_fig_ref = ref_fig_dim * ref_fig_dim
    a_fig = fig_dim * fig_dim
    k_a = a_fig / a_fig_ref
    new_s = ref_s * k_a
    return new_s
