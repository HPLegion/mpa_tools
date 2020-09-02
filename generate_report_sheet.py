import sys
import os
from string import Template

import argparse
from _common import (
    default_argparser,
    check_output
)

_TEMPLATE = Template(
"""# $filename
## Metadata

## Plots

![$hist_adc1]($hist_adc1)

![$hist_adc2]($hist_adc2)

![$hist_adc3]($hist_adc3)

![$hist_adc2_adc1]($hist_adc2_adc1)

![$hist_adc2_adc3_dr1]($hist_adc2_adc3_dr1)

![$hist_adc2_adc3_dr2]($hist_adc2_adc3_dr2)

![$hist_adc2_adc1_dr2]($hist_adc2_adc1_dr2)


"""
)
def _main():
    parser = argparse.ArgumentParser(
        parents=[default_argparser],
        description="Create a report sheet for a given measurement."
    )
    args = parser.parse_args()
    stub = os.path.splitext(os.path.basename(args.file))[0]
    outfile = args.out
    if not outfile:
        outfile = stub + ".md"
    check_output(outfile, args.yes)

    content = _TEMPLATE.substitute(
        filename=f"{stub}.lst",
        hist_adc1=f"./{stub}_ADC1.png",
        hist_adc2=f"./{stub}_ADC2.png",
        hist_adc3=f"./{stub}_ADC3.png",
        hist_adc2_adc1=f"./{stub}_ADC2_ADC1.png",
        hist_adc2_adc3_dr1=f"./{stub}_DR1_ADC2_ADC3.png",
        hist_adc2_adc3_dr2=f"./{stub}_DR2_ADC2_ADC3.png",
        hist_adc2_adc1_dr2=f"./{stub}_DR2_ADC2_ADC1.png",

    )
    with open(outfile, "w") as f:
        f.write(content)

if __name__ == "__main__":
    _main()