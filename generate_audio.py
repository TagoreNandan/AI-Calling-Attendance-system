from gtts import gTTS

text = """
Hello. This is an automated attendance call from the college.
Your child was marked absent today.
May I know the reason for the absence?
"""

tts = gTTS(text=text, lang="en", slow=False)
tts.save("question.mp3")

print("Audio Generated")