import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

plt.style.use("seaborn-v0_8-colorblind")


def float_tex(x: float | str, sig: int = 6):
    if isinstance(x, str):
        return x
    if x == 0 or (isinstance(x, float) and np.isclose(x, 0)):
        return "$0$"
    if np.isnan(x) or np.isinf(x):
        return "---"

    return rf"${x:.{sig}f}$"


def sci_tex(x, sig=6):
    if x == 0 or (isinstance(x, float) and np.isclose(x, 0)):
        return "$0$"
    if np.isnan(x):
        return "---"
    exp = int(np.floor(np.log10(abs(x))))
    mant = x / (10**exp)
    return rf"${mant:.{sig - 1}f}\times 10^{{{exp}}}$"


def _sty(df, formats=None, sig=6, hide_index=True):
    """
    Return a Markdown table string that Quarto can render in both HTML and PDF.

    Parameters
    ----------
    df : pandas.DataFrame
        Input table.
    formats : dict or None
        Mapping of column name -> formatter function.
        Example: {"h": sci_tex, "Abs. error": sci_tex}
    sig : int
        Significant digits passed to sci_tex if used via lambda.
    hide_index : bool
        If True, omit the index from the Markdown table.
    """
    out = df.copy()

    if formats is None:
        formats = {}

    for col, fmt in formats.items():
        if col in out.columns:
            out[col] = out[col].map(fmt)

    # Replace remaining missing values with em-dash style marker
    out = out.fillna("---")

    return out.to_markdown(index=not hide_index)


def table_styler(df):
    return _sty(
        df,
        formats={
            "h": sci_tex,
            "Solution": float_tex,
            "Abs. error": sci_tex,
            "Run time": sci_tex,
            "Ratio": float_tex,
            "Run time ratio": float_tex,
        },
    )
