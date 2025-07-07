"""Transcribes audio files to text."""

import logging
from pathlib import Path

import speech_recognition as sr

logger = logging.getLogger(__name__)


def transcribe_audio_file(audio_path: Path, text_path: Path) -> None:
    """
    Transcribes a single audio file to text.

    Args:
        audio_path: The path to the audio file.
        text_path: The path to save the transcribed text file.
    """
    print(f"开始转录音频文件: {audio_path}")
    recognizer = sr.Recognizer()
    try:
        print(f"正在读取音频文件: {audio_path}")
        with sr.AudioFile(str(audio_path)) as source:
            audio_data = recognizer.record(source)
        print(f"正在使用Google语音识别服务转录音频...")
        text = recognizer.recognize_google(audio_data, language="zh-CN")
        print(f"转录完成，正在保存到: {text_path}")
        with text_path.open("w", encoding="utf-8") as f:
            f.write(text)
        print(f"转录成功！音频文件: {audio_path} -> 文本文件: {text_path}")
        logger.info("Successfully transcribed %s to %s", audio_path, text_path)
    except sr.UnknownValueError:
        print(f"警告: Google语音识别无法理解音频内容: {audio_path}")
        logger.warning(
            "Google Speech Recognition could not understand audio in %s", audio_path
        )
    except sr.RequestError:
        print(f"错误: 无法连接到Google语音识别服务: {audio_path}")
        logger.exception(
            "Could not request results from Google Speech Recognition service for %s",
            audio_path,
        )
    except Exception:
        print(f"错误: 转录过程中发生未知错误: {audio_path}")
        logger.exception(
            "An unknown error occurred during transcription of %s", audio_path
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    audio_file = Path("converted_audio/20250509125527876.wav")
    text_file = Path("transcriptions/20250509125527876.txt")
    transcribe_audio_file(audio_file, text_file)
