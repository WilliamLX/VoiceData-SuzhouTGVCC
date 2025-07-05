"""Runs the audio processing functions."""

import argparse
import logging

from audio_processor import convert_all_aac_to_wav


def main() -> None:
    """Run the main program."""
    parser = argparse.ArgumentParser(description="Process audio files in a directory.")
    parser.add_argument(
        "source_directory", help="The directory containing audio files to process."
    )
    parser.add_argument(
        "destination_directory", help="The directory to save the converted files."
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    convert_all_aac_to_wav(args.source_directory, args.destination_directory)


if __name__ == "__main__":
    main()
