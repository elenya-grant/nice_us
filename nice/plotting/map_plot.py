import matplotlib.pyplot as plt
import numpy as np

from nice.tools.geo_data_file_tools import convert_df_to_gdf, load_us_state_boundaries


def plot_scatter_map_basic(df, data_col: str, cbar_label: str, cmap, norm, figfpath):
    gdf = convert_df_to_gdf(df.copy())

    # fig, ax = plt.subplots(1, 1, figsize=[8, 8])
    fig, ax = plt.subplots(1, 1, figsize=[6, 6])

    us_states = load_us_state_boundaries()
    us_states.boundary.plot(ax=ax, alpha=0.5, edgecolor="tab:gray", linewidth=0.325)

    sc = ax.scatter(
        x=gdf["Longitude"],
        y=gdf["Latitude"],
        s=0.50,
        c=np.ma.masked_invalid(gdf[data_col].values),
        cmap=cmap,
        norm=norm,
        alpha=0.9,
        # alpha=0.75,
    )
    # ax.set_ylim([24.396308,49.384479])
    ax.set_ylim([24.2, 49.384479])
    # ax.set_xlim([-124.848974,-66.885444])
    ax.set_xlim([-125.0, -66.5])

    cb = fig.colorbar(
        sc,
        ax=ax,
        label=cbar_label,
        location="bottom",
        orientation="horizontal",
        pad=0.0,
        shrink=0.75,
        extend="both",
    )
    cb.ax.tick_params(labelsize=8.0)
    cb.ax.xaxis.label.set_fontsize(9.0)

    ax.spines[["right", "top", "bottom", "left"]].set_visible(False)
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([])

    fig.savefig(figfpath, bbox_inches="tight", dpi=300, pad_inches=0.0)

    plt.close(fig)
