import asyncio
import random
import time
import wave
import opuslib
from pathlib import Path
from datetime import datetime
import discord
from discord.ext.voice_recv import AudioSink, VoiceData
from core.logger import logging, SHH_BOT
from faster_whisper import WhisperModel

logger = logging.getLogger(SHH_BOT)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

CHANNELS = 2
SAMPLE_WIDTH = 2
SAMPLING_RATE = 48000
FRAME_DURATION_MS = 20
SAMPLES_PER_FRAME = SAMPLING_RATE * FRAME_DURATION_MS // 1000
BYTES_PER_FRAME = SAMPLES_PER_FRAME * CHANNELS * SAMPLE_WIDTH

RTP_MAX = 2**32

DISCORD_FILE_LIMIT = 25 * 1024 * 1024

ARNNDN_MODEL: Path | None = BASE_DIR / "arnndn-models" / "sh.rnnn"


def _rtp_diff(a: int, b: int) -> int:
    d = (a - b) & 0xFFFFFFFF
    return d if d < RTP_MAX // 2 else d - RTP_MAX


class _PerSsrcState:
    def __init__(self, path: Path):
        self.path = path
        self.wf = wave.open(str(path), "wb")
        self.wf.setnchannels(CHANNELS)
        self.wf.setsampwidth(SAMPLE_WIDTH)
        self.wf.setframerate(SAMPLING_RATE)
        self.decoder = opuslib.Decoder(SAMPLING_RATE, CHANNELS)
        self.last_rtp_ts: int | None = None
        self.buf = bytearray()
        self.pending_frames = 0

    def flush(self):
        if self.buf:
            self.wf.writeframes(bytes(self.buf))
            self.buf.clear()
        self.pending_frames = 0

    def close(self):
        self.flush()
        try:
            self.wf.close()
        except Exception:
            pass


class SSRCWaveSink(AudioSink):

    FLUSH_EVERY = 10

    def __init__(self, recordings_dir: Path, timestamp: str):
        super().__init__()
        self._recordings_dir = recordings_dir
        self._timestamp = timestamp
        self._ssrcs: dict[int, _PerSsrcState] = {}
        self._packet_count = 0
        self._last_log = 0.0

    def wants_opus(self) -> bool:
        return True

    def write(self, user: discord.User | None, data: VoiceData):
        self._packet_count += 1
        now = time.monotonic()
        if now - self._last_log >= 5.0:
            logger.info(
                f"Sink: {self._packet_count} packets, SSRCs={list(self._ssrcs.keys())}"
            )
            self._last_log = now

        opus_bytes: bytes | None = data.opus
        if not opus_bytes:
            return

        ssrc = data.packet.ssrc
        rtp_ts = data.packet.timestamp

        if ssrc not in self._ssrcs:
            path = self._recordings_dir / f"ssrc_{ssrc}_{self._timestamp}.wav"
            self._ssrcs[ssrc] = _PerSsrcState(path)
            logger.info(f"New SSRC {ssrc} -> {path.name}")

        state = self._ssrcs[ssrc]

        if state.last_rtp_ts is not None:
            gap_samples = _rtp_diff(rtp_ts, state.last_rtp_ts)
            missed = (gap_samples - SAMPLES_PER_FRAME) // SAMPLES_PER_FRAME
            if 0 < missed <= 50:
                logger.debug(f"SSRC {ssrc}: filling {missed} missing frame(s)")
                for _ in range(missed):
                    try:
                        plc_pcm = state.decoder.decode(None, SAMPLES_PER_FRAME)
                        state.buf.extend(plc_pcm)
                    except Exception:
                        state.buf.extend(b'\x00' * BYTES_PER_FRAME)
            elif missed > 50:
                silence_bytes = min(missed, 300) * BYTES_PER_FRAME
                state.buf.extend(b'\x00' * silence_bytes)

        try:
            pcm = state.decoder.decode(opus_bytes, SAMPLES_PER_FRAME)
            state.buf.extend(pcm)
        except Exception as e:
            logger.warning(f"SSRC {ssrc}: Opus decode error: {e} -- inserting silence")
            state.buf.extend(b'\x00' * BYTES_PER_FRAME)

        state.last_rtp_ts = rtp_ts
        state.pending_frames += 1
        if state.pending_frames >= self.FLUSH_EVERY:
            state.flush()

    def cleanup(self):
        for state in self._ssrcs.values():
            state.close()
        self._ssrcs.clear()

    @property
    def ssrcs(self) -> list[int]:
        return list(self._ssrcs.keys())

    def get_path(self, ssrc: int) -> Path | None:
        state = self._ssrcs.pop(ssrc, None)
        if state is None:
            return None
        state.close()
        return state.path


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
        self._recordings_dir = BASE_DIR.parent / "recordings"
        self._recordings_dir.mkdir(exist_ok=True)
        self._recording = False
        self._sink: SSRCWaveSink | None = None
        self._voice_client = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._text_channel: discord.TextChannel | None = None
        self._keep_wav = False

    @property
    def is_recording(self):
        return self._recording

    def start(
        self,
        voice_client,
        text_channel: discord.TextChannel,
        loop: asyncio.AbstractEventLoop,
        keep_wav: bool = False,
    ):
        self._loop = loop
        self._text_channel = text_channel
        self._voice_client = voice_client
        self._keep_wav = keep_wav
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._sink = SSRCWaveSink(self._recordings_dir, timestamp)
        voice_client.listen(self._sink, after=self._on_stop)
        self._recording = True
        logger.info(
            f"Recording started (mode={voice_client.mode}, ssrc={voice_client.ssrc})"
        )

    def stop(self, voice_client):
        self._recording = False
        voice_client.stop_listening()

    def _on_stop(self, error: Exception | None):
        self._recording = False
        ssrcs = list(self._sink.ssrcs) if self._sink else []
        paths: dict[int, Path] = {}
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

    @staticmethod
    def _split_at_word(text: str, limit: int) -> tuple[str, str]:
        if len(text) <= limit:
            return text, ""
        cut = text.rfind(" ", 0, limit)
        if cut == -1:
            return text[:limit], text[limit:]
        return text[:cut], text[cut + 1:]

    def _split_content(self, prefix: str, text: str) -> list[str]:
        if not text:
            return [f"{prefix}*[no speech detected]*"]
        first_max = 1900
        rest_max = 2000
        first_msg = f"{prefix}{text}"
        if len(first_msg) <= first_max:
            return [first_msg]
        result = []
        remaining = text
        limit = first_max - len(prefix)
        chunk, remaining = self._split_at_word(remaining, limit)
        result.append(f"{prefix}{chunk}")
        while remaining:
            chunk, remaining = self._split_at_word(remaining, rest_max)
            result.append(chunk)
        return result

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
            logger.info(f"SSRC {ssrc} WAV: {size_mb:.1f} MB")

            user_id = client._get_id_from_ssrc(ssrc) if client else None
            user = text_channel.guild.get_member(user_id) if user_id else None

            processed_wav = await self._enhance_audio(wav_path)

            transcript = await self._transcribe(processed_wav or wav_path)

            mp3_path = await self._wav_to_mp3(processed_wav or wav_path)

            results.append((user, transcript, wav_path, processed_wav, mp3_path))

        if not results:
            await text_channel.send("No audio files found to process.")
            return

        msg = await text_channel.send(f"Recording finished -- **{thread_name}**")
        thread = await msg.create_thread(name=thread_name)

        for user, transcript, wav_path, processed_wav, mp3_path in results:
            display = f"<@{user.id}>" if user else f"SSRC {wav_path.stem.split('_')[1]}"

            if transcript:
                prefix = f"**{display}**: "
                messages = self._split_content(prefix, transcript)
            else:
                messages = [f"**{display}**: *[no speech detected]*"]

            upload_path = await self._select_upload_file(processed_wav or wav_path, mp3_path)
            upload_name = upload_path.name

            upload_success = False
            try:
                await thread.send(
                    messages[0], file=discord.File(str(upload_path), filename=upload_name)
                )
                upload_success = True
                for m in messages[1:]:
                    await thread.send(m)
            except Exception as e:
                logger.error(f"Upload failed for {upload_path.name}: {e}")
                try:
                    await text_channel.send(
                        f"**{display}**: transcript preserved, but audio upload failed ({e}).\n"
                        f"File kept at: `{upload_path}`"
                    )
                except Exception:
                    pass

            if upload_success:
                for p in (mp3_path, processed_wav):
                    if p and p.exists():
                        p.unlink(missing_ok=True)
                if wav_path.exists() and not self._keep_wav:
                    wav_path.unlink(missing_ok=True)
            else:
                logger.info(f"Preserved local file: {upload_path}")

        logger.info(f"Recording finished: {thread_name}")
        self._sink = None
        self._voice_client = None

    async def _enhance_audio(self, wav_path: Path) -> Path | None:
        out_path = wav_path.with_name(wav_path.stem + "_enhanced.wav")

        filters = [
            "highpass=f=80",
            "lowpass=f=12000",
        ]

        if ARNNDN_MODEL and ARNNDN_MODEL.exists():
            filters.insert(0, f"arnndn=m='{ARNNDN_MODEL}':mix=0.85")
        else:
            logger.info("arnndn model not found -- skipping neural denoising")

        filters += [
            "acompressor=threshold=-18dB:ratio=2:attack=5:release=100:makeup=2dB",
            "loudnorm=I=-16:TP=-2:LRA=7",
        ]

        af = ",".join(filters)

        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y",
                "-i", str(wav_path),
                "-af", af,
                "-ar", str(SAMPLING_RATE),
                "-ac", str(CHANNELS),
                str(out_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.error(
                    f"Audio enhancement failed for {wav_path.name}: "
                    f"{stderr.decode(errors='replace')[:500]}"
                )
                return None
            enh_mb = out_path.stat().st_size / (1024 * 1024)
            logger.info(f"Enhanced {wav_path.name} -> {out_path.name} ({enh_mb:.1f} MB)")
            return out_path
        except FileNotFoundError:
            logger.error("ffmpeg not found -- skipping enhancement")
            return None
        except Exception as e:
            logger.error(f"Enhancement error for {wav_path.name}: {e}")
            return None

    async def _select_upload_file(self, wav_path: Path, mp3_path: Path | None) -> Path:
        if mp3_path and mp3_path.exists() and mp3_path.stat().st_size <= DISCORD_FILE_LIMIT:
            return mp3_path
        if mp3_path and mp3_path.exists():
            mp3_path.unlink(missing_ok=True)
        for bitrate in ("64k", "32k"):
            new_mp3 = await self._wav_to_mp3(wav_path, bitrate=bitrate)
            if new_mp3 and new_mp3.exists() and new_mp3.stat().st_size <= DISCORD_FILE_LIMIT:
                return new_mp3
            if new_mp3:
                new_mp3.unlink(missing_ok=True)
        return wav_path

    async def _wav_to_mp3(self, wav_path: Path, bitrate: str = "128k") -> Path | None:
        mp3_path = wav_path.with_suffix(".mp3")
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y",
                "-i", str(wav_path),
                "-codec:a", "libmp3lame",
                "-b:a", bitrate,
                "-ar", str(SAMPLING_RATE),
                "-ac", str(CHANNELS),
                str(mp3_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.error(
                    f"ffmpeg failed for {wav_path.name}: "
                    f"{stderr.decode(errors='replace')[:500]}"
                )
                return None
            mp3_size = mp3_path.stat().st_size / (1024 * 1024)
            logger.info(
                f"Converted {wav_path.name} -> {mp3_path.name} ({mp3_size:.1f} MB at {bitrate})"
            )
            return mp3_path
        except FileNotFoundError:
            logger.error("ffmpeg not found, falling back to WAV upload")
            return None
        except Exception as e:
            logger.error(f"ffmpeg conversion error for {wav_path.name}: {e}")
            return None

    async def _transcribe(self, audio_path: Path) -> str | None:
        try:
            result, info = await asyncio.to_thread(
                self._transcribe_sync, str(audio_path),
            )
            logger.debug(
                f"Whisper: lang={info.language} prob={info.language_probability:.2f}"
            )
            if result:
                logger.debug(
                    f"Whisper result: '{result[:200]}'" + ("..." if len(result) > 200 else "")
                )
            return result or None
        except Exception as e:
            logger.error(f"Transcription failed for {audio_path.name}: {e}")
            return None

    def _transcribe_sync(self, audio_path: str) -> tuple[str | None, object]:
        segments, info = self._model.transcribe(
            audio_path, beam_size=5, vad_filter=False, no_speech_threshold=0.8,
        )
        texts = [seg.text for seg in segments]
        result = " ".join(texts).strip()
        return (result, info)
