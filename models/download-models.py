import requests
from tqdm import tqdm

# List of models to download
models = [
    "https://huggingface.co/distil-whisper/distil-medium.en/resolve/main/ggml-medium-32-2.en.bin",
    "https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"
]

# Download each model

def download_models(models):
    for model in models:
        filename = model.split("/")[-1]
        r = requests.get(model, stream=True)
        with open(filename, "wb") as f:
            file_size = int(r.headers.get("Content-Length", 0))
            chunk_size = 1024
            with tqdm(total=file_size, unit="B", unit_scale=True, desc=filename) as pbar:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
                    pbar.update(chunk_size)

if __name__ == "__main__":
    download_models(models)