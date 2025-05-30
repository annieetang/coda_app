from music21 import *
from typing import Optional, Union
from music21.musicxml.m21ToXml import ( GeneralObjectExporter )
from ..music.matrix import MusicMatrixRepresentation
import numpy as np
from collections import defaultdict
import os


def get_music21_score_notation(score_filename: str, start_m: Optional[int] = None, end_m: Optional[int] = None) -> stream.Score:
    """
    Returns the music21 score notation for the given score filename.
    Optionally extracts a specific measure range.
    """
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
    MUSIC_DIR = os.path.join(PROJECT_ROOT, "coda_app/music")

    raw_score = converter.parse(MUSIC_DIR + "/" + score_filename)
    score = raw_score

    if not start_m and not end_m:
        return score
    elif not start_m:
        start_m = 1
    elif not end_m:
        end_m = score.parts[0].measure(-1).number

    if start_m < 1 or end_m < 1:
        raise ValueError("Start and end measures must be greater than 0")
    if start_m > score.parts[0].measure(-1).number:
        raise ValueError("Start measure cannot be greater than total number of measures")
    if end_m > score.parts[0].measure(-1).number:
        raise ValueError("End measure cannot be greater than total number of measures")
    if start_m > end_m:
        raise ValueError("Start measure cannot be greater than end measure")
    
    if start_m == end_m:
        excerpt = score.measure(start_m)
    else:
        excerpt = score.measures(start_m, end_m)

    return excerpt

def get_musicxml_from_music21(score: stream.Score) -> Optional[str]:
    """Convert a music21 score to MusicXML string."""
    if score is None:
        return None
    
    if score.isWellFormedNotation():
        gex = GeneralObjectExporter()
        scoreBytes = gex.parse(score)
        scoreBytesUnicode = scoreBytes.decode('utf-8')
        return scoreBytesUnicode
    else:
        raise ValueError("Score is not well-formed. Cannot convert to MusicXML.")

def get_music21_from_matrix(mmr: MusicMatrixRepresentation) -> stream.Part:
    """Reconstructs a music21 stream from the matrix representation."""
    part = stream.Part()
    part.insert(0, instrument.Piano())
    part.insert(0, mmr.key_signature)
    part.insert(0, mmr.time_signature)
    
    num_pitches, num_timesteps = mmr.piano_roll.shape

    if num_pitches == 0:
        return None

    for t in range(num_timesteps):
        duration_to_pitches = defaultdict(list)

        for midi_pitch in range(num_pitches):
            dur = mmr.durations_matrix[midi_pitch, t]
            if dur > 0:
                duration_to_pitches[dur].append(midi_pitch)
        
        for dur, pitches in duration_to_pitches.items():
            quarter_length = dur / mmr.quantization
            offset = t / mmr.quantization

            if len(pitches) > 1:
                new_chord = chord.Chord(pitches)
                for p in new_chord.pitches:
                    if p.accidental and p.accidental == pitch.Accidental('natural'):
                        p.accidental = None
                new_chord.quarterLength = quarter_length
                part.insert(offset, new_chord)
            else:
                new_note = note.Note(pitches[0])
                new_note.quarterLength = quarter_length
                if new_note.pitch and new_note.pitch.accidental == pitch.Accidental('natural'):
                    new_note.pitch.accidental = None
                part.insert(offset, new_note)

    part.makeMeasures(inPlace=True)
    part.makeNotation(inPlace=True, useKeySignature=True)
    part.makeRests(fillGaps=True, inPlace=True)
    part.makeAccidentals(inPlace=True)
    part.makeTies(inPlace=True)
    
    return part 


def get_music21_from_music_matrix_representation(MMR):
    """
    Reconstructs a music21 stream from the matrix representation
    """

    part = stream.Part()
    part.insert(0, instrument.Piano())
    part.insert(0, MMR.key_signature)
    part.insert(0, MMR.time_signature)
    
    num_pitches, num_timesteps = MMR.piano_roll.shape

    if num_pitches == 0:
        return None

    for t in range(num_timesteps):
        duration_to_pitches = defaultdict(list)

        for midi_pitch in range(num_pitches):
            dur = MMR.durations_matrix[midi_pitch, t]
            if dur > 0:
                duration_to_pitches[dur].append(midi_pitch)
        
        for dur, pitches in duration_to_pitches.items():
            quarter_length = dur / MMR.quantization
            offset = t / MMR.quantization

            if len(pitches) > 1:
                new_chord = chord.Chord(pitches)
                # NOTE: manually removed the natural but it also might be wrong in certain cases....
                for p in new_chord.pitches:
                    if p.accidental and p.accidental == pitch.Accidental('natural'):
                        p.accidental = None
                new_chord.quarterLength = quarter_length
                part.insert(offset, new_chord)
            else:
                new_note = note.Note(pitches[0])
                new_note.quarterLength = quarter_length
                # NOTE: manually removed the natural but it also might be wrong in certain cases....
                if new_note.pitch and new_note.pitch.accidental == pitch.Accidental('natural'):
                    new_note.pitch.accidental = None
                part.insert(offset, new_note)

    # make measures does not fill up incomplete measures
    part.makeMeasures(inPlace=True) 
    part.makeNotation(inPlace=True, useKeySignature=True)  
    part.makeRests(fillGaps=True, inPlace=True)
    part.makeAccidentals(inPlace=True)
    part.makeTies(inPlace=True)
    return part

