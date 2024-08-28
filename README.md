# midi2clonehero

`midi2clonehero` is a script that converts standard MIDI (`.mid`) files into [Clone Hero](https://clonehero.net/) chart (`.chart`) files.

## Motivation

This script was mainly developed for getting accurate expert pro drums transcriptions into the game. Why a script instead of using the de facto editor [Moonscraper](https://github.com/FireFox2000000/Moonscraper-Chart-Editor)?

 - Editing in a DAW is faster and more convenient if you're already familiar with the workflow, and you can use any software which can export MIDI
 - A script can create the chart automatically in a semi-intelligent way instead of manual work
 - A MIDI file can act as the more accurate archivable transcription since Clone Hero charts are always an approximation and not necessarily a one-to-one match to the actual performance
 - Multiple chart variants can be created from the same MIDI input

 ## Default functionality

- 4-lane Pro drums output with Expert difficulty
- All hi-hats (closed, pedal, open) are mapped to yellow cymbal
- Other cymbals than hi-hat are never mapped to yellow cymbal
- Rides and crash 2 are mapped to green and all the rest to blue
  - these may be automatically re-mapped inside sections where e.g. crash 2 occurs in between rides (`strict` option can be used to disable this) 
  - the `cymbalflip` option can be used to switch blue/green cymbal around
- Supported MIDI notes out of the box
  - Kick (35, 36)
  - Snare, side stick (37, 38, 40)
  - Toms (41, 43, 45, 47, 48, 50)
  - Hi-hat (42, 44, 46)
  - Crash (49, 57)
  - Ride (51, 53, 59)
  - China (52)
  - Splash (55)

## Setup/installation

[Python](https://www.python.org/) 3 should be installed.

[Initialize virtual environment](https://docs.python.org/3/library/venv.html#creating-virtual-environments), install requirements and activate the virtual environment:
```
python -m venv env
pip install -r requirements.txt
source env/bin/activate
```

On Windows, replace last line with `env\Scripts\activate`

## Usage

In activated virtual environment:

 `python midi2clonehero.py [-h] [--cymbalflip] [--strict] [--meta META] inputfile`

```
positional arguments:
  inputfile     Input MIDI file

options:
  --cymbalflip  Flip blue/green cymbals
  --strict      Map notes strictly without any automatic improvements
  --meta META   Source .chart file for song metadata
```

### Input MIDI file

The input file should be MIDI type 0 (single track) with time signature and tempo events. Any PPQN value should work since it's directly mapped to the chart file `Resolution`.

### Metadata file

Metadata file uses the .chart format also so you can copy and edit this from an existing chart. Only the `[Song]` section is needed. `Resolution` is ignored in the metadata file and read from the midi file instead.

## Notation tips

- Use crashes 1 and 2 (standard MIDI map 49 & 57) and have them mapped to different pads. Double crashes can then be notated conveniently.
- Flams should be notated as 2 consecutive 64th notes (or at least faster than 32nd notes)
- Anything longer than a quarter note is considered a swell for drums. Swells are implemented as special roll lane events.
- Because of limitations of the file format/game implementation, blue tom and blue cymbal can't occur at the same time. If this happens during processing a warning will be displayed. You can try the `cymbalflip` option to resolve this, or manually edit the source MIDI file.

## TODO / wishlist

- flam options
- open hihat options
- automatic accents/ghosts based on velocity
- automatic kick2x mapping
- star power phrases/activations

## References

[Guitar Game Chart Formats](https://github.com/TheNathannator/GuitarGame_ChartFormats)