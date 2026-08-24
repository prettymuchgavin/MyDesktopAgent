import os
import urllib.request
import sys

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# Official Kokoro-ONNX GitHub release URLs
ONNX_MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx"
VOICES_BIN_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin"

ONNX_PATH = os.path.join(MODELS_DIR, "kokoro-v0_19.onnx")
VOICES_BIN_PATH = os.path.join(MODELS_DIR, "voices.bin")

def download_file(url: str, dest_path: str):
    filename = os.path.basename(dest_path)
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        print(f"[EXISTS] {filename} already exists at {dest_path}")
        return

    print(f"[DOWNLOADING] {filename} from {url}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
            total_size = int(response.info().get('Content-Length', 0))
            count = 0
            block_size = 8192
            while True:
                buffer = response.read(block_size)
                if not buffer:
                    break
                count += len(buffer)
                out_file.write(buffer)
                percent = int(count * 100 / total_size) if total_size > 0 else 0
                sys.stdout.write(f"\rDownloading {filename}: {percent}% ({count // (1024*1024)} MB)")
                sys.stdout.flush()
        print(f"\n[SUCCESS] {filename} downloaded successfully!")
    except Exception as e:
        print(f"\n[ERROR] Failed downloading {filename}: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("KOKORO-TTS MODEL DOWNLOADER")
    print("=" * 60)
    download_file(VOICES_BIN_URL, VOICES_BIN_PATH)
    download_file(ONNX_MODEL_URL, ONNX_PATH)
    print("\n[COMPLETE] Kokoro-TTS models downloaded to models/ directory.")
