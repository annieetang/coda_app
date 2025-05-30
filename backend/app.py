from flask import Flask, request, Response, render_template
import os
from flask_cors import CORS
from music21.musicxml.m21ToXml import ( GeneralObjectExporter )
from music21 import *
import numpy as np
import math
from flask import jsonify
from collections import defaultdict
from .redis_db import RedisDatabase
from io import BytesIO
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

SOUNDSLICE_APP_ID = os.getenv("SOUNDSLICE_APP_ID")
SOUNDSLICE_PASSWORD = os.getenv("SOUNDSLICE_PASSWORD")

app = Flask(__name__)
CORS(app)

# Initialize Redis database
db = RedisDatabase()

# Configure upload settings
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "music")
ALLOWED_EXTENSIONS = {'xml', 'musicxml', 'mxl'}

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# TODO: currentl not working properly
@app.route("/upload_score", methods=["POST"])
def upload_score():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path_to_save = os.path.join(UPLOAD_FOLDER, filename)
            
            # Check if file already exists
            if os.path.exists(file_path_to_save):
                return jsonify({'error': 'File already exists'}), 400
            
            try:
                print("trying to save file, ", file_path_to_save)
                file.save(file_path_to_save)
                # Use file's stream directly with music21
                temp_score = converter.parse(file_path_to_save)
                
                return jsonify({'message': 'File uploaded successfully'}), 200
            except Exception as e:
                return jsonify({'error': f'Invalid MusicXML file: {str(e)}'}), 400
        
        return jsonify({'error': 'Invalid file type'}), 400
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route("/list_files", methods=["GET"])
def list_files():
    # music_folder = os.path.join(app.static_folder, "music")
    music_folder = "../music"
    files = [
        f for f in os.listdir(music_folder)
        if f.lower().endswith((".mxl", ".musicxml"))
    ]
    json_files = jsonify(files)
    return json_files

@app.route("/get_measure_from_second", methods=["POST"])
def get_measure_from_second():
    # takes filename and second as input
    # returns the measure number
    data = request.get_json()
    # print(data)
    score_name = data.get("filename")
    second = data.get("second")
    # print(score_name, second)

    score_name = "../music/" + score_name

    # get the score notation
    score = get_music21_score_notation(score_name)
    # print("got score")
    # get the time signature   
    time_signature = score.recurse().getElementsByClass(meter.TimeSignature)[0]
    # print("got time signature")
    # print(time_signature)
    # get tempo marking if it exists
    tempo_marks = score.recurse().getElementsByClass(tempo.MetronomeMark)
    if tempo_marks:
        tempo_marking = tempo_marks[0]
    else:
        tempo_marking = None
    # print("got tempo marking")
    # print(tempo_marking)

    # get the tempo in bpm
    if tempo_marking:
        bpm = tempo_marking.number
    else:
        bpm = 120

    # get the time signature in beats per measure
    beats_per_measure = time_signature.numerator
    # get the time signature in beat unit
    # beat_unit = time_signature.denominator

    # print(second, bpm, beats_per_measure, beat_unit)

    # calculate the number of seconds per beat
    measure_number = math.floor(second / 60 * bpm / beats_per_measure) + 1
    print("measure number: ", measure_number)

    # print(measure_number)   
    return jsonify({"measure_number": measure_number})

    

from soundsliceapi import Client, Constants

scoreToScorehash = defaultdict(str)

# this isn't doing anything right now
@app.route("/slice_callback", methods=["POST"])
def slice_callback():
    print("Slice callback received")
    data = request.get_json()
    print("Callback data:", data)
    
    scorehash = data.get("scorehash")
    success = data.get("success")
    error = data.get("error")
    
    if success == "2":  # Error case
        print(f"Error processing notation: {error}")
        return Response(status=400)
    
    print(f"Successfully processed notation for scorehash {scorehash}")
    return Response(status=200)

def load_hashes_from_redis():
    """Load hashes from Redis into memory"""
    global scoreToScorehash
    scoreToScorehash = defaultdict(str, db.get_all_hashes())

@app.before_request
def before_first_request():
    """Load hashes into memory before each request"""
    print("Loading score hashes from Redis...")
    load_hashes_from_redis()
    print("Loaded score hashes from Redis")

@app.route("/get_slicehash", methods=["POST"])
def get_slicehash():
    print("Getting slice hash...")
    data = request.get_json()
    print(data)
    score_name = data.get("filename")
    print(score_name)
    print(scoreToScorehash)
    if score_name in scoreToScorehash:
        print("Score found in Redis, returning slice hash...")
        return jsonify({"slicehash": scoreToScorehash[score_name]})
    else:
        # return jsonify({"slicehash": None})
        print("Score not found, creating and uploading new slice...")
        create_and_upload_slice(score_name)
        return jsonify({"slicehash": scoreToScorehash[score_name]})

def create_and_upload_slice(score_name):
    print("Creating and uploading slice...")
    client = Client(SOUNDSLICE_APP_ID, SOUNDSLICE_PASSWORD)
    
    # Create a new slice
    res = client.create_slice(
        name=score_name,
        artist="Dummy Artist",
        embed_status=Constants.EMBED_STATUS_ON_ALLOWLIST,
    )
    print("Slice created:", res)
    scorehash = res['scorehash']
    
    # Get the XML content
    data = request.get_json()
    musicxml = data.get("musicxml", "")
    
    if musicxml:
        # If musicxml is provided in the request, create a BytesIO object
        fp = BytesIO(musicxml.encode('utf-8'))
    else:
        # If no musicxml provided, open the file directly
        fp = open(score_name, "rb")
    
    try:
        # Upload the notation using the client library
        client.upload_slice_notation(
            scorehash=scorehash,
            fp=fp,
            callback_url="http://127.0.0.1:5000/slice_callback"
        )
        print("Notation upload initiated")
    finally:
        fp.close()
    
    # Save the score hash
    db.save_hash(score_name, scorehash)
    scoreToScorehash[score_name] = scorehash
    
    return scorehash
    

@app.route("/load_soundslice", methods=["POST"])
def load_soundslice():
    print("Loading soundslice...")
    data = request.get_json()
    print(data)
    client = Client("gFvbBEoWaXZwHgpKundgrWzgbvaXnLHR", "]nR7VIwxD:]qW~W'N(ZUtY>$v(|!rij2")
    # data = request.get_json()
    # score_name = data.get("filename")

    dummy_score_name = "test_score.mxl"
    score_name = "test score"

    # try to get the score hash from the soundslice API
    # if the score hash is not found, create a new slice, and upload the notation to that slice
    # if the score hash is found, return the score hash
    if score_name in scoreToScorehash:
        return jsonify({"score_hash": scoreToScorehash[score_name]})
    else:
        # list all slices for now
        print("listing slices...")
        res = client.list_slices()
        print(res)

        print("creating folder...")
        res = client.list_folders()
        print(res)


        # get the score hash from the soundslice API
        # res = client.create_slice(
        #     name="Test Score",
        #     artist="Dummy Artist",
        #     embed_status=Constants.EMBED_STATUS_ON_ALLOWLIST,
        #     # folder_id="133976",
        # )
        # print(res)

        # upload the notation to the slice
        res = client.upload_slice_notation(
            scorehash = "LTPXc",
            fp=open('../music/' + dummy_score_name, "rb"),
            callback_url="http://127.0.0.1:5000/slice_callback"
        )
        print(res)

        """
        [{'name': 'Test Score', 'artist': 'Dummy Artist', 'url': '/slices/9TPXc/', 'scorehash': '9TPXc', 'slug': '2480642', 'status': 1, 'embed_status': 4, 'can_print': False, 'print_status': 1, 'has_notation': False, 'show_notation': True, 'recording_count': 0, 'folder_id': 0, 'embed_url': '/slices/9TPXc/embed/'}, 
        
        {'name': 'Test Score', 'artist': 'Dummy Artist', 'url': '/slices/PTPXc/', 'scorehash': 'PTPXc', 'slug': '2480641', 'status': 1, 'embed_status': 4, 'can_print': False, 'print_status': 1, 'has_notation': False, 'show_notation': True, 'recording_count': 0, 'folder_id': 0, 'embed_url': '/slices/PTPXc/embed/'}, 
        
        {'name': 'Test Score', 'artist': 'Dummy Artist', 'url': '/slices/LTPXc/', 'scorehash': 'LTPXc', 'slug': '2480639', 'status': 1, 'embed_status': 4, 'can_print': False, 'print_status': 1, 'has_notation': False, 'show_notation': True, 'recording_count': 0, 'folder_id': 0, 'embed_url': '/slices/LTPXc/embed/'}, 
        
        {'name': 'sonata01-1.xml', 'artist': '', 'url': '/slices/NfdXc/', 'scorehash': 'NfdXc', 'slug': '2460796', 'status': 1, 'embed_status': 4, 'can_print': False, 'print_status': 1, 'has_notation': True, 'show_notation': True, 'recording_count': 0, 'folder_id': 0, 'embed_url': '/slices/NfdXc/embed/'}]
        """

        print("relisting slices...")
        print(client.list_slices())

    return jsonify({"score_hash": "dummy_score_hash"})


@app.route("/save_musicxml_to_file", methods=["POST"])
def save_musicxml_to_file():
    data = request.get_json()
    score_name = data.get("filename")
    musicxml = data.get("musicxml")
    print(score_name)

    try:
        print("hi")
        # save the musicxml to the file
        with open(score_name, 'w') as f:
            f.write(musicxml)
        f.close()
        # print("Saved musicxml to file")
    except Exception as e:
        print(f"Error saving musicxml to file: {e}")
        return jsonify({"success": False, "error": str(e)})
    
    return jsonify({"success": True})


@app.route("/generate", methods=["POST"])
def generate_exercises():
    data = request.get_json()
    score_name = data.get("filename")
    start_measure = data.get("start_measure")
    end_measure = data.get("end_measure")

    # get the score excerpt in music21 notation
    score_excerpt = get_music21_score_notation(score_name, start_measure, end_measure)

    # generate all exercises possible from the original score excerpt, exercises is a hashmap
    exercises = get_all_exercises(score_excerpt)

    # add to the json a section for the start and end measures
    json = {
        "exercises": exercises,
        "start_measure": start_measure,
        "end_measure": end_measure
    }

    return jsonify(json)

# common functions
def get_music21_score_notation(score_filename, start_m=None, end_m=None):
    """
    Returns the music21 score notation for the given score filename.

    Expands the score if there is a repeat bar to accurately return the measures between start_m and end_m based on time duration from the frontend determination of start and end measure.

    If start_m and end_m are not provided, the entire score is returned.
    If start_m and end_m are provided, the score is sliced to return only the measures between start_m and end_m.
    If start_m is not provided, it defaults to 1.
    If end_m is not provided, it defaults to the last measure of the score.

    Any invalid start_m or end_m combination will raise an exception.
    """
    raw_score = converter.parse(score_filename)

    # if there is a repeat, expand the score by checking if there is a Repeat bar in any part of recurse
    # TODO: fix this, repeat gets broken when select the first "repeated" section of a score, but no problem if it selects the "second" repeat of the score
    # if raw_score.recurse().getElementsByClass(bar.Repeat):
    #     print("there is a repeat")
    #     expanded_score = raw_score.expandRepeats()
    #     score = expanded_score
    # else:
    #     score = raw_score

    score = raw_score

    if not start_m and not end_m:
        return score
    elif not start_m:
        start_m = 1
    elif not end_m:
        end_m = score.parts[0].measure(-1).number

    print("start and end measures: ", end="")
    print(start_m, end_m)

    print(score.parts[0].measure(-1).number)

    if start_m < 1 or end_m < 1:
        raise Exception("start and end measures invalid. start measure and end measure must be greater than 0")
    if start_m > score.parts[0].measure(-1).number:
        raise Exception("start and end measures invalid. start measure cannot be greater than total number of measures")
    if end_m > score.parts[0].measure(-1).number:
        raise Exception("start and end measures invalid. end measure cannot be greater than total number of measures")
    if start_m > end_m:
        raise Exception("start and end measures invalid. start measure cannot be greater than end measure")
    
    if start_m == end_m:
        excerpt = score.measure(start_m)
    else:
        excerpt = score.measures(start_m, end_m)


    excerpt.show('text')

    return excerpt

def get_musicxml_from_music21(score):
    if score is None:
        return None
    
    if score.isWellFormedNotation():
        gex = GeneralObjectExporter()
        scoreBytes = gex.parse(score)
        scoreBytesUnicode = scoreBytes.decode('utf-8')
        return scoreBytesUnicode
    else:
        raise Exception("Score is not well-formed. Cannot convert to MusicXML.")

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
    # part.show('text')
    return part

class Score:
    def __init__(self, filename):
        self.filename = filename
        self.score_mxl = converter.parse(filename)
        self.exercises = get_all_exercises(self.score_mxl)
        # self.bpm = 

    def get_exercises(self):
        return self.exercises

    def get_score_mxl(self):
        return self.score_mxl

# TODO: change name to make more sense
class MusicMatrixRepresentation:
    def __init__(self, key_signature, time_signature, quantization, piano_roll, onset_map, durations_matrix):
        self.key_signature = key_signature
        self.time_signature = time_signature
        self.quantization = quantization
        self.piano_roll = piano_roll
        self.onset_map = onset_map
        self.durations_matrix = durations_matrix

class ExerciseScore:
    def __init__(self, music21_score):
        self.original_stream = music21_score

        key_signatures = self.original_stream.recurse().getElementsByClass(key.KeySignature)
        self.key_signature = key_signatures[0] if key_signatures else None
        self.time_signature = self._extract_time_signature() # music21 time signature object
        self.quantization = self._calculate_quantization() # int

        self.parts = self._extract_parts() # list of ExercisePart objects

    
    def _extract_time_signature(self):
        """
        Extract the time signature from the music21 line.
        Currently only supports one time signature per line. 

        # TODO: handle multiple time signatures
        """
        time_signature = self.original_stream.recurse().getElementsByClass(meter.TimeSignature)
        if time_signature:
            return time_signature[0]
        else:
            return None

    # TODO: need to consider if there isn't a time signature
    def _calculate_quantization(self):
        """
        Calculate the quantization based on the time signature and the shortest note value in the excerpt.
        """
        durations = [
            n.duration.quarterLength
            for n in self.original_stream.recurse().notesAndRests
            if n.duration.quarterLength > 0
        ]

        if not durations:
            return None
    
        shortest = min(durations)
        quantization = math.ceil(1 / shortest)

        return quantization * self.time_signature.numerator

    def _extract_parts(self):
        """
        Create and return a list of ExercisePart objects from the score (music21 stream notation).
        """

        # TODO: if the part doesn't have notes, don't process it
        return [ExercisePart(part, self.key_signature, self.time_signature, self.quantization) for part in self.original_stream.parts]

class ExercisePart():
    def __init__(self, music21_part, key_signature, time_signature, quantization):
        self.original_stream = music21_part
        self.key_signature = key_signature
        self.time_signature = time_signature
        self.quantization = quantization
        self.lines = self._extract_lines() # list of ExerciseLine objects
    
    def _extract_lines(self):
        # this extracts the voices from the parts
        split_voices = self.original_stream.voicesToParts()
        lines = [ExerciseLine(line, self.key_signature, self.time_signature, self.quantization) for line in split_voices.parts]
        return lines
        # TODO: also get rid of parts with no notes in it

# TODO: change this name to "Voice" instead of "Line"?????
class ExerciseLine:
    def __init__(self, music21_line, key_signature, time_signature, quantization):
        self.original_stream = music21_line  # music21 stream object
        self.key_signature = key_signature
        self.time_signature = time_signature
        self.quantization = quantization

        # might have to move some functions around and whatever but keep like this for now
        piano_roll, onset_map, durations_matrix = self._create_matrices() # numpy arrays

        self.music_matrix_representation = MusicMatrixRepresentation(
            key_signature = key_signature,
            time_signature=time_signature,
            quantization=quantization,
            piano_roll=piano_roll,
            onset_map=onset_map,
            durations_matrix=durations_matrix
        )

        self.exercises = self.generate_exercises() # map of exercise name to music21 stream object

    def _create_matrices(self):
        # Get the measure offsets
        measure_offset = {}
        for el in self.original_stream.recurse(classFilter=('Measure')):
            measure_offset[el.measureNumber] = el.offset
        
        # Get the duration of the part
        duration_max = 0
        for el in self.original_stream.recurse(classFilter=('Note', 'Chord')):
            t_end = self._get_end_time(el,measure_offset,self.quantization)
            if(t_end>=duration_max):
                duration_max=t_end

        # Get the pitch and offset+duration
        piano_roll = np.zeros((128,math.ceil(duration_max)))

        # TODO: handle / account for the ties
        onset_map = np.zeros((128,math.ceil(duration_max)))

        durations_matrix = np.zeros((128,math.ceil(duration_max)))
        if duration_max == 0: 
            return piano_roll, onset_map, durations_matrix
        
        for el in self.original_stream.recurse(classFilter=('Note', 'Chord')):
            note_start = self._get_start_time(el,measure_offset,self.quantization)
            note_end = self._get_end_time(el,measure_offset,self.quantization)

            if el.isChord:
                for pitch in el.pitches:
                    midi = pitch.midi
                    onset_map[midi, note_start] = 1
                    piano_roll[midi, note_start:note_end] = 1
            else:
                midi = el.pitch.midi
                if el.tie != tie.Tie('stop'):
                    onset_map[midi, note_start] = 1
                piano_roll[midi,note_start:note_end] = 1

        rows, cols = piano_roll.shape

        for i in range(rows):
            onset_indices = np.where(onset_map[i] == 1)[0]
            for idx, start in enumerate(onset_indices):
                end = onset_indices[idx + 1] if idx + 1 < len(onset_indices) else cols
                # Sum the 1s in the piano roll between onset and next onset or end of row
                duration = np.sum(piano_roll[i, start:end])
                durations_matrix[i, start] = duration

        # plot_mtx(piano_roll)
        
        return piano_roll, onset_map, durations_matrix

    def _get_start_time(self, el,measure_offset,quantization):
        if (el.offset is not None) and (el.measureNumber in measure_offset):
            return int(math.ceil((measure_offset[el.measureNumber] + el.offset)*quantization))
        return None

    def _get_end_time(self, el,measure_offset,quantization):
        if (el.offset is not None) and (el.measureNumber in measure_offset):
            return int(math.ceil((measure_offset[el.measureNumber] + el.offset + el.duration.quarterLength)*quantization))
        return None

    def generate_exercises(self):
        """
        Generate exercises from the music matrix representation. Exercises are returned as music21 streams.
        """
        # exercises = []
        exercises = defaultdict(list)

        # try:

        # generated dotted exercises
        dotted_duration_patterns = [[1.5, 0.5], [0.5, 1.5]]
        for pattern in dotted_duration_patterns:
            dotted = self.generate_dotted_exercise(pattern)
            
            # exercises.append(dotted)
            exercises['dotted'].append(dotted)

        # generate the chord exercise
        # maybe just have this be all multiples of the numerator or denominator ranging from min quantization level to bar level? TODO
        level_of_chordification = set([self.music_matrix_representation.quantization, self.music_matrix_representation.quantization * 2, self.music_matrix_representation.quantization // 2, self.music_matrix_representation.time_signature.denominator, self.music_matrix_representation.time_signature.denominator * 2, self.music_matrix_representation.time_signature.denominator // 2, self.music_matrix_representation.time_signature.numerator * self.music_matrix_representation.time_signature.denominator])
        print(level_of_chordification)
        for chord_level in level_of_chordification:
            chordify = self.generate_chordify_exercise(chord_level)
            if chordify is not None:
                print(chord_level, "works")
                exercises['chordified'].append(chordify)

        # generate slowed down exercises
        factor_of_slowdown = [2, 4] # i.e., 2 is twice as slow, 4 is four times as slow
        for factor in factor_of_slowdown:
            slowed_down = self.generate_slowed_down_exercise(factor)
            if slowed_down is not None:
                exercises['slowed_down'].append(slowed_down)

        return exercises

        # except Exception as e:
        #     print(f"Error generating exercises: {e}")
        #     return []
    
    def generate_dotted_exercise(self, dotted_duration_pattern):
        """
        Generate a dotted exercise from the music matrix representation.
        """
        # 1. flatten the duration- assumes that there is one linear line representation of duration 
        # (if there are multiple notes happening, they are all of the same duration)
        flattened_durations_list, pitches_hashmap = self._flatten_durations()

        # 2. find the ranges where there is an even pattern to dottify
        ranges = self._find_duplicate_length_ranges(flattened_durations_list)
        # print(ranges)

        # 3. iterate through the given duration list and modify the rhythm durations in the flattened duration list
        dotted_flat_durations = flattened_durations_list.copy()
        n = len(dotted_duration_pattern)

        # print(ranges)

        # only works if durations are integers
        for start_time, end_time, num_notes in ranges: # [(0, 8, 4)]
            print(start_time, end_time, num_notes)

            dotted_factor_i = 0

            old_rhythm_phrase = flattened_durations_list[start_time:end_time]
            new_rhythm_phrase = [0] * (end_time - start_time)

            # [2,0,2,0,2,0,2,0]
            # [3,0,0,1,3,0,0,1]
            old_rhythm_i = 0
            t = start_time
            new_rhythm_i = 0
            while t < end_time and new_rhythm_i < len(new_rhythm_phrase) and old_rhythm_i < len(old_rhythm_phrase):
                old_duration = old_rhythm_phrase[old_rhythm_i]
                new_dur = old_duration * dotted_duration_pattern[dotted_factor_i]
                # print(t, old_rhythm_i)
                # print(t, old_duration, new_dur)
                if new_dur <= 0:
                    print("Invalid duration, skipping...")
                    break
                new_dur = int(new_dur)
                # print(t, new_rhythm_phrase, new_dur)
                new_rhythm_phrase[new_rhythm_i] = new_dur

                # update hashmap of time to pitches
                pitches_to_update = pitches_hashmap[start_time + old_rhythm_i]
                pitches_hashmap[start_time + old_rhythm_i] = []
                pitches_hashmap[t] = pitches_to_update
                
                old_rhythm_i += old_duration
                dotted_factor_i = (dotted_factor_i + 1) % n
                new_rhythm_i += new_dur
                t += new_dur
                
            # print(old_rhythm_phrase)
            # print(new_rhythm_phrase)
            # print(pitches_hashmap)

            dotted_flat_durations[start_time:end_time] = new_rhythm_phrase

        # print(dotted_flat_durations)

        # 4. update the piano roll and onset map to reflect the flattened durations (maybe can do one pass, but splitting them for now)

        # 4.0. reconstruct the new durations matrix via the hashmap
        new_durations_matrix = np.zeros_like(self.music_matrix_representation.durations_matrix)
        # print(new_durations_matrix.shape)
        for time, pitches in pitches_hashmap.items():
            for p in pitches:
                new_durations_matrix[p, time] = dotted_flat_durations[time]

        # plot_mtx(new_durations_matrix)
        # print(new_durations_matrix)

        # 4.1. update the onset map by copying and boolean-ifying the unflatted duration
        dotted_onset_map = new_durations_matrix.copy()
        mask = dotted_onset_map != 0
        dotted_onset_map[mask] = 1
        # print(dotted_onset_map)
        # plot_mtx(dotted_onset_map)


        # 4.2. update the piano roll from the flattened duration
        new_piano_roll = self._reconstruct_piano_roll(new_durations_matrix)
        # plot_mtx(new_piano_roll)

        # if there are no 1s in the new piano roll, return None
        if np.sum(new_piano_roll) == 0:
            return None

        return get_music21_from_music_matrix_representation(MusicMatrixRepresentation(
            key_signature=self.music_matrix_representation.key_signature,
            time_signature=self.music_matrix_representation.time_signature,
            quantization=self.music_matrix_representation.quantization,
            piano_roll=new_piano_roll,
            onset_map=dotted_onset_map,
            durations_matrix=new_durations_matrix
        ))
    

    # TODO: beats are weird for three blind mice first measure? extra eighth note
    def generate_chordify_exercise(self, chord_level):
        # 1. flatten the duration- assumes that there is one linear line representation of duration 
        # (if there are multiple notes happening, they are all of the same duration)
        flattened_durations_list, pitches_hashmap = self._flatten_durations()

        print(flattened_durations_list, pitches_hashmap)

        # 2. find the ranges where there is an even pattern to dottify
        ranges = self._find_duplicate_length_ranges(flattened_durations_list)
        # print(ranges)

        chordified_flat_durations = flattened_durations_list.copy()

        # 3. the range will give ALL notes similar in rhythm, iterate through the ranges and group them into X total chords based on quantization and feasibility of actually being played (so 4-5 notes max, and an interval difference no greater than an octave), and update the MMR info
        for start_time, end_time, num_notes in ranges:
            # get the groupings of notes to make into chords via times
            sub_groupings = self._find_sub_groupings(flattened_durations_list, start_time, end_time, chord_level)

            # print("looping through each subgrouping")

            # for each sub-grouping, turn the mini-grouping into a chord by modifying the piano roll, onset map, and durations matrix to turn all the 1s in the earliest to latest time into 1s, onset at the earliest time for each affected pitch, and duration for all affected pitches to be the last time - earliest time
            for sub_start_time, sub_end_time in sub_groupings:
                # print(sub_start_time, sub_end_time)
                
                total_duration = sum(flattened_durations_list[sub_start_time:sub_end_time])
                new_rhythm_phrase = [0] * (sub_end_time - sub_start_time)
                new_rhythm_phrase[0] = total_duration

                # print(total_duration)

                # print(new_rhythm_phrase)
                chordified_flat_durations[sub_start_time:sub_end_time] = new_rhythm_phrase

                # print(flattened_durations_list[sub_start_time:sub_end_time])

                # get the indices of the non-zero durations in the sub-grouping
                # update the hashmap of time to pitches
                # print(len(flattened_durations_list))
                non_zero_indices = [i for i in range(sub_start_time, sub_end_time-1) if flattened_durations_list[i] != 0]
                # print(non_zero_indices)
                pitches = set()

                for i in non_zero_indices:
                    c_pitches = pitches_hashmap[i]
                    for p in c_pitches:
                        pitches.add(p)

                # print("pitches:", pitches)

                # if the distance in pitches is greater than an octave, skip this sub-grouping
                if pitches and max(pitches) - min(pitches) > 12:
                    return None

                # too many notes to chord, skip this sub-grouping
                if len(non_zero_indices) > 5:
                    return None

                for i in non_zero_indices:
                    pitches_to_update = pitches_hashmap[i]
                    pitches_hashmap[i] = []
                    pitches_hashmap[sub_start_time].append(pitches_to_update)

        # if new flat duration is the same as the old one, return None
        if flattened_durations_list == chordified_flat_durations:
            return None

        # 4. reconstruct the new durations matrix via the hashmap
        new_durations_matrix = np.zeros_like(self.music_matrix_representation.durations_matrix)
        for time, pitches in pitches_hashmap.items():
            for p in pitches:
                new_durations_matrix[p, time] = chordified_flat_durations[time]
        
        # update the onset map by copying and boolean-ifying the unflatted duration
        chordified_onset_map = new_durations_matrix.copy()
        mask = chordified_onset_map != 0
        chordified_onset_map[mask] = 1

        # update the piano roll from the flattened duration
        new_piano_roll = self._reconstruct_piano_roll(new_durations_matrix)

        # if there are no 1s in the new piano roll, return None
        if np.sum(new_piano_roll) == 0:
            return None

        return get_music21_from_music_matrix_representation(MusicMatrixRepresentation(
            key_signature=self.music_matrix_representation.key_signature,
            time_signature=self.music_matrix_representation.time_signature,
            quantization=self.music_matrix_representation.quantization,
            piano_roll=new_piano_roll,
            onset_map=chordified_onset_map,
            durations_matrix=new_durations_matrix
        ))


    def generate_slowed_down_exercise(self, factor):
        """
        Generate a slowed down exercise from the music matrix representation.
        """
        # 1. flatten the duration- assumes that there is one linear line representation of duration 
        # (if there are multiple notes happening, they are all of the same duration)
        flattened_durations_list, pitches_hashmap = self._flatten_durations()

        # slow down the entire flattened durations list by the factor, meaning we multiply the durations by the factor
        # flattened durations list has to be len * factor as long
        new_durations_list = [0] * (len(flattened_durations_list) * factor)
        for i in range(len(flattened_durations_list)):
            new_durations_list[i * factor] = flattened_durations_list[i] * factor

        # update the hashmap of time to pitches
        new_pitches_hashmap = defaultdict(list)
        items = list(pitches_hashmap.items())
        for time, pitches in items:
            for p in pitches:
                new_pitches_hashmap[time * factor].append(p)

        # print(flattened_durations_list, new_durations_list)
        # if new flat duration is the same as the old one, return None
        if flattened_durations_list == new_durations_list:
            return None

        # 4. reconstruct the new durations matrix via the hashmap
        new_durations_matrix = np.zeros((128, len(new_durations_list)))
        for time, pitches in new_pitches_hashmap.items():
            for p in pitches:
                new_durations_matrix[p, time] = new_durations_list[time]
        
        # update the onset map by copying and boolean-ifying the unflatted duration
        chordified_onset_map = new_durations_matrix.copy()
        mask = chordified_onset_map != 0
        chordified_onset_map[mask] = 1

        # update the piano roll from the flattened duration
        new_piano_roll = self._reconstruct_piano_roll(new_durations_matrix)

        # if there are no 1s in the new piano roll, return None
        if np.sum(new_piano_roll) == 0:
            return None

        return get_music21_from_music_matrix_representation(MusicMatrixRepresentation(
            key_signature=self.music_matrix_representation.key_signature,
            time_signature=self.music_matrix_representation.time_signature,
            quantization=self.music_matrix_representation.quantization,
            piano_roll=new_piano_roll,
            onset_map=chordified_onset_map,
            durations_matrix=new_durations_matrix
        ))


    def _find_sub_groupings(self, flattened_durations_list, start_time, end_time, chord_level):
        # TODO: improve on this, but currently split the group by the time signature denominator
        sub_groupings = []
        # print(self.quantization, self.time_signature.denominator)
        for i in range(start_time, end_time, chord_level):
            sub_groupings.append((i, min(i + chord_level, end_time)))

        # print(sub_groupings)
        return sub_groupings

    
    def _flatten_durations(self):
        flat = [int(x) for x in self.music_matrix_representation.durations_matrix[0]]

        # time_index : [midi pitch 1, midi pitch 2]
        hashmap = defaultdict(list)

        for ri, ci in np.ndindex(self.music_matrix_representation.durations_matrix.shape):
            if self.music_matrix_representation.durations_matrix[ri, ci] != 0:
                if flat[ci] == 0:
                    flat[ci] = int(self.music_matrix_representation.durations_matrix[ri, ci])
                    # print(self.music_matrix_representation.durations_matrix[ri, ci])
                hashmap[ci].append(ri)

        return flat, hashmap
    
    def _find_duplicate_length_ranges(self, durations_list):
        windows = [] # start_time, end_time
        
        curr_val_count = 0
        curr_val = -1
        i = 0
        j = 0
        # for j in range(len(durations_list)):
        while j < len(durations_list):
            if durations_list[j] > 0:
                if curr_val < 0:
                    curr_val = durations_list[j]
                    curr_val_count += 1
                    i = j
                elif durations_list[j] == curr_val:
                    curr_val_count += 1
                else:
                    if curr_val_count > 1:
                        windows.append((i, j, curr_val_count))
                    curr_val = durations_list[j]
                    curr_val_count = 1
                    i = j

            j += 1

        if curr_val_count > 1:
            windows.append((i, j, curr_val_count))

        return windows

    def _reconstruct_piano_roll(self, durations_matrix):
        new_piano_roll = np.zeros_like(durations_matrix)
        # plot_mtx(durations_matrix)

        # print(durations_matrix.shape)
        rows, cols = durations_matrix.shape

        for r in range(rows):
            row = durations_matrix[r]

            c = 0
            while c < cols:
                dur = int(durations_matrix[r, c])
                if dur == 0:
                    c += 1
                else:
                    x = c
                    for dx in range(dur):
                        # NOTE: THIS IS A TEMPORARY SOLUTION, DOES NOT FULLY SOLVE THE DOTTED RHYTHM NEEDING RESTS ISSUE? need to fix the durations matrix to account for rests
                        if (x+dx) >= cols:
                            break
                        new_piano_roll[r, x+dx] = 1
                    c += dur

        return new_piano_roll

# TODO: clean up structure
def get_all_exercises(score):
    # turn l into a hashmap
    l = defaultdict(list)

    exerciseScore = ExerciseScore(score)

    # if the score has multiple lines, we want to display the entire score together, otherwise we don't display score-level since it's the same as part-level
    # if len(exerciseScore.parts) > 1:
    description = "Full score showing all parts together"
    l['Score Level'].append((description, get_musicxml_from_music21(exerciseScore.original_stream)))
    # else:
    #     l['Score Level'].append((None, None))

    for part in exerciseScore.parts:
        # if the part has multiple lines, we want to display the entire part together, otherwise we don't display part-level since it's the same as line-level
        # if len(part.lines) > 1:
        # if len(exerciseScore.parts) > 1:
        description = "Part showing all notes in a part together"
        l['Part Level'].append((description, get_musicxml_from_music21(part.original_stream)))
        # else:
            # l['Part Level'].append((None, None))
        
        for line in part.lines:
            description = "Original voice before any modifications"
            # if len(part.lines) > 1:
            l['Line Level Original'].append((description, get_musicxml_from_music21(line.original_stream)))
            for exercise_name, exercises in line.exercises.items():
                # l['line_generated_exercise'].append(get_musicxml_from_music21(exercise))
                for exercise in exercises:
                    # improve the descriptions + tooltip
                    description = f"Exercise generated by modifying the rhythm pattern to {exercise_name}"
                    l["Line Level Exercise: " + exercise_name].append((description, get_musicxml_from_music21(exercise)))
    return l


if __name__ == "__main__":
    app.run(port=5000)