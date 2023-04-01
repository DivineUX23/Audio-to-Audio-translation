from flask import Flask, render_template, request, send_file, Response
from flask_bootstrap import Bootstrap
from pytube import YouTube
import openai

#Using socketIO to for js interaction:
from flask_socketio import SocketIO, emit
from flask import session
import os
import io

#Elevenlabs:
import requests

#chucking video:
from moviepy.video.io.VideoFileClip import VideoFileClip
from pydub import AudioSegment
import math

#for playing vidoe:
import uuid
from moviepy.audio.io.AudioFileClip import AudioFileClip

#chucking words of over 3000 tokens:
import nltk
from nltk.tokenize import sent_tokenize
from nltk.tokenize import word_tokenize


# Use your own API key
openai.api_key = os.environ["OPENAI_API_KEY"]

#Elevenlabs API key
user.api_key = os.environ["OPENAI_API_KEY"]


transcript = []

conversation_history = []

bot_response = None

prompt = None

filepath = None

current_filepath = None

voice = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'divine'
app.config['UPLOAD_FOLDER'] = 'static'

socketio = SocketIO(app)
Bootstrap(app)


@app.route('/')
def index():
    return render_template('audio_input.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected')


# Upload video page
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    global transcript
    global prompt
    global bot_response
    global conversation_history
    global filepath
    global current_filepath


    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Transcribe video and generate timestamped transcript
            transcript = transcribe_video(filepath)
            print(transcript)
            current_filepath = filepath

            return render_template('audio.html', video_url=filepath, transcript=transcript)


        elif 'youtube_link' in request.form:
            youtube_link = request.form['youtube_link']

            # Use pytube to download the YouTube video
            yt = YouTube(youtube_link)
            stream = yt.streams.get_highest_resolution()
            file = stream.download(output_path='static', filename='my_video.mp4')
            filepath = os.path.join('static', 'my_video.mp4')

            # Transcribe video and generate timestamped transcript
            transcript = transcribe_video(filepath)
            print(transcript)
            current_filepath = filepath

            return render_template('audio.html', video_url=filepath, transcript=transcript)



        elif 'audio' in request.files:
            file = request.files['audio']
            filename = str(uuid.uuid4()) + '.' + file.filename.split('.')[-1]
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Transcribe video and generate timestamped transcript
            transcript = transcribe_audio(filepath)
            print(transcript)
            current_filepath = filepath

            # Return the path to the downloaded video file
            return render_template('audio.html', filename=filepath, transcript=transcript)


        elif 'link' in request.form:
            link = request.form['link']
            response = requests.get(link)
            filename = str(uuid.uuid4()) + '.mp3'
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)

            # Transcribe video and generate timestamped transcript
            transcript = transcribe_audio(filepath)
            print(transcript)
            current_filepath = filepath

            # Return the path to the downloaded video file
            return render_template('audio.html', filename=filepath, transcript=transcript)

        return render_template('audio.html')
    else:

        return render_template('audio.html')



# Play video on page
@app.route('/play/<path:video_url>')
def play(video_url):
    # Remove the extra 'static' directory from the file path
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], video_url.replace('static/', '', 1))
    return send_file(file_path, mimetype='video/mp4')


# Play audio on page
@app.route('/play_file/<path:filename>')
def play_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.replace('static/', '', 1))
    return send_file(file_path, mimetype='audio/mp3')



#For generating of video the transcript with wisper
def transcribe_video(filepath):

    # Load the video file
    video = VideoFileClip(filepath)
    segment_duration = 10 * 60  # seconds
    transcripts = []
    num_segments = math.ceil(video.duration / segment_duration)

    # Loop through the segments
    for i in range(num_segments):

        start_time = i * segment_duration
        end_time = min((i + 1) * segment_duration, video.duration)
        segment = video.subclip(start_time, end_time)
        segment_name = f"segment_{i+1}.mp3"
        segment.audio.write_audiofile(segment_name)

        # Pass the audio segment to WISPR for speech recognition
        audio = open(segment_name, "rb")
        transcripting = openai.Audio.transcribe("whisper-1", audio).text
        transcripts.append(transcripting)
        os.remove(segment_name)

    transcript = "\n".join(transcripts)
    return transcript


#For generating of audio the transcript with wisper
def transcribe_audio(filepath):

    audio = AudioFileClip(filepath)
    segment_duration = 10 * 60  # seconds
    transcripts = []
    num_segments = math.ceil(audio.duration / segment_duration)

    # Loop through the segments
    for i in range(num_segments):

        start_time = i * segment_duration
        end_time = min((i + 1) * segment_duration, audio.duration)
        segment = audio.subclip(start_time, end_time)
        segment_name = f"segment_{i+1}.mp3"
        segment.write_audiofile(segment_name)

        # Pass the audio segment to WISPR for speech recognition
        audio = open(segment_name, "rb")
        transcripting = openai.Audio.transcribe("whisper-1", audio).text
        transcripts.append(transcripting)

        os.remove(segment_name)
    transcript = "\n".join(transcripts)

    return transcript


# Getting users to choose a voice

@socketio.on('voice_id')
def get_audio(voice_id):

    global voice

    print(f"Voice ID = {voice_id}")

    word2 = "Jane"

    if set(voice_id) == set(word2):
        voice = 'EXAVITQu4vr4xnSDxMaL'

    else:
        voice = 'pNInz6obpgDQGcFmaJgB'

    print(f"Voice ID = {voice}")



#opeanAI for the chat converation:
nltk.download('punkt')

@socketio.on('user_input')

def handle_conversation(user_input):


    print(f"Voice ID 2 = {voice}")

    global bot_response


    if len(word_tokenize(transcript)) <= 3000:

        print("Token count less = ", len(word_tokenize(str(transcript))))

        bot_response = generate_response(transcript, user_input)

        print(f"less than 3000 tokens = {bot_response}\n")

    else:

        print("Token count more = ", len(word_tokenize(transcript)))
        chunk_size = 3000
        chunks = []
        sentences = sent_tokenize(transcript)
        current_chunk = ""

        for sentence in sentences:
            tokens = nltk.word_tokenize(sentence)

            if len(current_chunk.split()) + len(tokens) <= chunk_size:
                current_chunk += " " + sentence

            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence

            print(f"TOKEN LENT OF unsent CHUNK = \n\n{len(word_tokenize(str(current_chunk.strip())))}\n\n\n")

        if current_chunk:
            chunks.append(current_chunk.strip())


        responses = []
        for chunk in chunks:
            response = generate_response(chunk, user_input)

            print(f"TOKEN LENT OF CHUNK = \n\n{len(word_tokenize(str(response)))}\n\n\n")

            responses.append(response)

        joined_response = ' '.join(responses)
        bot_response = joined_response

    new_audio = audio_output(bot_response, voice)

    # Create a Flask response object with the mp3 data and appropriate headers
    response = Response(new_audio, mimetype='audio/mpeg')
    response.headers.set('Content-Disposition', 'attachment', filename='responding.mp3')

    # Emit the audio data to the client-side
    socketio.emit('new_audio', {'data': new_audio, 'type': 'audio/mpeg'})
    socketio.emit('bot_response', bot_response)




#passing transcript or each chucks to chatgpt
def generate_response(transcript, user_input):

    prompt = f"Translate {transcript} to {user_input}, don't say anything else except the translation,"

    completion = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
            {"role": "system", "content": "You're a proffesional language translator"},
            {"role": "user", "content": prompt}
    ]
    )
    bot_first_response = completion.choices[0].message.content

    return bot_first_response



#Eleven-labs: Text to audio for new lang
def audio_output(bot_response, voice):

    print(voice)

    CHUNK_SIZE = 1024


    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/stream"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": user
    }

    data = {
        "text": bot_response,
        "voice_settings": {
        "stability": 0,
        "similarity_boost": 0
        }
    }
    response = requests.post(url, json=data, headers=headers, stream=True)


    audio_data = io.BytesIO()
    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
        if chunk:
            audio_data.write(chunk)

    return audio_data.getvalue()



#Automatic delete video/audio
@app.route('/delete_video', methods=['POST'])
def delete_video():
    global current_filepath
    print("Dead & Gone")

    if os.path.exists(current_filepath):
        os.remove(current_filepath)
        print("Dead & Gone")

    return "Ooops! Time out"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


