import sys
import os
from string import Template

from pandas import NA
from numpy import float_

import argparse
from _common import (
    default_argparser,
    check_output
)

_TEMPLATE = Template(
"""# $FILENAME

## Meta data

$META

## Plots

$PLOTS
"""
)

_PLOTS = Template(
"""
![$hist_adc1]($hist_adc1)

![$hist_adc2]($hist_adc2)

![$hist_adc3]($hist_adc3)

![$hist_adc2_adc1]($hist_adc2_adc1)

![$hist_adc2_adc3_dr1]($hist_adc2_adc3_dr1)

![$hist_adc2_adc3_dr2]($hist_adc2_adc3_dr2)

![$hist_adc2_adc1_dr2]($hist_adc2_adc1_dr2)
"""
)

_META = Template(
"""Recorded: $T_START - $T_STOP

Comments:

$COMMENT

Pressures:

- Gun: $P_GUN_START mbar - $P_GUN_STOP mbar
- Magnet: $P_MAG_START mbar - $P_MAG_STOP mbar
- Collector: $P_COLL_START mbar - $P_COLL_STOP mbar
- Injection 1: $P_INJ1_START mbar - $P_INJ1_STOP mbar
- Injection 2: $P_INJ2_START mbar - $P_INJ2_STOP mbar

Time intervals:

- Breeding: $TAU_BREED s
- Dumping (beam stop): $TAU_DUMP s
- Energy Ramp: $TAU_RAMP s

Electron beam:

- Current: $I_BEAM A
- Cathode bias: $U_CATHODE V
- Focus: $U_FOCUS_ON / $U_FOCUS_OFF
- Cathode heater: $U_HEAT V / $I_HEAT A

Trap:

- Trap DT: $U_TRAP V
- Dump (Trap DT): $U_DUMP_PULSE V
- Barrier (E1/G1): $U_BARRIER
- Barrier Ramp?: $BARRIER_RAMP
- DT platform: $U_DT_LOW V - $U_DT_HIGH V

Coils:

- Bucking: $U_BUCKING_COIL V / $I_BUCKING_COIL A
- Collector $U_COLL_COIL V / $I_COLL_COIL A

ADCs:

- ADC1: $ADC1_CALIB_LOW eV - $ADC1_CALIB_HIGH eV ($ADC1_CUT_LOW - $ADC1_CUT_HIGH)
- ADC2: $ADC2_CALIB_LOW V - $ADC2_CALIB_HIGH V ($ADC2_CUT_LOW - $ADC2_CUT_HIGH)
- ADC3: $ADC3_CALIB_LOW s - $ADC3_CALIB_HIGH s ($ADC3_CUT_LOW - $ADC3_CUT_HIGH)
- ADC4: $ADC4_CALIB_LOW V - $ADC4_CALIB_HIGH V ($ADC4_CUT_LOW - $ADC4_CUT_HIGH)
"""
)

def stringify_meta(dct):
    for k, v in dct.items():
        if k == "COMMENT":
            if dct[k] is NA:
                dct[k] = "N/A"
            else:
                cm = v.split(";")
                cm = ["- " + c.strip() for c in cm]
                dct[k] = "\n".join(cm) + "\n"
        if isinstance(v, float_):
            dct[k] = f"{v:.2f}"
        if k.startswith("P_"):
            dct[k] = f"{v:.2e}"
        if k == "I_BEAM":
            dct[k] = f"{v:.3f}"
        dct[k] = str(dct[k])


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

    plots = _PLOTS.substitute(
        hist_adc1=f"./{stub}_ADC1.png",
        hist_adc2=f"./{stub}_ADC2.png",
        hist_adc3=f"./{stub}_ADC3.png",
        hist_adc2_adc1=f"./{stub}_ADC2_ADC1.png",
        hist_adc2_adc3_dr1=f"./{stub}_DR1_ADC2_ADC3.png",
        hist_adc2_adc3_dr2=f"./{stub}_DR2_ADC2_ADC3.png",
        hist_adc2_adc1_dr2=f"./{stub}_DR2_ADC2_ADC1.png",

    )

    if not args.meta:
        meta = "N/A"
    else:
        from pickle import load
        meta_data = load(open(args.meta, "rb"))
        stringify_meta(meta_data)
        meta = _META.substitute(**meta_data)

    content = _TEMPLATE.substitute(
        FILENAME=f"{stub}.lst", META=meta, PLOTS=plots
    )
    with open(outfile, "w") as f:
        f.write(content)

if __name__ == "__main__":
    _main()