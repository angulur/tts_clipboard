import json
import time
import random
import pyperclip
import requests
import pyaudio
import keyboard
import threading

char_mode = True
stop_audio = False
male_voices = [
    "en_20",
    "en_22",
    "en_23",
    "en_25",
    "en_26",
    "en_63",
]
female_voices = [
    "en_50",
    "en_67",
    "en_51",
    "en_72",
    "en_52",
    "en_76",
    "en_53",
    "en_54",
    "en_55",
    "en_56",
    "en_61",
    "en_62",
    "en_21",
    "en_24",
]
name_to_voices = [
    {
        "name": "None",
        "audio": "en_63"
    },
    {
        "name": "Ty",
        "audio": "en_63"
    },
    {
        "name": "Tyler",
        "audio": "en_63"
    },
]


male_voices_iter = iter(male_voices)
female_voices_iter = iter(female_voices)


def load_names_and_genders():
    try:
        with open('names_and_genders.txt', 'r') as f:
            for line in f:
                name, is_male = line.strip().split(',')
                audio = next(male_voices_iter) if is_male == 'm' else next(
                    female_voices_iter)

                name_to_voices.append({
                    "name": name,
                    "audio": audio
                })
    except FileNotFoundError:
        # If the file doesn't exist, do nothing
        pass


def get_audio_for_name(name):
    for name_to_audio in name_to_voices:
        if name_to_audio["name"] == name:
            return name_to_audio["audio"]
    # if the name is not in the list, ask user if it's male or female and add it
    is_male = None
    while is_male not in ['m', 'f', '']:
        is_male = input(f"Is the name {name} male (m) or female (f)? ").lower()
    if is_male == '':
        return "en_63"
    new_voice = next(male_voices_iter) if is_male == 'm' else next(
        female_voices_iter)
    name_to_voices.append({
        "name": name,
        "audio": new_voice
    })
    # Save the name and gender to a text file
    with open('names_and_genders.txt', 'a') as f:
        f.write(f"{name},{is_male}\n")
    return new_voice


def send_to_api(data):
    global stop_audio
    # Here we simply post the data to the api
    # You may need to modify this based on the API requirements
    url = "http://127.0.0.1:8010/tts/generate"
    speaker = "en_78"
    # data = "Here we simply post the data to the api"

    if char_mode:
        bad_prefixes = [
        ]

        # if data contains bad prefix, continue
        if any(prefix in data for prefix in bad_prefixes):
            return

        # get name from data, for example "[John]: Hello" -> "John"
        name = data[1:data.find("]")]
        # remove "whispers" from name
        name = name.replace(" whispers", "")
        name = name.replace("'s Thoughts", "")

        # remove name from data, for example "[John]: Hello" -> "Hello"
        if data.startswith("["):
            data = data[data.find("]")+2:]

        # remove repeating characters, for example "Hellooooo" -> "Hello" and "Hello...!" -> "Hello!"
        data = data.replace("...", ".")
        data = data.replace("..", ".")
        data = data.replace(".", " ")
        data = data.replace(r"{i}", "")
        data = data.replace("{/i}", "")
        data = data.replace(r"{p}", "")
        data = data.replace("{/p}", "")

        speaker = get_audio_for_name(name)
        print(f"Sending to API: [{name}] {data} {speaker}")

    payload = json.dumps({
        "text": data,
        "speaker": speaker
    })
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code == 200:
        print("Successfully sent to API")

        # play audio without saving to file
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(2),
                        channels=1,
                        rate=48000,
                        output=True)

        # Break audio data into chunks and play each one unless stopped
        chunk_size = 1024
        for i in range(0, len(response.content), chunk_size):
            if stop_audio:
                break
            stream.write(response.content[i:i+chunk_size])
        stream.stop_stream()
        stream.close()
        p.terminate()
        stop_audio = False

    else:
        print("Failed to send to API")


def listen_for_interrupt_key():
    global stop_audio
    while True:
        if keyboard.is_pressed('q'):  # if key 'q' is pressed
            print('You pressed a key!')
            stop_audio = True
            time.sleep(0.1)  # prevent CPU overusage


def monitor_clipboard():
    old_clipboard = ""
    while True:
        try:
            clipboard = pyperclip.paste()
            if clipboard != old_clipboard:
                old_clipboard = clipboard
                # Create a new thread for each new clipboard content
                send_to_api(clipboard)
        except Exception as e:
            print(f"Error occurred: {e}")
        # Pause for a while
        time.sleep(1)


if __name__ == "__main__":
    load_names_and_genders()
    interrupt_thread = threading.Thread(target=listen_for_interrupt_key)
    interrupt_thread.start()
    monitor_clipboard()
