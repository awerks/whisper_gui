import subprocess
from typing import TextIO, Iterator


def srt_format_timestamp(seconds: float):
    """
    Convert a time duration in seconds to SRT (SubRip Subtitle) timestamp format.

    """
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = milliseconds // 3_600_000
    milliseconds -= hours * 3_600_000

    minutes = milliseconds // 60_000
    milliseconds -= minutes * 60_000

    seconds = milliseconds // 1_000
    milliseconds -= seconds * 1_000

    return (f"{hours}:") + f"{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def write_srt(transcript: Iterator[dict], file: TextIO):
    """
    Writes a transcript to a file in SubRip Subtitle (SRT) format.
    """
    count = 0
    for segment in transcript:
        count += 1
        print(
            f"{count}\n"
            f"{srt_format_timestamp(segment['start'])} --> {srt_format_timestamp(segment['end'])}\n"
            f"{segment['text'].replace('-->', '->').strip()}\n",
            file=file,
            flush=True,
        )


def compress_file(file_path_or_url: str, compressed_path: str = "compressed_audio.mp3") -> str:
    """Compress the audio file using ffmpeg."""
    popen: subprocess.Popen = subprocess.Popen(
        ["ffmpeg", "-i", file_path_or_url, "-b:a", "64k", compressed_path, "-y"],
    )
    stdout, stderr = popen.communicate()
    if popen.returncode != 0:
        raise subprocess.CalledProcessError(popen.returncode, popen.args, output=stdout, stderr=stderr)
    return compressed_path


def download_url(url: str, save_path: str) -> str:
    """
    Downloads a video from the given URL and saves it to the specified path.

    This function uses the `yt-dlp` command-line tool to download the best available video
    with a resolution of up to 720p, along with the best available audio. The video and audio
    are merged into a single MP4 file.

    """

    popen: subprocess.Popen = subprocess.Popen(
        [
            "yt-dlp",
            url,
            "-f",
            "bestvideo[height<=720]+bestaudio/best[height<=720]/best[height<=720]",
            "-o",
            save_path,
            "--merge-output-format",
            "mp4",
        ],
    )
    stdout, stderr = popen.communicate()
    if popen.returncode != 0:
        raise subprocess.CalledProcessError(popen.returncode, popen.args, output=stdout, stderr=stderr)
    return save_path


def extract_audio(video_path: str, audio_path: str) -> str:
    """
    Extracts the audio from a video file and saves it to a specified path.

    """
    popen: subprocess.Popen = subprocess.Popen(
        ["ffmpeg", "-i", video_path, "-vn", audio_path],
    )
    stdout, stderr = popen.communicate()
    if popen.returncode != 0:
        raise subprocess.CalledProcessError(popen.returncode, popen.args, output=stdout, stderr=stderr)
    return audio_path
