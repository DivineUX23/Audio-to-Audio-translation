socket = io();
// Connect to the WebSocket server
socket.connect('https://divineux23-code50-96517814-445597p7x7f5rx6-5000.preview.app.github.dev/');
// When the SocketIO connection is established
socket.on('connect', function() {
console.log('Connected to server');
});

  // Send user input to the server when the form is submitted
  const form = document.getElementById('chat-form');
  console.log(form);
  const input = document.getElementById('user_input');
  const chat = document.getElementById('conversation-history');

  const botAudio = document.getElementById('bot-audio');

  form.addEventListener('submit', function(event) {
  event.preventDefault();
  console.log('Form submitted');

  // Handle submission of user input to server
  console.log(input.value);
  const message = document.createElement('div');
  message.innerHTML = `<span class="user-label">LANGUAGE:</span> <span class="userInput-label">${input.value}</span>`;

  message.classList.add('user-message');
  chat.appendChild(message);
  socket.emit('user_input', input.value);
  input.value = '';


  // Handle submission of voice to server
  const voiceSelect = document.getElementById('choice');
  const selectedVoice = voiceSelect.value;
  console.log(selectedVoice);
  socket.emit('voice_id', selectedVoice);
});


  // Listen for incoming bot responses
  socket.on('bot_response', function(data) {

  // Update the chat UI with the bot response
  console.log(data);
  const chat = document.getElementById('conversation-history');
  const message = document.createElement('div');

  const ai = document.createElement('span');
  ai.innerText = 'TEXT: ';
  ai.style.color = 'blue';
  ai.style.fontWeight = 'meduim';
  ai.style.fontSize = '14px';

  message.appendChild(ai);

  const response = document.createElement('span');
  response.innerText = data;
  response.style.color = 'black';

  message.appendChild(response);

  message.classList.add('bot-message');

  chat.appendChild(message);

});


    // Handle the new_audio event
    socket.on('new_audio', data => {

    console.log(data);

    const key = new Blob([data.data], { type: data.type });

    const url = URL.createObjectURL(key);

    const audio = new Audio(url);

    audio.controls = true;

    const chat = document.getElementById('conversation-history');

    chat.appendChild(audio);

    });



//Deleting the video

window.addEventListener("beforeunload", function(event) {
var xhr = new XMLHttpRequest();
xhr.open("POST", "/delete_video", true);
xhr.send();
});


var timeout;

function deleteVideoFile() {
var xhr = new XMLHttpRequest();
xhr.open('POST', '/delete_video', true);
xhr.send();
}

function startTimeout() {
timeout = setTimeout(deleteVideoFile, 1800000);
}

function clearTimeoutIfInteracted() {
clearTimeout(timeout);
document.removeEventListener('mousemove', clearTimeoutIfInteracted);
}

function clearTimeIfInteracted(){
clearTimeout(timeout);
document.removeEventListener('click', clearTimeoutIfInteracted);
}
function clearAndDelete() {
clearTimeout(timeout);
deleteVideoFile();
}

startTimeout();

document.addEventListener('click', clearTimeoutIfInteracted);

document.addEventListener('mousemove', clearTimeoutIfInteracted);

window.addEventListener('beforeunload', clearAndDelete);
