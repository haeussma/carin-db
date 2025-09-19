import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

rng = np.random.default_rng(7)


def gaussian(x, mu, sigma, amp):
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def lorentzian(x, x0, gamma, amp):
    return amp * (0.5 * gamma) ** 2 / ((x - x0) ** 2 + (0.5 * gamma) ** 2)


# ---- Common timepoints (minutes) ----
tp_min = np.array([0, 10, 20])
tp_sec = tp_min * 60

# ---- (i) Photometric MTP (one filled well only) ----
rows, cols = 8, 12
well_rc = (1, 2)  # B3 (0-indexed)
t = np.linspace(0, 1800, 120)
Amax, k = 1.0, 1 / 700
trace = Amax * (1 - np.exp(-k * t)) + rng.normal(0, 0.004, t.size)


def plate_at(tsec):
    P = np.full((rows, cols), np.nan, dtype=float)
    P[well_rc] = Amax * (1 - np.exp(-k * tsec))
    return P


plates = [plate_at(ts) for ts in tp_sec]
vmin = 0.0
vmax = max(p[well_rc] for p in plates)
cmap = mpl.cm.get_cmap("viridis").copy()
cmap.set_bad("white")  # all other wells plain white

# ---- (ii) Chromatography (one analyte peak grows) ----
rt = np.linspace(0.6, 6.0, 2000)
analyte_rt, analyte_sigma = 3.20, 0.07


def chromo_at(tp):
    frac = np.clip(tp / tp_min[-1], 0, 1)
    amp = 0.08 + 0.95 * frac
    base = 0.01 + 0.002 * np.sin(2 * np.pi * rt / 2.8)
    y = gaussian(rt, analyte_rt, analyte_sigma, amp) + base
    y += rng.normal(0, 0.0018, rt.size)
    return y


chromos = [chromo_at(tp) for tp in tp_min]
ch_offsets = np.linspace(0.0, 0.25, len(chromos))

# ---- (iii) 1H NMR (one integral window increases) ----
ppm = np.linspace(10, 0, 4000)  # high→low ppm
peak_ppm, gamma = 3.35, 0.05
integral_region = (3.60, 3.10)  # start, end (axis reversed)


def nmr_at(scale):
    y = lorentzian(ppm, peak_ppm, gamma, 0.25 * scale)
    y += 0.002 * np.sin(2 * np.pi * ppm / 3.5)
    y += rng.normal(0, 0.0018, ppm.size)
    return y


nmr_scales = 0.9 + 0.2 * (tp_min / tp_min[-1])
nmr_specs = [nmr_at(s) for s in nmr_scales]
nmr_offsets = np.linspace(0.0, 0.6, len(nmr_specs))

# ---- Plot ----
fig = plt.figure(figsize=(14, 5))
gs = fig.add_gridspec(1, 3, wspace=0.25)

# Panel (i): 3 heatmaps (single well colored), shared colorbar, inset trace
ax1 = fig.add_subplot(gs[0, 0])
ax1.axis("off")
sub = gs[0, 0].subgridspec(1, 3, wspace=0.05)
axs_hm = [fig.add_subplot(sub[0, i]) for i in range(3)]
ims = []
for i, (ax, P, lbl) in enumerate(zip(axs_hm, plates, tp_min)):
    im = ax.imshow(P, vmin=vmin, vmax=vmax, cmap=cmap, aspect="auto")
    ims.append(im)
    ax.set_title(f"{lbl} min", fontsize=9)
    ax.set_xticks(range(cols))
    ax.set_yticks(range(rows))
    ax.set_xticklabels([str(j + 1) for j in range(cols)], fontsize=6)
    ax.set_yticklabels([chr(ord("A") + j) for j in range(rows)], fontsize=6)
    if i > 0:
        ax.set_yticklabels([])
    if i == 0:
        r, c = well_rc
        ax.scatter(
            [c], [r], s=45, marker="s", edgecolor="k", facecolor="none", linewidths=1
        )

cb = fig.colorbar(ims[0], ax=axs_hm, fraction=0.046, pad=0.04)
cb.set_label("Signal (a.u.)", fontsize=8)
axs_hm[0].text(
    -0.05,
    1.05,
    "Photometric (MTP): one analyte, one well",
    transform=axs_hm[0].transAxes,
    ha="left",
    va="bottom",
    fontsize=11,
)

in_ax = inset_axes(
    axs_hm[-1], width="58%", height="58%", loc="lower right", borderpad=0.7
)
in_ax.plot(t / 60, trace, lw=1)
in_ax.set_xlabel("Time (min)", fontsize=7)
in_ax.set_ylabel("Abs.", fontsize=7)
in_ax.tick_params(labelsize=7)
in_ax.set_title("Tracked well (B3)", fontsize=8)

# Panel (ii): Chromatograms (one peak), stacked
ax2 = fig.add_subplot(gs[0, 1])
for y, off, tp in zip(chromos, ch_offsets, tp_min):
    ax2.plot(rt, y + off, lw=1, label=f"{tp} min")
ix = np.argmin(np.abs(rt - analyte_rt))
ax2.annotate(
    "Analyte",
    xy=(analyte_rt, chromos[-1][ix] + ch_offsets[-1]),
    xytext=(analyte_rt + 0.35, chromos[-1][ix] + ch_offsets[-1] + 0.06),
    arrowprops=dict(arrowstyle="->"),
    fontsize=8,
)
ax2.set_xlabel("Retention time (min)")
ax2.set_ylabel("Response (offset)")
ax2.set_title("Chromatographic (discrete samples): one analyte")
ax2.legend(frameon=False, fontsize=8)

# Panel (iii): NMR (one region), stacked with integral shading
ax3 = fig.add_subplot(gs[0, 2])
for y, off in zip(nmr_specs, nmr_offsets):
    ax3.plot(ppm, y + off, lw=1)
lo, hi = integral_region
mask = (ppm <= lo) & (ppm >= hi)
for y, off in zip(nmr_specs, nmr_offsets):
    ax3.fill_between(ppm[mask], off, (y + off)[mask], alpha=0.18, linewidth=0)
ax3.annotate(
    "Analyte integral",
    xy=(np.mean([lo, hi]), (nmr_specs[-1][mask].max() + nmr_offsets[-1])),
    xytext=(np.mean([lo, hi]) + 0.6, nmr_offsets[-1] + 0.35),
    arrowprops=dict(arrowstyle="->"),
    fontsize=8,
)
ax3.set_xlabel("δ (ppm)")
ax3.set_ylabel("Intensity (offset)")
ax3.set_title("¹H NMR (stacked): one analyte")
ax3.invert_xaxis()

fig.suptitle("One analyte across methods: 0 / 10 / 20 min", y=0.99, fontsize=12)
plt.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig("kinetics_one_analyte_three_panels.png", dpi=300)
fig.savefig("kinetics_one_analyte_three_panels.svg")
plt.show()
