"""
Script for converting MPA-3 lst files into HDF5 files using h5py.
"""
import os
import sys
import re
import argparse
import numpy as np
import numba as nb
from tqdm import tqdm
import h5py

from _common import (
    INVALID_ADC_VALUE,
    LST_FILE_APPROX_CHUNK,
    default_argparser,
    check_input,
    check_output,
)

FLAG_LISTDATA = "[LISTDATA]"
BINFLAG_TIMER_LITTLE_ENDIAN = b"\x00\x40"
SYNCFLAG = np.array([0xffff, 0xffff], dtype="u2")


def _main():
    parser = argparse.ArgumentParser(
        description="Convert an MPA-3 list file into HDF5 format.",
        parents=[default_argparser]
    )
    args = parser.parse_args()
    fin = check_input(args.file)
    fout = args.out
    if not fout:
        fout = fin.replace(".lst", ".h5")
    fout = check_output(fout, args.yes)
    convert(fin, fout)
    sys.exit(0)

def _read_header(f):
    header = []
    while True:
        ln = f.readline()
        ln = ln#.decode("utf-8")#.strip()
        if ln.decode("utf-8").strip() == FLAG_LISTDATA:
        # if ln == FLAG_LISTDATA:
            break
        header.append(ln)
    return header

def _parse_header(f):
    P_NORMAL_ENTRY = r"^(.+)=(.+)$"
    P_SECTION = r"^\[(.+)\]\s?(.*)$"
    header = _read_header(f)
    out = {"ROOT":{}}
    active = out["ROOT"]
    unparsed_cnt = 0
    duplicate_cnt = 0
    for row in header:
        row = row.decode("ASCII").strip()
        m = re.match(P_NORMAL_ENTRY, row)
        if m:
            val = m[2]
            try:
                val = int(val)
            except ValueError:
                try:
                    val = float(val)
                except ValueError:
                    pass
            if m[1] in active.keys():
                active[f"{m[1]}_{duplicate_cnt}"] = val
                duplicate_cnt += 1
            else:
                active[m[1]] = val
            continue

        m = re.match(P_SECTION, row)
        if m:
            out[m[1]] = {}
            active = out[m[1]]
            if m[2]:
                active["SECTIONHEADER"] = m[2]
            unparsed_cnt = 0
            duplicate_cnt = 0
            continue

        active[f"UNPARSED_{unparsed_cnt}"] = row
        unparsed_cnt += 1
    return out

def _read_binary_chunk(f, filesize, approx_bytes=LST_FILE_APPROX_CHUNK):
    if approx_bytes % 2 == 1:
        approx_bytes -= 1 # make sure its even numbered
    remaining = filesize - f.tell()
    if remaining < approx_bytes:
        bts = f.read(remaining)
    else:
        bts = f.read(approx_bytes)
        while True:
            nxt = f.read(4)
            if nxt[2:] == BINFLAG_TIMER_LITTLE_ENDIAN:
                f.seek(-4, 1)
                break
            bts += nxt
            if f.tell() == filesize:
                break
    return bts

def _array_from_binary_chunk(chnk):
    arr = np.frombuffer(chnk, dtype="<u2")
    arr = arr.reshape((arr.size//2, 2))
    return arr

@nb.njit(cache=True)
def _extract_event_data(a):
    # estim_sync = _estimate_syncflag_count(a)
    n_timer = 0
    n_sync = 0
    n_event = 0
    k = 0
    l = 0
    out_event_id = np.zeros(a.size, dtype=np.uint32)
    out_time = np.zeros(a.size, dtype=np.uint32)
    out_value = np.zeros(a.size, dtype=np.uint16)
    out_channel = np.zeros(a.size, dtype=np.uint8)
    while True:
        if k >= a.shape[0]:
            break
        r = a[k]

        if r[1] == 0x4000:
            n_timer += 1
            k += 1

        elif np.all(r == SYNCFLAG):
            n_sync += 1
            k += 1
            while True:
                if k >= a.shape[0]:
                    break

                adc_has_data = a[k, 0]
                if adc_has_data == 0:
                    k += 1
                    continue
                event_flags = a[k, 1]
                event_bit = (event_flags>>14) & 0x01 # bit 30 of double word, SHOULD BE 0
                dummy_bit = (event_flags>>15) & 0x01 # bit 31 of double word
                rtc_bit   = (event_flags>>12) & 0x01 # bit 28 of double word
                if event_bit:
                    break
                k += 1

                n_data = 0
                for i in range(16):
                    n_data += (adc_has_data>>i) & 0x01
                n_bytes = n_data + dummy_bit + 3*rtc_bit
                adc_data = a[k:k+n_bytes//2].flatten()[dummy_bit + 3*rtc_bit:]
                c = 0
                for i in range(16):
                    if (adc_has_data >> i) & 0x01:
                        out_time[l] = n_timer
                        out_value[l] = adc_data[c]
                        out_channel[l] = i + 1  #Index ADCs starting with 1
                        out_event_id[l] = n_event
                        l += 1
                        c += 1
                    if c == n_data:
                        break
                n_event += 1
                k += n_bytes//2
        else: # Something is fishy, just press on
            k+=1
    return out_event_id[:l], out_time[:l], out_channel[:l], out_value[:l]

@nb.njit(cache=True)
def _assemble_output_array(event_id, time, channel, value):
    adcs = np.unique(channel)
    _col = {}
    for k in range(adcs.size):
        _col[adcs[k]] = k
    n_events = np.unique(event_id).size
    out_time = np.zeros(n_events, dtype=np.int32)
    out_value = np.zeros((n_events, adcs.size), dtype=np.uint16)
    out_value[:] = INVALID_ADC_VALUE
    id0 = event_id[0]
    for k in range(event_id.size):
        e_id = event_id[k] - id0
        out_time[e_id] = time[k]
        out_value[e_id, _col[channel[k]]] = value[k]
    return adcs, out_time, out_value

@nb.njit(cache=True)
def _explore_event_data(a):
    # estim_sync = _estimate_syncflag_count(a)
    n_timer = 0
    n_sync = 0
    n_event = 0
    adc_has_data_total = 0x00
    k = 0
    while True:
        if k >= a.shape[0]:
            break
        r = a[k]

        if r[1] == 0x4000:
            n_timer += 1
            k += 1

        elif np.all(r == SYNCFLAG):
            n_sync += 1
            k += 1
            while True:
                if k >= a.shape[0]:
                    break

                event_flags = a[k, 1]
                event_bit = (event_flags>>14) & 0x01 # bit 30 of double word, SHOULD BE 0
                dummy_bit = (event_flags>>15) & 0x01 # bit 31 of double word
                rtc_bit   = (event_flags>>12) & 0x01 # bit 28 of double word
                if event_bit:
                    break
                adc_has_data = a[k, 0]
                if adc_has_data == 0:
                    k += 1
                    continue
                adc_has_data_total = adc_has_data_total | adc_has_data

                k += 1
                n_data = 0
                for i in range(16):
                    n_data += (adc_has_data>>i) & 0x01
                n_bytes = n_data + dummy_bit + 3*rtc_bit
                n_event += 1
                k += n_bytes//2
        else: # Something is fishy, just press on
            k+=1
    return n_timer, n_sync, n_event, adc_has_data_total

def explore_list_file(fin):
    n_timer = 0
    n_sync = 0
    n_event = 0
    adc_has_data = 0x00
    filesize = os.path.getsize(fin)
    with open(fin, mode="rb") as f: #Prerun for exploration purposes
        header = _read_header(f)
        tq = tqdm(total=filesize, unit="B", desc="Analysis")
        curs = f.tell()
        tq.update(curs)
        while True:
            chnk = _read_binary_chunk(f, filesize)
            tq.update(f.tell()-curs)
            curs = f.tell()
            arr = _array_from_binary_chunk(chnk)

            _n_timer, _n_sync, _n_event, _adc_has_data =  _explore_event_data(arr)
            n_timer += _n_timer
            n_sync += _n_sync
            n_event += _n_event
            adc_has_data = adc_has_data | _adc_has_data

            exhausted = f.tell() == filesize
            if exhausted:
                break
        tq.close()
    relevant_adcs = []
    for k in range(16):
        if adc_has_data >> k & 0x01:
            relevant_adcs.append(k+1) #Index ADCs starting with 1
    return {
        "n_event":n_event,
        "n_timer":n_timer,
        "n_sync":n_sync,
        "relevant_adcs":relevant_adcs
    }

def convert(fin, fout):
    explore = explore_list_file(fin)
    filesize = os.path.getsize(fin)
    with open(fin, mode="rb") as f, h5py.File(fout, mode="w") as o:
        header = _parse_header(f)
        h5cfg = o.create_group("CFG")
        for grpk, grp in header.items():
            if not grpk in h5cfg.keys():
                h5cfg.create_group(grpk)
            for k, v in grp.items():
                h5cfg[grpk].attrs[k] = v

        h5events = o.create_group("EVENTS")
        h5events.create_dataset("TIME", shape=(explore["n_event"],), dtype=np.uint32)
        for n in explore["relevant_adcs"]:
            h5events.create_dataset(f"ADC{n}", shape=(explore["n_event"],), dtype=np.uint16)
        tq = tqdm(total=filesize, unit="B", desc="Rewrite ")
        curs = f.tell()
        tq.update(curs)
        last_time = 0
        last_event_id = 0
        while True:
            chnk = _read_binary_chunk(f, filesize)
            tq.update(f.tell()-curs)
            curs = f.tell()
            arr = _array_from_binary_chunk(chnk)

            event_id, time, channel, value = _extract_event_data(arr)
            if event_id.size > 0:
                event_id += last_event_id
                time += last_time

                channel, time, value = _assemble_output_array(event_id, time, channel, value)
                h5events["TIME"].write_direct(np.ascontiguousarray(time), dest_sel=np.s_[event_id[0]:event_id[-1]+1])
                for n, c in enumerate(channel):
                    h5events[f"ADC{c}"].write_direct(np.ascontiguousarray(value[:, n]), dest_sel=np.s_[event_id[0]:event_id[-1]+1])

                last_event_id = event_id[-1]
                last_time = time[-1]
            exhausted = f.tell() == filesize
            if exhausted:
                break
        tq.close()


if __name__ == "__main__":
    _main()
