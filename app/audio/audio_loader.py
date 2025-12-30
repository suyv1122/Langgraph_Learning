from __future__ import annotations

import subprocess
from pathlib import Path

def ensure_dir(p: Path) -> None:
    """此函数用于确保路径存在"""
    p.mkdir(parents=True, exist_ok=True)


def ffprobe_duration_ms(src: Path) -> int:
    """确认音频时长，并以毫秒为单位计数"""
    cmd = [
        '/tmp/ffprobe/ffprobe', # 确认本地ffprobe路径，此块代码将于终端执行
        '-v', 'error',
        '-show_entries','format=duration',
        '-of','default=noprint_wrappers=1:nokey=1',
        str(src)
    ]
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8').strip()
    if not out:
        return 0
    sec = float(out)
    return int(sec * 1000)  # 音频时长，以毫秒为单位计数


def transcode_to_wav_16k_mono(src: Path, dst: Path) -> None:
    """将音频文件转换为wav_16k格式，需要原始文件路径，以及转换后的保存路径"""
    ensure_dir(dst.parent)
    cmd = [
        '/tmp/ffmpeg/ffmpeg',   # 同上，本地路径
        '-y',
        '-i', str(src),
        '-ac','1',
        '-ar','16000',
        '-vn',
        str(dst)
    ]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == '__main__':
    print(ffprobe_duration_ms(Path('../data/test.m4a')))
    transcode_to_wav_16k_mono(Path('../data/test.m4a'), Path('../data/test.wav'))