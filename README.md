# Speech and Speech Translation App

This is a Flask web app that allows you to translate audio and video files to an audio output in any languag of your choice using OpenAI's whisper, gpt-3.5-turbo and Eleven labs. It uses the pytube, moviepy, and pydub libraries to download and process the videos, and nltk for tokenizing the text.

## Watch a simple demo of the project:

https://user-images.githubusercontent.com/96517814/229331997-4525a982-a482-462a-8a3a-559073905151.mp4

## Installation
Clone this repository and navigate to the project directory:

```bash
git clone https://github.com/<username>/<project-name>.git
cd <project-name>
```

Create a virtual environment and install the required packages:

```bash
python -m venv venv
source venv/bin/activate  # on Windows, use "venv\Scripts\activate"
pip install -r requirements.txt
```
  
## Usage
Run the app locally using Flask:

```arduino
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```
Navigate to `http://localhost:5000/` in your web browser to access the app.

## Features
- Upload audio or video files or links.
- Transcribe audio or video and generate a text output.
- Chuck words of over 3000 tokens.
- Use the OpenAI API to translate.
- Use Elevenlabs API to convert text to audio.

## Dependencies
```
- Flask
- Flask-SocketIO
- Flask-Bootstrap
- PyTube
- moviepy
- pydub
- nltk
- OpenAI API key
- Elevenlabs API key
```

## Contributing
Contributions to this project are welcome. To contribute, please follow these steps:
1. Fork this repository.
2. Create a new branch: `git checkout -b my-new-branch`
3. Make your changes and commit them: `git commit -m "Add some feature"`
4. Push to the branch: `git push origin my-new-branch`
5. Create a new pull request.
6. Please include a clear description of your changes and their purpose.
