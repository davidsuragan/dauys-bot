from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import speech_recognition as sr
import soundfile as sf
import tempfile, os

app = FastAPI()
recognizer = sr.Recognizer()

def convert_to_wav(input_path: str) -> str:
    audio_data, samplerate = sf.read(input_path, always_2d=True)
    audio_data = audio_data[:, 0]  # mono
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_out:
        sf.write(temp_out.name, audio_data, samplerate, subtype="PCM_16")
        return temp_out.name

@app.post("/api/stt")
async def stt(file: UploadFile = File(...)):
    input_path = wav_path = None
    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_in:
            temp_in.write(await file.read())
            input_path = temp_in.name

        wav_path = convert_to_wav(input_path)

        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="kk-KZ")

        return JSONResponse(content={"text": text})
    except sr.UnknownValueError:
        return JSONResponse(status_code=400, content={"error": "Сөйлемді түсіне алмады"})
    except sr.RequestError as e:
        return JSONResponse(status_code=500, content={"error": f"Google API қатесі: {e}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        if input_path and os.path.exists(input_path):
            os.remove(input_path)
        if wav_path and os.path.exists(wav_path):
            os.remove(wav_path)

@app.get("/")
async def root():
    return {"message": "✅ SpeechRecognition + FastAPI STT жұмыс істеп тұр!"}
