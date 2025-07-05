"""Provides functions for audio file conversion."""

import logging
from pathlib import Path

from pydub import AudioSegment

logger = logging.getLogger(__name__)


def convert_all_aac_to_wav(source_dir: str, dest_dir: str) -> None:
    """
    Convert all AAC audio files in a directory to WAV format.

    Args:
        source_dir: The path to the directory containing AAC files.
        dest_dir: The path to the directory to save the WAV files.

    """
    dest_path = Path(dest_dir)
    dest_path.mkdir(exist_ok=True)

    for aac_file in Path(source_dir).glob("*.aac"):
        wav_file = dest_path / f"{aac_file.stem}.wav"
        try:
            audio = AudioSegment.from_file(aac_file, format="aac")
            audio.export(wav_file, format="wav")
            logger.info("Successfully converted %s to %s", aac_file, wav_file)
        except Exception:
            logger.exception("Error converting %s", aac_file)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    source_directory = "downloads"
    destination_directory = "converted_audio"
    convert_all_aac_to_wav(source_directory, destination_directory)
