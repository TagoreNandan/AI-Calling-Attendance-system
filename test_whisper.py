from faster_whisper import WhisperModel

model = WhisperModel("base")

segments, info = model.transcribe("temp.wav")

for segment in segments:
    print(segment.text)