import asyncio
import random
import time
import struct
import wave
from pathlib import Path
from datetime import datetime
import discord
from discord.ext.voice_recv import AudioSink, VoiceData
from util.logger import logging, SHH_BOT
from faster_whisper import WhisperModel

logger = logging.getLogger(SHH_BOT)

BASE_DIR = Path(__file__).resolve().parent.parent

CHANNELS = 2
SAMPLE_WIDTH = 2
SAMPLING_RATE = 48000


class SSRCWaveSink(AudioSink):

    def __init__(self, recordings_dir: Path, timestamp: str):
        super().__init__()
        self._recordings_dir = recordings_dir
        self._timestamp = timestamp
        self._files: dict[int, wave.Wave_write] = {}
        self._packet_count = 0
        self._last_log = 0.0

    def wants_opus(self) -> bool:
        return False

    def write(self, user: discord.User | None, data: VoiceData):
        self._packet_count += 1
        now = time.monotonic()
        if now - self._last_log >= 5.0:
            logger.info(f"Sink: {self._packet_count} packets, SSRCs={list(self._files.keys())}")
            self._last_log = now

        ssrc = data.packet.ssrc
        if ssrc not in self._files:
            path = self._recordings_dir / f"ssrc_{ssrc}_{self._timestamp}.wav"
            wf = wave.open(str(path), "wb")
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(SAMPLING_RATE)
            self._files[ssrc] = wf

        if data.pcm:
            self._files[ssrc].writeframes(data.pcm)

    def cleanup(self):
        for wf in self._files.values():
            try:
                wf.close()
            except Exception:
                pass
        self._files.clear()

    @property
    def ssrcs(self) -> list[int]:
        return list(self._files.keys())

    def get_path(self, ssrc: int) -> Path | None:
        if ssrc not in self._files:
            return None
        wf = self._files.pop(ssrc)
        wf.close()
        return self._recordings_dir / f"ssrc_{ssrc}_{self._timestamp}.wav"


class TranscriptionService:

    _adjectives = [
        "Wobbly", "Funky", "Zesty", "Soggy", "Grumpy",
        "Fuzzy", "Janky", "Boopy", "Crusty", "Wiggly",
        "Blorpy", "Honky", "Slurpy", "Floofy", "Dingy",
        "Sporky", "Wonky", "Noodly", "Bumpy", "Zonky",
    ]

    _nouns = [
        "Banana", "Wombat", "Pickle", "Nacho", "Pancake",
        "Nugget", "Sausage", "Goblin", "Squid", "Muffin",
        "Blorb", "Dingus", "Snoot", "Giblet", "Waffle",
        "Zoodle", "Bingle", "Crumpet", "Doohickey", "Poingo",
    ]

    def __init__(self):
        self._model = WhisperModel("base", device="cpu", compute_type="int8")
        self._recordings_dir = BASE_DIR / "recordings"
        self._recordings_dir.mkdir(exist_ok=True)
        self._recording = False
        self._sink: SSRCWaveSink | None = None
        self._voice_client = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._text_channel: discord.TextChannel | None = None

    @property
    def is_recording(self):
        return self._recording

    def start(self, voice_client, text_channel: discord.TextChannel, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        self._text_channel = text_channel
        self._voice_client = voice_client
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._sink = SSRCWaveSink(self._recordings_dir, timestamp)
        voice_client.listen(self._sink, after=self._on_stop)
        self._recording = True
        logger.info(f"Recording started (mode={voice_client.mode}, ssrc={voice_client.ssrc})")

    def stop(self, voice_client):
        self._recording = False
        voice_client.stop_listening()

    def _on_stop(self, error: Exception | None):
        self._recording = False
        ssrcs = list(self._sink.ssrcs) if self._sink else []
        paths = {}
        for ssrc in ssrcs:
            p = self._sink.get_path(ssrc)
            if p:
                paths[ssrc] = p
        asyncio.run_coroutine_threadsafe(
            self._process(error, ssrcs, paths), self._loop
        )

    def _goofy_name(self) -> str:
        adj = random.choice(self._adjectives)
        noun = random.choice(self._nouns)
        return f"{adj}{noun}"

    def _analyze_pcm(self, wav_path: Path, ssrc: int) -> None:
        raw = wav_path.read_bytes()
        pcm_data = raw[44:]
        if len(pcm_data) < 4:
            return
        pcm_slice = pcm_data[:200000]
        sample_count = len(pcm_slice) // 2
        samples = struct.unpack(f"<{sample_count}h", pcm_slice)
        if CHANNELS == 2 and len(samples) >= 2:
            left = samples[::2]
            right = samples[1::2]
            l_peak = max(abs(s) for s in left) if left else 0
            r_peak = max(abs(s) for s in right) if right else 0
            l_avg = sum(abs(s) for s in left) / len(left) if left else 0
            r_avg = sum(abs(s) for s in right) / len(right) if right else 0
            r_zero_pct = sum(1 for s in right if s == 0) / len(right) * 100 if right else 0
            logger.info(f"SSRC {ssrc} PCM: L_peak={l_peak} L_avg={l_avg:.1f}  R_peak={r_peak} R_avg={r_avg:.1f} R_zero={r_zero_pct:.1f}%")
        else:
            peak = max(abs(s) for s in samples) if samples else 0
            avg = sum(abs(s) for s in samples) / len(samples) if samples else 0
            zero_pct = sum(1 for s in samples if s == 0) / len(samples) * 100 if samples else 0
            logger.info(f"SSRC {ssrc} PCM: peak={peak} avg_abs={avg:.1f} zero={zero_pct:.1f}% samples={len(samples)}")

    async def _process(self, error: Exception | None, ssrcs: list, paths: dict):
        text_channel = self._text_channel
        client = self._voice_client
        if text_channel is None or self._sink is None:
            return

        if not ssrcs:
            await text_channel.send("No speech detected during the recording session.")
            return

        if error:
            logger.error(f"Recording error: {error}")

        date_str = datetime.now().strftime("%Y-%m-%d")
        goofy = self._goofy_name()
        thread_name = f"Recording - {date_str} - {goofy}"

        results = []

        for ssrc in ssrcs:
            wav_path = paths.get(ssrc)
            if wav_path is None or not wav_path.exists():
                continue
            size_mb = wav_path.stat().st_size / (1024 * 1024)
            logger.info(f"SSRC {ssrc} WAV: {size_mb:.1f}MB")

            self._analyze_pcm(wav_path, ssrc)

            user_id = client._get_id_from_ssrc(ssrc) if client else None
            user = text_channel.guild.get_member(user_id) if user_id else None

            transcript = await self._transcribe(wav_path)

            mp3_path = await self._wav_to_mp3(wav_path)
            upload_path = mp3_path if mp3_path else wav_path
            upload_name = upload_path.name

            results.append((user, transcript, upload_path, upload_name))

            wav_path.unlink(missing_ok=True)

        msg = await text_channel.send(f"Recording finished — **{thread_name}**")
        thread = await msg.create_thread(name=thread_name)

        for user, transcript, upload_path, upload_name in results:
            display = f"<@{user.id}>" if user else f"SSRC {upload_path.stem.rsplit('_', 1)[0]}"
            content = f"**{display}**: {transcript}" if transcript else f"**{display}**: *[no speech detected]*"

            try:
                await thread.send(content, file=discord.File(str(upload_path), filename=upload_name))
            except Exception as e:
                await thread.send(f"{content}\n*(failed to upload audio: {e})*")

            upload_path.unlink(missing_ok=True)

        logger.info(f"Recording finished: {thread_name}")
        self._sink = None
        self._voice_client = None

    async def _wav_to_mp3(self, wav_path: Path) -> Path | None:
        mp3_path = wav_path.with_suffix('.mp3')
        try:
            proc = await asyncio.create_subprocess_exec(
                'ffmpeg', '-y',
                '-i', str(wav_path),
                '-codec:a', 'libmp3lame',
                '-b:a', '64k',
                '-ar', str(SAMPLING_RATE),
                '-ac', str(CHANNELS),
                str(mp3_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.error(f"ffmpeg failed for {wav_path.name}: {stderr.decode(errors='replace')[:500]}")
                return None
            mp3_size = mp3_path.stat().st_size / (1024 * 1024)
            logger.info(f"Converted {wav_path.name} -> {mp3_path.name} ({mp3_size:.1f}MB)")
            return mp3_path
        except FileNotFoundError:
            logger.error("ffmpeg not found, falling back to WAV upload")
            return None
        except Exception as e:
            logger.error(f"ffmpeg conversion error for {wav_path.name}: {e}")
            return None

    async def _transcribe(self, audio_path: Path) -> str | None:
        try:
            segments, info = await asyncio.to_thread(
                self._model.transcribe,
                str(audio_path),
                beam_size=5,
                vad_filter=False,
                no_speech_threshold=0.8,
            )
            logger.debug(f"Whisper: lang={info.language} prob={info.language_probability:.2f}")
            texts = []
            for seg in segments:
                logger.debug(f"Whisper segment [{seg.start:.1f}->{seg.end:.1f}] '{seg.text}'")
                texts.append(seg.text)
            result = " ".join(texts).strip()
            logger.debug(f"Whisper result: '{result[:200]}'" + ("..." if len(result) > 200 else ""))
            return result or None
        except Exception as e:
            logger.error(f"Transcription failed for {audio_path.name}: {e}")
            return None
