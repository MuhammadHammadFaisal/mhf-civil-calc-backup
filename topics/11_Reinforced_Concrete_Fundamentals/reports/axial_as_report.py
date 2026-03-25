import pandas as pd


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
