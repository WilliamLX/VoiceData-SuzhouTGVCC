"""Provides functions for transcribing audio files."""

import logging
from pathlib import Path
from funasr import AutoModel
from tqdm import tqdm

logger = logging.getLogger(__name__)


def transcribe_all_wav_to_text(source_dir: str, dest_dir: str) -> None:
    """
    Transcribe all WAV audio files in a directory to text using FunASR.

    Args:
        source_dir: The path to the directory containing WAV files dest_dir: The path to the directory to save the text files.

    """
    dest_path = Path(dest_dir)
    dest_path.mkdir(exist_ok=True)

    model = AutoModel(model="paraformer-zh")

    wav_files = list(Path(source_dir).glob("*.wav"))
    for wav_file in tqdm(wav_files, desc="Transcribing audio files"):
        txt_file = dest_path / f"{wav_file.stem}.txt"
        try:
            res = model.generate(input=str(wav_file))
            text = res[0]['text']
            with open(txt_file, "w") as f:
                f.write(text)
            logger.info("Successfully transcribed %s to %s", wav_file, txt_file)
        except Exception:
            logger.exception("Error transcribing %s", wav_file)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) != 3:
        print("Usage: python transcribe_audio.py <source_directory> <destination_directory>")
        sys.exit(1)
    source_directory = sys.argv[1]
    destination_directory = sys.argv[2]
    transcribe_all_wav_to_text(source_directory, destination_directory)
