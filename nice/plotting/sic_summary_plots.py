import matplotlib.pyplot as plt
import numpy as np

from nice.tools.eia_860_file_tools import (
    make_prime_mover_cmap,
    prime_mover_to_desc,
    storage_prime_mover_to_desc,
)


def stacked_bar_sic_capacity(
    pm_list,
    sic,
    tot_capac,
    fig_fpath,
    y_units,
    sub_pm_list,
):
    pm_cmap = make_prime_mover_cmap()
    pm_to_desc = prime_mover_to_desc()

    x_vals = np.arange(1, len(pm_list) + 1, 1)
    fig, ax = plt.subplots(1, 1, figsize=[11.0, 6.0])

    sorted_pm_list = tot_capac.loc[pm_list].sort_values(ascending=False).index.to_list()

    y1_vals = tot_capac.loc[sorted_pm_list].values
    y2_vals = sic.loc[sorted_pm_list].values
    colors = [pm_cmap[pm] for pm in sorted_pm_list]
    bw = 0.8

    b1 = ax.bar(x_vals, y1_vals, width=bw, color=colors, alpha=0.5, align="center")
    b2 = ax.bar(x_vals, y2_vals, width=bw, color=colors, alpha=1.0, align="center")
    # ax.bar_label(b1, fmt="{:.2E}",label_type='edge')
    # ax.bar_label(b2, fmt="{:.2E}",label_type='center')
    ax.bar_label(b1, fmt="{:,.1f}", label_type="edge")
    ax.bar_label(b2, fmt="{:,.1f}", label_type="center")

    ax.set_ylabel(f"Capacity ({y_units})")
    # xticks = ax.get_xticks()
    # ax.set_xticks(x_vals, x_labels, rotation=45)
    ax.set_xticks(x_vals, sorted_pm_list)
    ax.set_xlim([x_vals[0] - bw / 2, x_vals[-1] + bw / 2])

    ax.spines[["right", "top"]].set_visible(False)
    # x_tick_locs = np.array(x_vals) - (bw/2)
    # ax.set_xticklabels(x_labels)

    if len(sub_pm_list) > 0:
        ymax = np.ceil(tot_capac.loc[sub_pm_list].max())
        xmin = x_vals[-1] - len(sub_pm_list) - bw / 2

        y1s_vals = tot_capac.loc[sub_pm_list].values
        y2s_vals = sic.loc[sub_pm_list].values
        scolors = [pm_cmap[pm] for pm in sub_pm_list]

        xs_vals = xmin + np.arange(0, len(y1s_vals), 1)

        axins = ax.inset_axes(
            # [0.5, 0.35, 0.47, 0.47],
            [0.55, 0.4, 0.45, 0.60],
            # xlim=(xmin-bw/2, x_vals[-1]+bw/2),
            xlim=(xs_vals[0] - bw / 2, xs_vals[-1] + bw / 2),
            ylim=(0, ymax),
        )

        ymax = np.ceil(tot_capac.loc[sub_pm_list].max())
        b1s = axins.bar(
            xs_vals,
            y1s_vals,
            width=bw,
            color=scolors,
            alpha=0.5,
            align="center",
            tick_label=sub_pm_list,
        )
        b2s = axins.bar(
            xs_vals, y2s_vals, width=bw, color=scolors, alpha=1.0, align="center"
        )
        axins.bar_label(b1s, fmt="{:.2f}", label_type="edge")
        axins.bar_label(b2s, fmt="{:.2f}", label_type="center")

        # ax.indicate_inset_zoom(axins, edgecolor="black")

    fig.savefig(fig_fpath, bbox_inches="tight", dpi=300, pad_inches=0.0)

    plt.close(fig)


def stacked_bar_capacity(
    df,
    include_storage_techs,
    figure_dir,
    surplus_threshold_fraction,
):
    make_prime_mover_cmap()
    prime_mover_to_desc()
    storage_pm_to_desc = storage_prime_mover_to_desc()

    sic = (
        df.groupby(level="Prime Mover")["Surplus Interconnect Capacity (MW)"]
        .sum()
        .copy()
    )
    tot_capac = df.groupby(level="Prime Mover")["Nameplate Capacity (MW)"].sum().copy()

    if not include_storage_techs:
        pm_list = [k for k in sic.index.to_list() if k not in storage_pm_to_desc]
    else:
        pm_list = sic.index.to_list()

    tot_capac.loc[pm_list].sort_values() / 1e3

    i_big = np.argwhere(
        (tot_capac.loc[pm_list].sort_values() / 1e3).values > 10.0
    ).flatten()
    pm_big = tot_capac.loc[pm_list].sort_values().iloc[i_big].index.to_list()
    pm_small = (set(pm_list)).difference(set(pm_big))

    pm_small_sorted = (
        tot_capac.loc[list(pm_small)].sort_values(ascending=False).index.to_list()
    )
    figname_all = (
        f"capacity_PM_barchart_capacities_{int(surplus_threshold_fraction*100)}_percent"
    )
    stacked_bar_sic_capacity(
        pm_list,
        sic / 1e3,
        tot_capac / 1e3,
        figure_dir / figname_all,
        "GW",
        pm_small_sorted,
    )

    figname_small = f"small_capacity_PM_barchart_capacities_{int(surplus_threshold_fraction*100)}_percent"
    figname_large = f"large_capacity_PM_barchart_capacities_{int(surplus_threshold_fraction*100)}_percent"

    stacked_bar_sic_capacity(
        list(pm_small), sic, tot_capac, figure_dir / figname_small, "MW"
    )
    stacked_bar_sic_capacity(
        list(pm_big), sic / 1e3, tot_capac / 1e3, figure_dir / figname_large, "GW"
    )
    # for pm in pm_list:
    #     []
    # # PLOT MONTHLY SURPLUS INTERCONECTION FACTOR
    # fig, ax = plt.subplots(1, 1, figsize=[11.0, 6.0])
