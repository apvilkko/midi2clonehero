import sys
import re
import os
import math
from constants import *
import curses

state = dict()
state['bufferedEvents'] = []
state['tick'] = 0

EMPTY = ' - '
CYMB = ' X '
PAD = ' O '
C_GREEN = '\033[92m'
C_BLUE = '\033[94m'
C_YELLOW = '\033[93m'
C_RED = '\033[91m'
C_END = '\033[0m'


def header(section, noLeadingNewline=False):
    print(('' if noLeadingNewline else os.linesep) +
          section + os.linesep + '='*len(section) + os.linesep)


def printNote(item):
    red = False
    blue = False
    yellow = False
    green = False
    yellow_cy = False
    green_cy = False
    blue_cy = False
    kick = False
    for event in item[1]:
        parts = event.split(' ')
        if parts[0] != 'N':
            continue
        note = int(parts[1])
        if note == YELLOW_CY:
            yellow_cy = True
        elif note == RED:
            red = True
        elif note == YELLOW:
            yellow = True
        elif note == BLUE:
            blue = True
        elif note == GREEN:
            green = True
        elif note == KICK:
            kick = True
        elif note == GREEN_CY:
            green_cy = True
        elif note == BLUE_CY:
            blue_cy = True
    line = (((PAD) if kick else EMPTY) +
            ((C_RED + PAD + C_END) if red else (EMPTY)) +
            ((C_YELLOW + CYMB + C_END) if yellow_cy else ((C_YELLOW + PAD + C_END) if yellow else EMPTY)) +
            ((C_BLUE + CYMB + C_END) if blue_cy else ((C_BLUE + PAD + C_END) if blue else EMPTY)) +
            ((C_GREEN + CYMB + C_END) if green_cy else ((C_GREEN + PAD + C_END) if green else EMPTY)))
    print(line)


def appendEvent(key, value):
    global state
    eventTime = int(key)
    found = False
    for item in state['bufferedEvents']:
        if item[0] == eventTime:
            item[1].append(value)
            found = True
    if not found:
        state['bufferedEvents'].insert(0, [eventTime, [value]])
    numEmpties = 0
    while eventTime > state['tick']:
        state['tick'] += state['rowLen']
        numEmpties = numEmpties + 1
    numNotes = 0
    while len(state['bufferedEvents']) and state['bufferedEvents'][-1][0] < state['tick']:
        item = state['bufferedEvents'].pop()
        numNotes = numNotes + 1
        printNote(item)
    if numEmpties > numNotes:
        for i in range(numNotes, numEmpties - numNotes):
            print(EMPTY * 5)


def main(filename):
    global state
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    section = None
    firstHeader = True
    i = 0
    for line in lines:
        sectionMatch = re.match(r"\s*\[(\w+)\]\s*", line)
        valueMatch = re.match(r"\s*(.+)\s*=\s*(.+)\s*", line)
        if sectionMatch:
            section = sectionMatch[1]
            if section != 'SyncTrack':
                header(section, firstHeader)
                firstHeader = False
        if valueMatch:
            key = valueMatch[1].strip()
            value = valueMatch[2].lstrip('"').rstrip(
                '"').strip().lstrip(',').strip()
            if section == 'Song':
                print(f"{key:{16}}: {value}")
                if key == 'Resolution':
                    state['resolution'] = int(value)
                    state['rowLen'] = math.floor(state['resolution'] / 4)
            elif 'Drums' in section:
                appendEvent(key, value)
                i = i + 1


if __name__ == "__main__":
    main(sys.argv[1])
