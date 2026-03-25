import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64

from ..diagrams_results.load_deformation_plot import plot_load_deformation


def _fmt(x, nd=2):
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return str(x)


def build_axial_summary_table(results):
    results_data = [
        ["Unconfined Capacity (N_or)", f"{results.Nor1 / 1000:,.1f} kN"]
    ]

    if results.Nor2 is not None:
        results_data.append(["Confined Capacity (N_or2)", f"{results.Nor2 / 1000:,.1f} kN"])
        results_data.append(["Capacity Increase (Δ)", f"{(results.Nor2 - results.Nor1) / 1000:,.1f} kN"])
    else:
        results_data.append(["Confined Capacity (N_or2)", "N/A"])
        results_data.append(["Capacity Increase (Δ)", "N/A"])

    return pd.DataFrame(results_data, columns=["Parameter", "Value"])


def build_axial_graph_html(results, reinf_style):
    graph_N1 = results.Nor1 / 1000
    graph_N2 = results.Nor2 / 1000 if results.Nor2 is not None else 0
    plot_type = "Spiral" if "Spiral" in reinf_style else "Ties"

    fig = plot_load_deformation(graph_N1, graph_N2, plot_type)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", transparent=True)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)

    return f'<img src="data:image/png;base64,{img_base64}" style="width:100%; max-width:700px; border-radius:8px;">'


def build_step_by_step_markdown(
    results,
    fc,
    fy_long,
    Ag,
    Ast,
    reinf_style,
    core_diameter_input,
    strength_basis,
    fywk=0.0,
    spiral_dia=0.0,
    spiral_spacing=0.0,
):
    """
    Student-friendly step-by-step report.

    Units:
    - MPa = N/mm²
    - Area = mm²
    - Force = N (we also display kN)
    """

    ALPHA_CC = 0.85
    gamma_c = getattr(results, "gamma_c", 1.5)
    gamma_s = getattr(results, "gamma_s", 1.15)

    fcd = results.fcd
    fyd = results.fyd

    Fc = ALPHA_CC * fcd * Ag
    Fs = Ast * fyd
    Nor1 = Fc + Fs

    md = f"""
### Given / Inputs
- Concrete strength input: $f_{{ck}} = {_fmt(fc,2)}\\,\\text{{MPa}}$
- Steel strength input: $f_{{yk}} = {_fmt(fy_long,2)}\\,\\text{{MPa}}$
- Gross area: $A_g = {_fmt(Ag,0)}\\,\\text{{mm}}^2$
- Steel area: $A_{{st}} = {_fmt(Ast,0)}\\,\\text{{mm}}^2$
- Confinement type: **{reinf_style}**
- Strength selection (radio): **{strength_basis}**

> Unit note: $1\\,\\text{{MPa}} = 1\\,\\text{{N/mm}}^2$  
> So (MPa) × (mm²) = **N**.

---

## Step 1 — Choose design or characteristic strengths
Your radio button decides what we use:

### If **Design Values (fcd, fyd)**
Use partial safety factors:
- $\\gamma_c = {_fmt(gamma_c,2)}$
- $\\gamma_s = {_fmt(gamma_s,2)}$

$$
f_{{cd}} = \\frac{{f_{{ck}}}}{{\\gamma_c}}
= \\frac{{{_fmt(fc,2)}}}{{{_fmt(gamma_c,2)}}}
= \\mathbf{{{_fmt(fc/gamma_c,2)}}}\\,\\text{{MPa}}
$$

$$
f_{{yd}} = \\frac{{f_{{yk}}}}{{\\gamma_s}}
= \\frac{{{_fmt(fy_long,2)}}}{{{_fmt(gamma_s,2)}}}
= \\mathbf{{{_fmt(fy_long/gamma_s,2)}}}\\,\\text{{MPa}}
$$

### If **Characteristic Values (fck, fyk)**
No reduction:
$$
f_{{cd}} = f_{{ck}} = \\mathbf{{{_fmt(fc,2)}}}\\,\\text{{MPa}}
\\qquad
f_{{yd}} = f_{{yk}} = \\mathbf{{{_fmt(fy_long,2)}}}\\,\\text{{MPa}}
$$

✅ Your selected values used in calculations:
$$
f_{{cd}} = \\mathbf{{{_fmt(fcd,2)}}}\\,\\text{{MPa}}
\\qquad
f_{{yd}} = \\mathbf{{{_fmt(fyd,2)}}}\\,\\text{{MPa}}
$$

---

## Step 2 — Concrete contribution $F_c$
**Course assumption:** concrete compression uses *gross* area $A_g$.

Formula:
$$
F_c = \\alpha_{{cc}}\\, f_{{cd}}\\, A_g
$$

Substitute:
$$
F_c = 0.85\\times({_fmt(fcd,2)})\\times({_fmt(Ag,0)})
$$

Result:
$$
F_c = \\mathbf{{{Fc/1000:,.1f}}}\\,\\text{{kN}}
\\;\\;\\; (={Fc:,.0f}\\,\\text{{N}})
$$

---

## Step 3 — Steel contribution $F_s$
Formula:
$$
F_s = A_{{st}}\\, f_{{yd}}
$$

Substitute:
$$
F_s = ({_fmt(Ast,0)})\\times({_fmt(fyd,2)})
$$

Result:
$$
F_s = \\mathbf{{{Fs/1000:,.1f}}}\\,\\text{{kN}}
\\;\\;\\; (={Fs:,.0f}\\,\\text{{N}})
$$

---

## Step 4 — Total axial capacity (Unconfined)
$$
N_{{or}} = F_c + F_s
$$

$$
N_{{or}} = \\mathbf{{{Nor1/1000:,.1f}}}\\,\\text{{kN}}
$$
"""

    if (
        "Spiral" in reinf_style
        and results.Nor2 is not None
        and spiral_spacing > 0
        and spiral_dia > 0
        and fywk > 0
        and core_diameter_input > 0
    ):
        d_outer = core_diameter_input
        d_center = d_outer - spiral_dia

        Ack = np.pi * d_outer**2 / 4.0
        Asp = np.pi * spiral_dia**2 / 4.0

        rho_s = (4.0 * Asp) / (d_center * spiral_spacing)

        rho_min_calc = 0.45 * (fc / fywk) * ((Ag / Ack) - 1.0)
        rho_min_abs = 0.12 * (fc / fywk)
        rho_min_req = max(rho_min_calc, rho_min_abs)

        confinement_boost = (2.0 * rho_s * fywk) / 1.5
        fccd = fcd + confinement_boost

        Nor2 = fccd * Ack + Ast * fyd

        ok_text = "✅ OK" if rho_s >= rho_min_req else "❌ NOT OK"

        md += f"""
---

# Spiral confinement (Confined core)

## Step 5 — Core & spiral geometry
- $D_k = {_fmt(d_outer,1)}\\,\\text{{mm}}$ (to centerline)
- Spiral bar $\\phi_{{sp}} = {_fmt(spiral_dia,1)}\\,\\text{{mm}}$
- Spacing $s = {_fmt(spiral_spacing,1)}\\,\\text{{mm}}$
- Spiral steel $f_{{ywk}} = {_fmt(fywk,1)}\\,\\text{{MPa}}$

Core area:
$$
A_{{ck}} = \\frac{{\\pi D_k^2}}{{4}}
= \\frac{{\\pi({_fmt(d_outer,1)})^2}}{{4}}
= {_fmt(Ack,0)}\\,\\text{{mm}}^2
$$

Spiral steel area:
$$
A_{{sp}} = \\frac{{\\pi \\phi_{{sp}}^2}}{{4}}
= {_fmt(Asp,0)}\\,\\text{{mm}}^2
$$

---

## Step 6 — Volumetric ratio $\\rho_s$
Using your calculator’s formula:
$$
\\rho_s = \\frac{{4A_{{sp}}}}{{D_{{center}}\\,s}}
\\quad \\text{{with}}\\quad D_{{center}} = D_k - \\phi_{{sp}} = {_fmt(d_center,1)}\\,\\text{{mm}}
$$

$$
\\rho_s = \\frac{{4\\times({_fmt(Asp,0)})}}{{({_fmt(d_center,1)})\\times({_fmt(spiral_spacing,1)})}}
= \\mathbf{{{_fmt(rho_s,5)}}}
$$

---

## Step 7 — Minimum required $\\rho_{{min}}$
$$
\\rho_{{min,calc}} = 0.45\\left(\\frac{{f_{{ck}}}}{{f_{{ywk}}}}\\right)\\left(\\frac{{A_g}}{{A_{{ck}}}} - 1\\right)
= \\mathbf{{{_fmt(rho_min_calc,5)}}}
$$

$$
\\rho_{{min,abs}} = 0.12\\left(\\frac{{f_{{ck}}}}{{f_{{ywk}}}}\\right)
= \\mathbf{{{_fmt(rho_min_abs,5)}}}
$$

$$
\\rho_{{min}} = \\max(\\rho_{{min,calc}},\\rho_{{min,abs}})
= \\mathbf{{{_fmt(rho_min_req,5)}}}
$$

Check: $\\rho_s \\ge \\rho_{{min}}$ → **{ok_text}**

---

## Step 8 — Confined concrete strength
Boost (your calculator):
$$
\\Delta f = \\frac{{2\\rho_s f_{{ywk}}}}{{1.5}}
= \\frac{{2\\times({_fmt(rho_s,5)})\\times({_fmt(fywk,1)})}}{{1.5}}
= {_fmt(confinement_boost,2)}\\,\\text{{MPa}}
$$

$$
f_{{ccd}} = f_{{cd}} + \\Delta f
= {_fmt(fcd,2)} + {_fmt(confinement_boost,2)}
= \\mathbf{{{_fmt(fccd,2)}}}\\,\\text{{MPa}}
$$

---

## Step 9 — Confined axial capacity
$$
N_{{or2}} = f_{{ccd}}A_{{ck}} + A_{{st}}f_{{yd}}
$$

$$
N_{{or2}} = ({_fmt(fccd,2)})\\times({_fmt(Ack,0)}) + ({_fmt(Ast,0)})\\times({_fmt(fyd,2)})
= \\mathbf{{{Nor2/1000:,.1f}}}\\,\\text{{kN}}
$$
"""

    return md


def build_required_as_table(results_as, Nu_kN_req):
    data = [
        ["Applied Load (Nu)", f"{Nu_kN_req:,.1f} kN"],
        ["Concrete Contribution (Fc)", f"{results_as.Fc / 1000:,.1f} kN"],
        ["Required Steel Area (As,req)", f"{results_as.Ast_req:,.1f} mm²"],
        ["Required Steel Ratio (ρ)", f"{results_as.rho_req * 100:.3f} %"],
        ["1st Peak Capacity (N_or1)", f"{results_as.Nor1 / 1000:,.1f} kN"],
        ["2nd Peak Capacity (N_or2)", f"{results_as.Nor2 / 1000:,.1f} kN"],
    ]
    return pd.DataFrame(data, columns=["Parameter", "Value"])
    
def build_required_as_graph_html(Ast_req, Ag):
    rho_req = (Ast_req / Ag * 100.0) if Ag > 0 else 0.0

    html = f"""
    <div style="padding: 18px; border-radius: 12px; text-align: center;">
        <h4 style="margin-bottom: 10px;">Required Reinforcement Preview</h4>
        <div style="font-size: 2rem; font-weight: 700; margin-bottom: 8px;">
            {Ast_req:,.1f} mm²
        </div>
        <div style="font-size: 1rem; opacity: 0.9;">
            Steel Ratio = {rho_req:.3f} %
        </div>
    </div>
    """
    return html


def build_required_as_markdown(
    results_as,
    fc,
    fy_long,
    Ag,
    reinf_style,
    strength_basis,
    Nu_kN_req,
    fywk=0.0,
    spiral_dia=0.0,
    spiral_spacing=0.0,
    core_diameter_input=0.0,
):
    md = f"""
### Required Steel (As) — Step-by-step

### Given / Inputs
- Concrete strength input: $f_{{ck}} = {fc:.2f}\\,\\text{{MPa}}$
- Steel strength input: $f_{{yk}} = {fy_long:.2f}\\,\\text{{MPa}}$
- Gross area: $A_g = {Ag:,.0f}\\,\\text{{mm}}^2$
- Required axial load: $N_u = {Nu_kN_req:,.1f}\\,\\text{{kN}}$
- Confinement type: **{reinf_style}**
- Strength selection (radio): **{strength_basis}**

---

## Step 1 — Choose strengths used in calculation

Used values:
$$
f_{{cd}} = {results_as.fcd:.2f}\\,\\text{{MPa}}
\\qquad
f_{{yd}} = {results_as.fyd:.2f}\\,\\text{{MPa}}
$$

---

## Step 2 — Concrete contribution
Formula:
$$
F_c = 0.85\\, f_{{cd}}\\, A_g
$$

Substitute:
$$
F_c = 0.85\\times({results_as.fcd:.2f})\\times({Ag:,.0f})
$$

Result:
$$
F_c = {results_as.Fc/1000:,.1f}\\,\\text{{kN}}
$$

---

## Step 3 — Solve for required steel
Formula:
$$
N_u = F_c + A_s f_{{yd}}
$$

Rearrange:
$$
A_s = \\frac{{N_u - F_c}}{{f_{{yd}}}}
$$

Substitute:
$$
A_s = \\frac{{{results_as.Nu_N:,.0f} - {results_as.Fc:,.0f}}}{{{results_as.fyd:.2f}}}
$$

Result:
$$
A_{{s,req}} = \\mathbf{{{results_as.Ast_req:,.1f}}}\\,\\text{{mm}}^2
$$

Steel ratio:
$$
\\rho = \\frac{{A_{{s,req}}}}{{A_g}} = {results_as.rho_req:.5f}
= {results_as.rho_req * 100:.3f}\\%
$$

---

## Step 4 — First peak capacity
Using required steel:
$$
N_{{or1}} = F_c + A_{{s,req}}f_{{yd}}
$$

$$
N_{{or1}} = {results_as.Nor1/1000:,.1f}\\,\\text{{kN}}
$$

---

## Step 5 — Second peak capacity
For non-spiral sections:
$$
N_{{or2}} = N_{{or1}}
$$

For spiral sections, confined concrete is checked and the displayed value is taken as:
$$
N_{{or2}} = \\max(N_{{or1}}, N_{{or2,raw}})
$$

Displayed result:
$$
N_{{or2}} = {results_as.Nor2/1000:,.1f}\\,\\text{{kN}}
$$
"""

    if "Spiral" in reinf_style and results_as.Ack is not None:
        ok_text = "✅ OK" if results_as.spiral_ok else "❌ NOT OK"

        md += f"""

---

## Spiral confinement check

- Spiral diameter: $\\phi_{{sp}} = {spiral_dia:.1f}\\,\\text{{mm}}$
- Spiral spacing: $s = {spiral_spacing:.1f}\\,\\text{{mm}}$
- Spiral steel strength: $f_{{ywk}} = {fywk:.1f}\\,\\text{{MPa}}$
- Core diameter: $D_k = {core_diameter_input:.1f}\\,\\text{{mm}}$

Core area:
$$
A_{{ck}} = {results_as.Ack:,.0f}\\,\\text{{mm}}^2
$$

Volumetric ratio:
$$
\\rho_s = {results_as.rho_s:.5f}
$$

Minimum required:
$$
\\rho_{{min}} = {results_as.rho_min_req:.5f}
$$

Check:
**{ok_text}**

Confined concrete strength:
$$
f_{{ccd}} = {results_as.fccd:.2f}\\,\\text{{MPa}}
$$

Raw confined capacity:
$$
N_{{or2,raw}} = {results_as.Nor2_raw/1000:,.1f}\\,\\text{{kN}}
$$

Final displayed second peak:
$$
N_{{or2}} = \\max(N_{{or1}}, N_{{or2,raw}})
= {results_as.Nor2/1000:,.1f}\\,\\text{{kN}}
$$
"""

    return md
