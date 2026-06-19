import calendar

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from nice.tools.eia_860_file_tools import (
    make_prime_mover_cmap,
    prime_mover_to_desc,
    storage_prime_mover_to_desc,
)


def plot_PM_legend_separately(
    pm_list, figure_dir, include_storage_techs: bool, fig_name="pm_types_legend.png"
):
    patches = []
    labels = []
    lfig, lax = plt.subplots(1, 1, figsize=[5.5, 4.5])
    pm_cmap = make_prime_mover_cmap()
    pm_to_desc = prime_mover_to_desc()
    storage_pm_to_desc = storage_prime_mover_to_desc()
    for pm in pm_list:
        if not include_storage_techs:
            # don't include storage techs
            if pm in storage_pm_to_desc:
                continue
        patch = Line2D([0], [0], color=pm_cmap[pm])  # , label=pm_to_desc[pm])
        # patch = mpatches.Patch(color=pm_cmap[pm], label=pm_to_desc[pm])
        labels.append(pm_to_desc[pm])
        patches.append(patch)
    lax.legend(
        handles=patches,
        labels=labels,
        bbox_to_anchor=(0.0, 0.5),
        loc="center left",
        borderaxespad=0,
        frameon=False,
        fontsize=12,
    )
    lax.spines[["left", "bottom", "right", "top"]].set_visible(False)
    lax.get_xaxis().set_ticks([])
    lax.get_yaxis().set_ticks([])
    lfig.tight_layout()
    lfig.savefig(figure_dir / fig_name, bbox_inches="tight", dpi=300, pad_inches=0.0)
    plt.close(lfig)


def plot_monthly_surplus_interconnection_factor(
    spif_per_pm,
    figure_dir,
    include_storage_techs,
    plot_labels_as_text,
    plot_legend_separately,
    plot_legend,
    fig_desc,
    surplus_threshold_fraction,
):
    pm_cmap = make_prime_mover_cmap()
    pm_to_desc = prime_mover_to_desc()
    storage_pm_to_desc = storage_prime_mover_to_desc()

    # PLOT MONTHLY SURPLUS INTERCONECTION FACTOR
    fig, ax = plt.subplots(1, 1, figsize=[11.0, 6.0])
    x_vals = np.arange(1, 13, 1)
    month_name_to_abbrev = dict(
        zip(list(calendar.month_name), list(calendar.month_abbr))
    )

    months_to_n_days = {
        calendar.month_name[i]: calendar.monthrange(2024, i)[1] for i in range(1, 13)
    }

    x_labels = [month_name_to_abbrev[m] for m in list(months_to_n_days.keys())]
    # pumped storage hydro, CSP, Other, combined cycle combustion, onshore wind
    pm_shift_down = ["PS", "CP", "OT", "CT", "HY"]
    pm_shift_up = ["WT"]
    for pm in spif_per_pm.index.to_list():
        if not include_storage_techs:
            # don't include storage techs
            if pm in storage_pm_to_desc:
                continue

        y_vals = spif_per_pm.loc[pm].values * 100

        ax.plot(x_vals, y_vals, c=pm_cmap[pm], label=pm_to_desc[pm])
        ax.scatter(x_vals, y_vals, s=5.0, c=[pm_cmap[pm]] * len(x_vals))
        va = "top" if pm in pm_shift_down else "center"
        if pm in pm_shift_up:
            va = "bottom"

        if plot_labels_as_text:
            ax.text(
                x_vals[-1],
                y_vals[-1],
                pm_to_desc[pm],
                c=pm_cmap[pm],
                ha="left",
                va=va,
                size="medium",
            )

    if plot_legend_separately:
        plot_PM_legend_separately(
            spif_per_pm.index.to_list(), figure_dir, include_storage_techs
        )

    if plot_legend:
        ax.legend(bbox_to_anchor=(1.04, 0.5), loc="center left", borderaxespad=0)
    ax.tick_params(axis="both", labelsize=14.0)
    ax.set_ylabel("Surplus Interconnection Factor (%)", fontsize=14.0)
    ax.spines[["right", "top"]].set_visible(False)
    ax.set_xticks(x_vals, x_labels)

    ax.set_ylim(top=100.0)
    ax.set_xlim(left=x_vals[0])
    # ax.set_xlim([x_vals[0], x_vals[-1]+0.25])

    fig.tight_layout()
    fig.savefig(
        figure_dir
        / f"monthly_sic_factor_{int(surplus_threshold_fraction*100)}_percent_{fig_desc}.png",
        bbox_inches="tight",
        dpi=300,
        pad_inches=0.25,
    )
    plt.close(fig)
