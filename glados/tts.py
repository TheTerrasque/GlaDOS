import ctypes
import os
import re
import sys
import tempfile
from typing import List, Optional

import numpy as np
import onnxruntime
import sounddevice as sd

# Constants
MAX_WAV_VALUE = 32767.0
RATE = 22050

# Settings
MODEL_PATH = "./models/glados.onnx"
USE_CUDA = True

# Conversions
PAD = "_"  # padding (0)
BOS = "^"  # beginning of sentence
EOS = "$"  # end of sentence
PHONEME_ID_MAP = {
    " ": [3],
    "!": [4],
    '"': [150],
    "#": [149],
    "$": [2],
    "'": [5],
    "(": [6],
    ")": [7],
    ",": [8],
    "-": [9],
    ".": [10],
    "0": [130],
    "1": [131],
    "2": [132],
    "3": [133],
    "4": [134],
    "5": [135],
    "6": [136],
    "7": [137],
    "8": [138],
    "9": [139],
    ":": [11],
    ";": [12],
    "?": [13],
    "X": [156],
    "^": [1],
    "_": [0],
    "a": [14],
    "b": [15],
    "c": [16],
    "d": [17],
    "e": [18],
    "f": [19],
    "g": [154],
    "h": [20],
    "i": [21],
    "j": [22],
    "k": [23],
    "l": [24],
    "m": [25],
    "n": [26],
    "o": [27],
    "p": [28],
    "q": [29],
    "r": [30],
    "s": [31],
    "t": [32],
    "u": [33],
    "v": [34],
    "w": [35],
    "x": [36],
    "y": [37],
    "z": [38],
    "æ": [39],
    "ç": [40],
    "ð": [41],
    "ø": [42],
    "ħ": [43],
    "ŋ": [44],
    "œ": [45],
    "ǀ": [46],
    "ǁ": [47],
    "ǂ": [48],
    "ǃ": [49],
    "ɐ": [50],
    "ɑ": [51],
    "ɒ": [52],
    "ɓ": [53],
    "ɔ": [54],
    "ɕ": [55],
    "ɖ": [56],
    "ɗ": [57],
    "ɘ": [58],
    "ə": [59],
    "ɚ": [60],
    "ɛ": [61],
    "ɜ": [62],
    "ɞ": [63],
    "ɟ": [64],
    "ɠ": [65],
    "ɡ": [66],
    "ɢ": [67],
    "ɣ": [68],
    "ɤ": [69],
    "ɥ": [70],
    "ɦ": [71],
    "ɧ": [72],
    "ɨ": [73],
    "ɪ": [74],
    "ɫ": [75],
    "ɬ": [76],
    "ɭ": [77],
    "ɮ": [78],
    "ɯ": [79],
    "ɰ": [80],
    "ɱ": [81],
    "ɲ": [82],
    "ɳ": [83],
    "ɴ": [84],
    "ɵ": [85],
    "ɶ": [86],
    "ɸ": [87],
    "ɹ": [88],
    "ɺ": [89],
    "ɻ": [90],
    "ɽ": [91],
    "ɾ": [92],
    "ʀ": [93],
    "ʁ": [94],
    "ʂ": [95],
    "ʃ": [96],
    "ʄ": [97],
    "ʈ": [98],
    "ʉ": [99],
    "ʊ": [100],
    "ʋ": [101],
    "ʌ": [102],
    "ʍ": [103],
    "ʎ": [104],
    "ʏ": [105],
    "ʐ": [106],
    "ʑ": [107],
    "ʒ": [108],
    "ʔ": [109],
    "ʕ": [110],
    "ʘ": [111],
    "ʙ": [112],
    "ʛ": [113],
    "ʜ": [114],
    "ʝ": [115],
    "ʟ": [116],
    "ʡ": [117],
    "ʢ": [118],
    "ʦ": [155],
    "ʰ": [145],
    "ʲ": [119],
    "ˈ": [120],
    "ˌ": [121],
    "ː": [122],
    "ˑ": [123],
    "˞": [124],
    "ˤ": [146],
    "̃": [141],
    "̧": [140],
    "̩": [144],
    "̪": [142],
    "̯": [143],
    "̺": [152],
    "̻": [153],
    "β": [125],
    "ε": [147],
    "θ": [126],
    "χ": [127],
    "ᵻ": [128],
    "↑": [151],
    "↓": [148],
    "ⱱ": [129],
}


class Phonemizer:
    """
    A class to handle phoneme conversion using the espeak-ng library.

    Attributes:
    -----------
    lib_espeak: ctypes.CDLL
        The loaded espeak-ng library.
    libc: ctypes.CDLL
        The C standard library, used for memory stream operations.

    Methods:
    --------
    __init__(self):
        Initializes the Phonemizer class, loading necessary libraries.

    synthesize_phonemes(self, text):
        Converts the given text to phonemes.

    _load_library(lib_name, fallback_name=None):
        Loads a shared library with an optional fallback.

    _open_memstream(self):
        Opens a memory stream for phoneme output.

    _close_memstream(self, file):
        Closes the opened memory stream.
    """

    # espeak-ng constants
    espeakPHONEMES_IPA = 0x02
    espeakCHARS_AUTO = 0
    espeakPHONEMES = 0x100
    espeakAUDIO_OUTPUT_SYNCHRONOUS = 0x02
    espeakVOICE = "en-us"

    def __init__(self, espeakng_path: str = ""):
        if sys.platform.startswith('win32'):
            self.libc = None
            self.msvcrt = ctypes.CDLL('msvcrt.dll')
            self.msvcrt.fseek.argtypes = [ctypes.c_void_p, ctypes.c_long, ctypes.c_int]
            self.msvcrt.fread.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t, ctypes.c_void_p]
            self.msvcrt.fread.restype = ctypes.c_size_t
        else:
            self.libc = ctypes.cdll.LoadLibrary("libc.so.6")
            self.libc.open_memstream.restype = ctypes.POINTER(ctypes.c_char)
        self.lib_espeak = self._load_library(os.path.join(espeakng_path, "libespeak-ng.so"))
        self.set_voice_by_name(self.espeakVOICE.encode("utf-8"))

    def set_voice_by_name(self, name) -> int:
        """Bindings to espeak_SetVoiceByName

        Parameters
        ----------
        name (str) : the voice name to setup

        Returns
        -------
        0 on success, non-zero integer on failure

        """
        f_set_voice_by_name = self.lib_espeak.espeak_SetVoiceByName
        f_set_voice_by_name.argtypes = [ctypes.c_char_p]
        return f_set_voice_by_name(name)

    def _load_library(self, lib_name):
        try:
            if sys.platform.startswith('linux'):
                return ctypes.CDLL(lib_name)
            elif sys.platform.startswith('win32'):
                return ctypes.CDLL(lib_name.replace("so", "dll"))
            else:
                raise OSError("Unsupported OS")
        except Exception as e:
            print(f"Failed to load library {lib_name}: {str(e)}")
            raise

    def _load_library_(self, lib_name, fallback_name=None):
        """Loads a shared library with an optional fallback."""
        try:
            return ctypes.cdll.LoadLibrary(lib_name)
        except OSError:
            if fallback_name:
                print(f"Loading {fallback_name}")
                return ctypes.cdll.LoadLibrary(fallback_name)
            else:
                raise

    def _open_tempfile(self):
        # Create a temporary file and return the file descriptor and path
        temp_fd, temp_path = tempfile.mkstemp()
        # Convert file descriptor to FILE* using fdopen
        FILE_p = ctypes.POINTER(ctypes.c_void_p)
        self.msvcrt._fdopen.argtypes = [ctypes.c_int, ctypes.c_char_p]
        self.msvcrt._fdopen.restype = ctypes.POINTER(ctypes.c_void_p)
        c_file = self.msvcrt._fdopen(temp_fd, b'w+b')
        return c_file, temp_path

    def _open_memstream(self):
        """Opens a memory stream for phoneme output."""
        buffer = ctypes.c_char_p()
        size = ctypes.c_size_t()  # Initialize size

        file = self.libc.open_memstream(ctypes.byref(buffer), ctypes.byref(size))
        return file, buffer, size

    def _close_memstream(self, file):
        """Closes the opened memory stream."""
        self.libc.fclose(file)

    def synthesize_phonemes(self, text):
        """
        Converts the given text to phonemes.

        Parameters:
        -----------
        text : str
            The text to be converted into phonemes.

        Returns:
        --------
        list of str
            The phonemes generated from the text.
        """
        # phonemes_file, phonemes_buffer = self._open_memstream()
        if self.libc:
            (
                phonemes_file,
                phonemes_buffer,
                size,
            ) = self._open_memstream()  # Capture the size
        else:
            phonemes_file, phonemes_path = self._open_tempfile()

        self.lib_espeak.espeak_Initialize(
            self.espeakAUDIO_OUTPUT_SYNCHRONOUS, 0, None, 0
        )

        try:
            phoneme_flags = self.espeakPHONEMES_IPA
            synth_flags = self.espeakCHARS_AUTO | self.espeakPHONEMES

            print("Calling espeak_SetPhonemeTrace")
            self.lib_espeak.espeak_SetPhonemeTrace(phoneme_flags, phonemes_file)
            text_bytes = text.encode("utf-8")


            print("Calling espeak_Synth")
            self.lib_espeak.espeak_Synth(
                text_bytes,
                0,  # buflength (unused in AUDIO_OUTPUT_SYNCHRONOUS mode)
                0,  # position
                0,  # position_type
                0,  # end_position (no end position)
                synth_flags,
                None,  # unique_speaker,
                None,  # user_data,
            )

            print("Retrieving phonemes")
            if self.libc:
                self.libc.fflush(phonemes_file)
                phonemes_data_length = size.value  # Get the actual size of the phoneme data
                phonemes = ctypes.string_at(
                    phonemes_buffer, phonemes_data_length
                )  # Use size to read buffer
                phonemes = phonemes.decode("utf-8")                
            else:
                print("Flushing")
                self.msvcrt.fflush(phonemes_file)
                print("Seeking")
                self.msvcrt.fseek(phonemes_file, 0, ctypes.c_int(0))
                print("Reading")
                buffer = ctypes.create_string_buffer(10000)
                num_bytes_read = self.msvcrt.fread(buffer, 1, 10000, phonemes_file)
                phonemes = buffer[:num_bytes_read].decode('utf-8')
            # phonemes = ctypes.string_at(phonemes_buffer)


            # There was a weird bug described here:
            # https://github.com/espeak-ng/espeak-ng/issues/694
            # There was a workaround on the phonemizer github, but the sentences
            # were merged and it sounded weird. This is a better workaround.
            phonemes = phonemes.strip().replace("\n", ".").replace("  ", " ")
            phonemes = re.sub(r"_+", "_", phonemes)
            phonemes = re.sub(r"_ ", " ", phonemes)

            return phonemes.splitlines()
        except Exception as e:
            print("Error in phonemization:", str(e))
        finally:
            if self.libc:
                self._close_memstream(phonemes_file)
            else:
                self.msvcrt.fclose(phonemes_file)
                #os.unlink(phonemes_path)


class Synthesizer:
    """Synthesizer, based on the VITS model.

    Trained using the Piper project (https://github.com/rhasspy/piper)

    Attributes:
    -----------
    session: onnxruntime.InferenceSession
        The loaded VITS model.
    id_map: dict
        A dictionary mapping phonemes to ids.

    Methods:
    --------
    __init__(self, model_path, use_cuda):
        Initializes the Synthesizer class, loading the VITS model.

    _initialize_session(self, model_path, use_cuda):
        Initializes the VITS model.

    _phonemes_to_ids(self, phonemes):
        Converts the given phonemes to ids.

    _synthesize_ids_to_raw(self, phoneme_ids, speaker_id, length_scale, noise_scale, noise_w):
        Synthesizes raw audio from phoneme ids.

    say_phonemes(self, phonemes):
        Converts the given phonemes to audio.
    """

    def __init__(self, model_path: str, use_cuda: bool):
        self.session = self._initialize_session(model_path, use_cuda)
        self.id_map = PHONEME_ID_MAP

    def _initialize_session(
        self, model_path: str, use_cuda: bool
    ) -> onnxruntime.InferenceSession:
        providers = ["CPUExecutionProvider"]
        if use_cuda:
            providers = ["CUDAExecutionProvider"]

        return onnxruntime.InferenceSession(
            str(model_path),
            sess_options=onnxruntime.SessionOptions(),
            providers=providers,
        )

    def _phonemes_to_ids(self, phonemes: str) -> List[int]:
        """Phonemes to ids."""

        ids: List[int] = list(self.id_map[BOS])

        for phoneme in phonemes:
            if phoneme not in self.id_map:
                continue

            ids.extend(self.id_map[phoneme])
            ids.extend(self.id_map[PAD])
        ids.extend(self.id_map[EOS])

        return ids

    def _synthesize_ids_to_raw(
        self,
        phoneme_ids: List[int],
        speaker_id: Optional[int] = None,
        length_scale: Optional[float] = 1.0,
        noise_scale: Optional[float] = 0.667,
        noise_w: Optional[float] = 0.8,  # 0.8
    ) -> bytes:
        """Synthesize raw audio from phoneme ids."""

        phoneme_ids_array = np.expand_dims(np.array(phoneme_ids, dtype=np.int64), 0)
        phoneme_ids_lengths = np.array([phoneme_ids_array.shape[1]], dtype=np.int64)

        scales = np.array(
            [noise_scale, length_scale, noise_w],
            dtype=np.float32,
        )

        # Synthesize through Onnx
        audio = self.session.run(
            None,
            {
                "input": phoneme_ids_array,
                "input_lengths": phoneme_ids_lengths,
                "scales": scales,
            },
        )[0].squeeze((0, 1))

        return audio

    def say_phonemes(self, phonemes: str) -> bytes:
        """Say phonemes."""

        phoneme_ids = self._phonemes_to_ids(phonemes)
        audio = self._synthesize_ids_to_raw(phoneme_ids)

        return audio


class TTSEngine:
    def __init__(self, model_path: str = MODEL_PATH, use_cuda: bool = USE_CUDA, espeakng_path: str = ""):
        self.phonemizer = Phonemizer(espeakng_path)
        self.synthesizer = Synthesizer(model_path, use_cuda)

    def generate_speech_audio(self, text: str) -> bytes:
        phonemes = self.phonemizer.synthesize_phonemes(text)
        print("Phonemes: ",phonemes)
        audio = []
        for sentence in phonemes:
            audio_chunk = self.synthesizer.say_phonemes(sentence)
            audio.append(audio_chunk)
        if audio:
            audio = np.concatenate(audio, axis=1).T
        return audio


if __name__ == "__main__":
    tts = TTSEngine(MODEL_PATH, USE_CUDA)
    audio = tts.generate_speech_audio("Hello world. How are you?")
    sd.play(audio, RATE)
    sd.wait()
