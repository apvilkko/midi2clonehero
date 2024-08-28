import argparse
import os
import sys
from mido import MidiFile, tempo2bpm
import math
import re

parser = argparse.ArgumentParser(
    description='MIDI file to Clone Hero chart converter.')
parser.add_argument('inputfile', help='Input MIDI file')
parser.add_argument(
    '--cymbalflip', help='Flip blue/green cymbals', default=False, action='store_true')
parser.add_argument(
    '--strict', help='Map notes strictly without any automatic improvements', default=False, action='store_true')
parser.add_argument('--meta', help='Source .chart file for song metadata')

arguments = parser.parse_args()

META_MSGS = ['set_tempo', 'time_signature']
sep = os.linesep
resolution_divisor = 1

KICK = 0
RED = 1
YELLOW = 2
BLUE = 3
GREEN = 4
ORANGE_5 = 4
GREEN_5 = 5
KICK2X = 32
YELLOW_CY = 66
BLUE_CY = 67
GREEN_CY = 68
ROLL_1 = 65

MIDI_C1 = 36
SWELL_THRESHOLD = 1  # quarters
ROLL_INSERT_EVENT_LEN = 0.166  # quarter divisions


def create_midimap(args):
    midi_map = dict()

    RIDE = [MIDI_C1+15, MIDI_C1+17, MIDI_C1+23]
    CRASH1 = [MIDI_C1+13]
    CRASH2 = [MIDI_C1+21]
    crashes = [*CRASH1, *CRASH2]

    # Kick
    midi_map[KICK] = [MIDI_C1, MIDI_C1-1]
    # Snares, clap, side stick
    midi_map[RED] = [MIDI_C1+1, MIDI_C1+2, MIDI_C1+3, MIDI_C1+4]
    # High tom
    midi_map[YELLOW] = [MIDI_C1+12, MIDI_C1+14]
    # Mid tom
    midi_map[BLUE] = [MIDI_C1+11, MIDI_C1+9]
    # Low/floor tom
    midi_map[GREEN] = [MIDI_C1+7, MIDI_C1+5]
    # Hihat (closed, pedal, open)
    midi_map[YELLOW_CY] = [MIDI_C1+6, MIDI_C1+8, MIDI_C1+10]
    # Crash 1, splash, china
    midi_map[BLUE_CY] = [*CRASH1, MIDI_C1+19, MIDI_C1+16]
    # Ride, ride bell, crash 2
    midi_map[GREEN_CY] = [*RIDE, *CRASH2]

    lookup = dict()
    for k, v in midi_map.items():
        for note in v:
            lookup[note] = k

    return {"midi_map": midi_map, "lookup": lookup, "crashes": crashes, "RIDE": RIDE}


def format_value(s):
    if isinstance(s, str):
        return f'"{s}"'
    return s


def output_section(section_name, data, noquote=False):
    out = [f"[{section_name}]", "{"]
    if type(data) is list:
        for item in data:
            arr = item
            if not type(arr[0]) is list:
                arr = [item]
            for i in arr:
                vals = ' '.join([str(x) for x in i[1:]])
                out.append(f"  {i[0]} = {vals}")
    else:
        for k, v in data.items():
            out.append(f"  {k} = {v if noquote else format_value(v)}")
    out.append('}')
    return sep.join(out)


def map_meta_msg(item):
    msg = item['msg']
    count = item['count']
    msgtype = ''
    value = None
    if msg.type == 'set_tempo':
        msgtype = 'B'
        value = round(tempo2bpm(msg.tempo) * 1000)
    elif msg.type == 'time_signature':
        msgtype = 'TS'
        value = f"{msg.numerator} {round(math.log2(msg.denominator))}"
    else:
        raise ValueError('bad msg type')
    return [count, msgtype, value]


last_output = None


def output_note(item, config):
    global last_output
    count = item['count']
    msgtype = item['mapped']
    notelen = item['length']
    length = 0 if notelen < (SWELL_THRESHOLD * config["ppqn"]) else notelen

    if config["args"].cymbalflip:
        if msgtype == BLUE_CY:
            msgtype = GREEN_CY
        elif msgtype == GREEN_CY:
            msgtype = BLUE_CY

    out = [[count, 'N', msgtype, length]]
    if last_output and last_output[0] != count:
        last_output = None
    if last_output and (
        (last_output[1] == BLUE_CY and msgtype == BLUE) or (
            last_output[1] == BLUE and msgtype == BLUE_CY)
    ):
        sys.stderr.write(
            f'Warning: Tick {count}: Blue cymbal/pad overlap! Try enabling/disabling cymbalflip option or adjust input file.' + sep)
    last_output = [count, msgtype]
    if msgtype in [YELLOW_CY, BLUE_CY, GREEN_CY]:
        out.append([count, 'N', msgtype-64, length])
    if length > 0:
        out.append([count, 'S', ROLL_1, length])
        step = math.ceil(ROLL_INSERT_EVENT_LEN * config["ppqn"])
        upper_limit = count + length
        n = count + step
        while n <= upper_limit:
            out.append([n, 'N', msgtype, 0])
            if msgtype in [YELLOW_CY, BLUE_CY, GREEN_CY]:
                out.append([n, 'N', msgtype-64, 0])
            n = n + step
    return out


def map_note(item, config):
    msg = item['msg']
    count = item['count']
    msgtype = config["midimap"]["lookup"].get(msg.note)
    if msgtype is None:
        raise ValueError('unmapped msgtype ' + str(msg))
    return {"midi": msg, "count": count, "mapped": msgtype, "length": item['length']}


def is_double_cymbal(i, items):
    cymbals = [GREEN_CY, BLUE_CY]
    if not items[i]["mapped"] in cymbals:
        return False
    other_items = [x for x in items if items[i]
                   ["count"] == x["count"] and items[i] != x]
    return len(other_items) and any([x for x in other_items if x["mapped"] in cymbals])


def maybe_improve_mapping(items, config):
    window_len = config["ppqn"] * 2
    crashes = config["midimap"]["crashes"]
    RIDE = config["midimap"]["RIDE"]

    for i, x in enumerate(items):
        if x["midi"].note in crashes and not is_double_cymbal(i, items):
            window = [y for y in items if y["count"] -
                      window_len <= x["count"] < y["count"] + window_len]
            rides_in_window = [c for c in window if c["midi"].note in RIDE]
            rides_mapped = [r["mapped"] for r in rides_in_window]
            # are rides mapped to the same as this (x) crash? => flip
            if x["mapped"] in rides_mapped:
                if x["mapped"] == GREEN_CY:
                    x["mapped"] = BLUE_CY
                elif x["mapped"] == BLUE_CY:
                    x["mapped"] = GREEN_CY
    return items


def patch_length(msg, notes, count):
    pos = len(notes) - 1
    while pos >= 0:
        if msg.note == notes[pos]["msg"].note:
            notes[pos]["length"] = count - notes[pos]["count"]
            break
        pos = pos - 1


def read_meta(filename):
    if not filename:
        return None
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    section = None
    out = dict()
    for line in lines:
        sectionMatch = re.match(r"\[(\w+)\]", line)
        if sectionMatch:
            section = sectionMatch.group(1)
        itemMatch = re.search(r"(\w+)\s*=\s*(.+)", line)
        if section is None or section == "Song" and itemMatch:
            key = itemMatch.group(1)
            value = itemMatch.group(2)
            if key not in ["Resolution"]:
                out[key] = value
    return out


def main(args):
    mid = MidiFile(args.inputfile)
    ppqn = round(mid.ticks_per_beat / resolution_divisor)

    meta_msgs = []
    notes = []
    count = 0

    metafile = read_meta(args.meta)

    config = {
        "ppqn": ppqn,
        "midimap": create_midimap(args),
        "args": args
    }

    for _, track in enumerate(mid.tracks):
        for msg in track:
            count += round(msg.time / resolution_divisor)
            if msg.type == 'note_on':
                notes.append({"msg": msg, "count": count, "length": 0})
            elif msg.type == 'note_off':
                patch_length(msg, notes, count)
            elif msg.is_meta and (msg.type in META_MSGS):
                meta_msgs.append({"msg": msg, "count": count})

    difficulty = 'Expert'
    mapped = [map_note(x, config) for x in notes]
    if not args.strict:
        mapped = maybe_improve_mapping(mapped, config)
    outmeta = dict(metafile if metafile else dict())
    outmeta["Resolution"] = ppqn
    output = [
        output_section('Song', outmeta, True),
        output_section('SyncTrack', [map_meta_msg(x) for x in meta_msgs]),
        output_section(f"{difficulty}Drums", [
                       output_note(x, config) for x in mapped])
    ]
    print(sep.join(output))


if __name__ == "__main__":
    main(arguments)
