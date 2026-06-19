import matplotlib.pyplot as plt

from nice.tools.eia_860_file_tools import make_prime_mover_cmap, prime_mover_to_desc


def violin_plot_of_sic(df, pm, figure_dir, surplus_threshold_fraction):
    pm_cmap = make_prime_mover_cmap()
    pm_to_desc = prime_mover_to_desc()
    vw = 0.5

    data_plt = (
        df.swaplevel().loc[pm]["Surplus Interconnect Capacity (MW)"].dropna().values
    )

    
    fig, ax = plt.subplots(1, 1, figsize=[4.8, 6.4])

    vparts = ax.violinplot(
        data_plt, [1.0], widths=vw, 
        points=100, showmedians=True, showextrema=True
    )

    # Step 5: modify violins
    for ni, pc in enumerate(vparts["bodies"]):
        pc.set_facecolor(pm_cmap[pm])
        pc.set_alpha(1.0)

    vpart_modifies = ["bodies", "cmedians", "cmaxes", "cmins", "cbars"]
    for k in vpart_modifies:
        v = {
            "color": "black" if k != "bodies" else pm_cmap[pm],
            "linewidth": 1.0 if k != "bodies" else 0.5,
            "linestyle": "solid" if k != "cmedians" else "dotted",
        }
        if k in vparts:
            if isinstance(vparts[k], list):
                for pi, pv in enumerate(vparts[k]):
                    # for ki,vi in v.items():
                    pv.set(**v)
            else:
                vparts[k].set(**v)

    ax.set_ylabel("Surplus Interconnection Capacity (MW)")
    ax.set_xlabel(f"{pm_to_desc[pm]} ({len(data_plt)} generators)")
    ax.spines[["right", "top"]].set_visible(False)

    # ax.set_ylim(bottom=0.0)
    ax.get_xaxis().set_ticks([])
    fig.tight_layout()
    fig_fpath = (
        figure_dir / f"violin_{pm}_{int(surplus_threshold_fraction*100)}_percent.png"
    )
    fig.savefig(fig_fpath, bbox_inches="tight", dpi=300, pad_inches=0.25)
    plt.close(fig)
