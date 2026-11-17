"""Assemble rendered teaching shots; standard-library Python plus FFmpeg."""

import argparse
from fractions import Fraction
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import wave


SAMPLE_RATE = 48000


def ffmpeg_run(executable, arguments, cwd=None, loglevel='error'):
    command = [executable, '-hide_banner', '-nostdin', '-v', loglevel, '-xerror', *map(str, arguments)]
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        raise ValueError(f'FFmpeg exited {result.returncode}:\n{result.stderr[-5000:]}')
    return result


def check_ffmpeg(executable):
    filters = ffmpeg_run(executable, ['-filters']).stdout
    encoders = ffmpeg_run(executable, ['-encoders']).stdout
    if not re.search(r'\bass\s+V->V\b', filters) or not re.search(r'\blibx264\s', encoders):
        raise ValueError('Use an FFmpeg build with the ass (libass) filter and libx264 encoder.')


def tool_path(value):
    path = shutil.which(value)
    if not path and Path(value).is_file():
        path = value
    if not path:
        raise ValueError('FFmpeg was not found. Put it on PATH or pass --ffmpeg with its full path.')
    return str(Path(path).resolve())


def simple_text(text):
    if not isinstance(text, str) or not text.strip() or any(char in text for char in '{}\\\r\n'):
        raise ValueError('Caption and chapter text must be plain, single-line text without ASS control characters.')
    return text


def read_manifest(path):
    config = json.loads(path.read_text(encoding='utf-8-sig'))
    width, height = config['canvas']
    if any(type(value) is not int or value <= 0 or value % 2 for value in (width, height)):
        raise ValueError('canvas must contain two positive even dimensions.')
    fps = Fraction(str(config['fps']))
    if not 0 < fps <= 240 or fps.numerator > 1000000:
        raise ValueError('fps must be a positive integer or a rational such as 30000/1001.')
    corner = config.get('chapter_corner', 'left')
    if corner not in ('left', 'right'):
        raise ValueError('chapter_corner must be left or right.')
    font = config.get('font', 'sans-serif')
    if ',' in simple_text(font):
        raise ValueError('font must be one font family, without commas.')
    font_dir = path.parent / config['font_dir'] if config.get('font_dir') else None
    if font_dir is not None and not font_dir.is_dir():
        raise ValueError(f'Font directory was not found: {font_dir}')
    shots = config['shots']
    if not isinstance(shots, list) or not shots:
        raise ValueError('Provide at least one shot in the manifest.')
    ids = set()
    timeline = 0
    for shot in shots:
        sid = shot['id']
        if not isinstance(sid, str) or not sid or sid in ids:
            raise ValueError(f'Invalid or duplicate shot id: {sid!r}')
        ids.add(sid)
        if type(shot['frames']) is not int or shot['frames'] <= 0:
            raise ValueError(f'{sid}: frames must be a positive integer.')
        first = shot.get('start_frame', 0)
        if type(first) is not int or first < 0:
            raise ValueError(f'{sid}: start_frame must be a nonnegative integer.')
        if type(shot.get('still', False)) is not bool:
            raise ValueError(f'{sid}: still must be true or false.')
        for field in ('video', 'narration'):
            if field not in shot and field == 'narration':
                continue
            asset = (path.parent / shot[field]).resolve()
            if not asset.is_file():
                raise ValueError(f'{sid}: missing {field}: {asset}')
            shot[field] = asset
        if shot.get('chapter'):
            simple_text(shot['chapter'])
        last = Fraction(0)
        for caption in shot.get('captions', []):
            start, end = (Fraction(str(caption[key])) for key in ('start', 'end'))
            if not last <= start < end <= shot['frames'] / fps:
                raise ValueError(f'{sid}: a caption overlaps or exceeds the shot.')
            if round(start * 100) >= round(end * 100):
                raise ValueError(f'{sid}: a caption is shorter than ASS time precision.')
            simple_text(caption['text'])
            last = end
        shot['offset'] = timeline
        timeline += shot['frames']
    return width, height, fps, corner, font, font_dir, shots, timeline


def stamp(time):
    ticks = round(Fraction(str(time)) * 100)
    return f'{ticks // 360000}:{ticks // 6000 % 60:02}:{ticks // 100 % 60:02}.{ticks % 100:02}'


def write_ass(path, shot, fps, font, corner):
    title_alignment = 7 if corner == 'left' else 9
    header = f'''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{font},49,&H00FFFFFF,&H00FFFFFF,&H00121B24,&H50000000,0,0,0,0,100,100,0,0,1,2.5,0,2,115,115,57,1
Style: Chapter,{font},33,&H00FFFFFF,&H00FFFFFF,&H401E1208,&H401E1208,0,0,0,0,100,100,0,0,3,6,0,{title_alignment},56,56,25,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events = [f'Dialogue: 0,{stamp(cue["start"])},{stamp(cue["end"])},Caption,,0,0,0,,{cue["text"]}\n'
              for cue in shot.get('captions', [])]
    if shot.get('chapter'):
        end = stamp(shot['frames'] / fps + Fraction(1, 10))
        events.append(f'Dialogue: 1,0:00:00.00,{end},Chapter,,0,0,0,,{shot["chapter"]}\n')
    path.write_text(header + ''.join(events), encoding='utf-8-sig')
    return bool(events)


def append_narration(wav, shot, fps):
    start = round(shot['offset'] * SAMPLE_RATE / fps)
    end = round((shot['offset'] + shot['frames']) * SAMPLE_RATE / fps)
    needed = end - start
    written = 0
    if 'narration' in shot:
        with wave.open(str(shot['narration']), 'rb') as source:
            if (source.getnchannels(), source.getsampwidth(), source.getframerate(), source.getcomptype()) != (1, 2, SAMPLE_RATE, 'NONE'):
                raise ValueError(f"{shot['id']}: use 48 kHz mono PCM16 WAV for narration.")
            samples = source.getnframes()
            if samples > needed:
                raise ValueError(f"{shot['id']}: narration is longer than the shot by {(samples - needed) / SAMPLE_RATE:.3f} s.")
            while written < samples:
                chunk = source.readframes(min(samples - written, SAMPLE_RATE * 4))
                if not chunk or len(chunk) % 2:
                    raise ValueError(f"{shot['id']}: truncated WAV payload.")
                wav.writeframesraw(chunk)
                written += len(chunk) // 2
    while written < needed:
        block = min(SAMPLE_RATE * 4, needed - written)
        wav.writeframesraw(b'\0' * (block * 2))
        written += block


def encode_shot(executable, folder, shot, index, width, height, fps, font, corner, has_fonts):
    stem = f'shot_{index:05d}'
    arguments = ['-y']
    if shot.get('still', False):
        arguments += ['-loop', '1', '-framerate', str(fps)]
    arguments += ['-i', shot['video']]
    start = shot.get('start_frame', 0)
    filters = [f'fps={fps}:round=near', f'trim=start_frame={start}:end_frame={start + shot["frames"]}',
               'setpts=PTS-STARTPTS', f'scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2:flags=lanczos',
               f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2', 'setsar=1']
    if write_ass(folder / f'{stem}.ass', shot, fps, font, corner):
        filters.append(f'ass={stem}.ass' + (':fontsdir=fonts' if has_fonts else ''))
    filename = f'{stem}.mp4'
    ffmpeg_run(executable, [*arguments, '-map', '0:v:0', '-an', '-vf', ','.join(filters), '-c:v', 'libx264',
                            '-pix_fmt', 'yuv420p', '-preset', 'fast', '-crf', '17', '-r', fps, '-fps_mode', 'cfr',
                            '-enc_time_base:v', f'{fps.denominator}:{fps.numerator}', '-video_track_timescale', fps.numerator,
                            filename], cwd=folder)
    verify_video(executable, folder / filename, width, height, fps, shot['frames'], label=shot['id'])
    return filename


def verify_video(executable, path, width, height, fps, frames, label='Final video'):
    log = ffmpeg_run(executable, ['-i', path, '-map', '0:v:0', '-an', '-vf', 'showinfo=checksum=0',
                                  '-fps_mode', 'passthrough', '-f', 'null', '-'], loglevel='info').stderr
    match = re.search(r'config in time_base:\s*(\d+/\d+)', log)
    if not match:
        raise ValueError(f'{label}: no video time base decoded.')
    time_base = Fraction(match[1])
    detected = re.findall(r'\bn:\s*(\d+)\s+pts:\s*(-?\d+)\s+pts_time:[^\r\n]*?\bs:(\d+)x(\d+)', log)
    if len(detected) != frames:
        raise ValueError(f'{label}: expected {frames} video frames; decoded {len(detected)}. Check source duration and cut points.')
    for i, (number, pts, w, h) in enumerate(detected):
        if int(number) != i or int(pts) * time_base != Fraction(i, 1) / fps or (int(w), int(h)) != (width, height):
            raise ValueError(f'{label}: wrong dimensions or timestamp at frame {i}.')


def build(executable, manifest, output):
    width, height, fps, corner, font, font_dir, shots, total = read_manifest(manifest)
    report = output.with_suffix('.report.json')
    if output.exists() or report.exists() or output.suffix.lower() != '.mp4':
        raise ValueError('Choose a new .mp4 output filename whose .report.json does not already exist.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.course-', dir=output.parent) as work:
        folder = Path(work)
        if font_dir:
            (folder / 'fonts').mkdir()
            for entry in font_dir.iterdir():
                if entry.is_file() and entry.suffix.lower() in ('.ttf', '.ttc', '.otf'):
                    shutil.copy2(entry, folder / 'fonts' / entry.name)
        with wave.open(str(folder / 'narration.wav'), 'wb') as audio:
            audio.setparams((1, 2, SAMPLE_RATE, 0, 'NONE', 'not compressed'))
            for shot in shots:
                append_narration(audio, shot, fps)

        listing = ['ffconcat version 1.0']
        timeline = []
        for index, shot in enumerate(shots):
            filename = encode_shot(executable, folder, shot, index, width, height, fps, font, corner, bool(font_dir))
            first, last = shot['offset'], shot['offset'] + shot['frames']
            micros = round(last * 1000000 / fps) - round(first * 1000000 / fps)
            listing.extend([f"file '{filename}'", f'duration {micros // 1000000}.{micros % 1000000:06d}'])
            timeline.append({'id': shot['id'], 'first_frame': first, 'end_frame_exclusive': last})
            print(f"{shot['id']}: {shot['frames']} frames verified", flush=True)
        (folder / 'shots.ffconcat').write_text('\n'.join(listing) + '\n', encoding='ascii')
        temporary = folder / 'course.mp4'
        ffmpeg_run(executable, ['-f', 'concat', '-safe', '1', '-i', 'shots.ffconcat', '-i', 'narration.wav',
                                '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-video_track_timescale', fps.numerator,
                                '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', temporary], cwd=folder)
        verify_video(executable, temporary, width, height, fps, total)
        pcm = folder / 'audio.pcm'
        ffmpeg_run(executable, ['-i', temporary, '-map', '0:a:0', '-vn', '-ar', SAMPLE_RATE, '-ac', '1', '-f', 's16le', pcm])
        audio_samples = pcm.stat().st_size // 2
        expected = round(total * SAMPLE_RATE / fps)
        if not expected - 1 <= audio_samples <= expected + 1024:
            raise ValueError(f'Unexpected decoded audio length: {audio_samples} samples, expected {expected} plus AAC padding.')
        temporary.replace(output)
        result = {'file': output.name, 'width': width, 'height': height, 'fps': str(fps), 'decoded_frames': total,
                  'duration_seconds': float(total / fps), 'decoded_audio_samples_at_48k': audio_samples, 'shots': timeline}
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Verified and saved: {output} ({width}x{height}, {fps} fps, {total} frames)', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffmpeg', default='ffmpeg', help='FFmpeg executable name or absolute path')
    subcommands = parser.add_subparsers(dest='command', required=True)
    subcommands.add_parser('doctor', help='Check FFmpeg and required capabilities')
    assemble = subcommands.add_parser('build', help='Assemble and verify the course MP4')
    assemble.add_argument('manifest', type=Path)
    assemble.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        executable = tool_path(args.ffmpeg)
        check_ffmpeg(executable)
        if args.command == 'doctor':
            print(f'OK: {executable} (libass and libx264 available)')
        else:
            build(executable, args.manifest.resolve(), args.output.resolve())
    except (OSError, ValueError, TypeError, KeyError, ZeroDivisionError, EOFError, wave.Error) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
