import asyncio
import os
import io
import wave
import shutil
import requests
import re
import logging
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_BIN = os.path.join(BASE_DIR, "piper_bin")
TMP_BASE = "/tmp" if not os.name == 'nt' else os.path.join(BASE_DIR, "tmp")
TMP_BIN = os.path.join(TMP_BASE, "piper_bin")
PIPER_PATH = os.path.join(TMP_BIN, "piper-linux", "piper") if not os.name == 'nt' else os.path.join(TMP_BIN, "piper.exe")

CACHE_DIR = os.path.join(TMP_BASE, "models")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(TMP_BIN, exist_ok=True)

REPO = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/kk/kk_KZ'
HF_MODELS = {
    "kk_KZ-iseke-x_low.onnx": f"{REPO}/iseke/x_low/kk_KZ-iseke-x_low.onnx?download=true",
    "kk_KZ-raya-x_low.onnx": f"{REPO}/raya/x_low/kk_KZ-raya-x_low.onnx?download=true",
    "kk_KZ-issai-high.onnx": f"{REPO}/issai/high/kk_KZ-issai-high.onnx?download=true"
}

def setup_piper():
    """Piper-ді дайындау"""
    if not os.path.exists(PIPER_PATH):
        if os.path.exists(SOURCE_BIN):
            logging.info(f"📦 Piper көшірілуде: {SOURCE_BIN} -> {TMP_BIN}")
            if os.path.exists(TMP_BIN):
                try: shutil.rmtree(TMP_BIN)
                except: pass
            shutil.copytree(SOURCE_BIN, TMP_BIN)
            if os.name != 'nt':
                os.chmod(PIPER_PATH, 0o755)
        else:
            logging.error(f"❌ SOURCE_BIN табылмады: {SOURCE_BIN}")

def get_model_file(model_name: str) -> str:
    model_path = os.path.join(CACHE_DIR, model_name)
    config_path = model_path + ".json"
    
    if not os.path.isfile(model_path):
        url = HF_MODELS.get(model_name)
        if not url:
            raise ValueError(f"Белгісіз модель: {model_name}")
        
        logging.info(f"📥 Модель жүктелуде: {model_name}")
        r = requests.get(url)
        r.raise_for_status()
        with open(model_path, "wb") as f:
            f.write(r.content)
            
        conf_url = url.replace(".onnx", ".onnx.json")
        r = requests.get(conf_url)
        if r.status_code == 200:
            with open(config_path, "wb") as f:
                f.write(r.content)
                
    return model_path

def get_wav_duration(data: bytes) -> int:
    try:
        with wave.open(io.BytesIO(data), 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            return int(frames / rate)
    except:
        return 0

async def synthesize_chunk(text: str, model_name: str, speaker_id: int = None) -> bytes:
    """Бір бөлікті синтездеу"""
    setup_piper()
    model_path = get_model_file(model_name)
    
    # Мәтінді тазалау
    text = re.sub(r'[^\w\s\d.,!?;:()"-]', '', text)
    text = re.sub(r'\n+', '\n', text)

    command = [PIPER_PATH, "--model", model_path, "--output_file", "-"]
    if speaker_id is not None:
        command.extend(["--speaker", str(speaker_id)])
    
    env = os.environ.copy()
    if os.name != 'nt':
        env["LD_LIBRARY_PATH"] = os.path.dirname(PIPER_PATH)
    
    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )
    stdout, stderr = await process.communicate(input=text.encode("utf-8"))
    if process.returncode != 0:
        logging.error(f"Piper error: {stderr.decode()}")
        return b""
    return stdout

def merge_wav_bytes(wav_list):
    """Бинарлы WAV бөліктерін бір файлға біріктіреді"""
    if not wav_list:
        return b""
    if len(wav_list) == 1:
        return wav_list[0]
        
    with io.BytesIO(wav_list[0]) as first_io:
        with wave.open(first_io, 'rb') as first_wav:
            params = first_wav.getparams()
            frames = first_wav.readframes(first_wav.getnframes())
            
    total_frames = frames
    for i in range(1, len(wav_list)):
        with io.BytesIO(wav_list[i]) as next_io:
            with wave.open(next_io, 'rb') as next_wav:
                total_frames += next_wav.readframes(next_wav.getnframes())
                
    with io.BytesIO() as out_io:
        with wave.open(out_io, 'wb') as out_wav:
            out_wav.setparams(params)
            out_wav.writeframes(total_frames)
        return out_io.getvalue()
