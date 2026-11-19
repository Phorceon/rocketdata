"""Talk to OpenRocket through a separate Java helper process.

The helper (java/RocketSim.java) loads an OpenRocket file, reports where every
part ended up and flies it. java/PROTOCOL.md describes the JSON lines the two
sides exchange. This module:

* finds Java and the OpenRocket jar (``find_java``, ``find_jar``),
* compiles the helper once into a cache folder (``compile_helper``),
* runs one helper process with timeouts and restarts (``Simulator``),
* runs several helpers side by side (``SimPool``),
* checks that the whole chain works (``check_setup``).

Failure policy (DESIGN.md section 3). A broken machine raises
``RewardSetupError`` and never becomes a score; every new Simulator flies the
built-in self-test rocket (the canary) and checks the size of OpenRocket's
motor list before it takes designs. Wrong arguments (for example a misspelt
launch field or a negative wind) are a fault of the calling code: they are
checked before anything is sent and raise ``SimRequestError``. Every request
names launch_into_wind, the geodetic model and the wind direction explicitly
(``FIXED_LAUNCH``). A design that OpenRocket cannot read or build comes back
as ``{"ok": false, "error_kind": "load" | "build"}``. A design that hangs or
crashes the helper, a request the helper still refuses as malformed, and a
flight on which OpenRocket threw an error are first taken as machine or
helper trouble: the design is retried once on a fresh helper, after the
canary has shown that the machine still works. If it fails again the result
is ``{"ok": false, "error_kind": "hang" | "crash"}`` (or, for a crashed
flight, the reply with that flight's ``"ok": false``), which the caller scores
as a design fault at the build floor. An aborted flight (``abort`` text) is a
normal flight result with ``"ok": true``.

When the Python process ends, helpers are killed (atexit), and a helper also
exits by itself as soon as its standard input closes, so a killed Python
process leaves no Java process behind.

Importing this module does no work: no files are read and no processes start.
"""
from __future__ import annotations

import atexit
import concurrent.futures
import dataclasses
import hashlib
import itertools
import json
import math
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .errors import RewardSetupError

# ---------------------------------------------------------------------------
# Pinned tools

OPENROCKET_VERSION = "24.12"
# SHA-256 of OpenRocket-24.12.jar as published on the OpenRocket GitHub release
# page (the same value the team's fetch_openrocket.sh checks). Any other file
# would give different flight numbers, so it is refused.
OPENROCKET_JAR_SHA256 = "4959b72f52f5f607941e9722abbb7b7f0c4a38ebbbf84204a329db9f31c4f897"
OPENROCKET_JAR_URL = (
    "https://github.com/openrocket/openrocket/releases/download/release-24.12/OpenRocket-24.12.jar"
)
JAR_NAME = "OpenRocket-24.12.jar"
MIN_JAVA_MAJOR = 17
JDK_DOWNLOAD_HINT = "a JDK 17 (for example Eclipse Temurin 17 from https://adoptium.net)"

ENV_JAVA_HOME = "ROCKET_REWARD_JAVA_HOME"
ENV_JAR = "ROCKET_REWARD_JAR"
ENV_CACHE = "ROCKET_REWARD_CACHE"

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_JAR_PATH = PACKAGE_DIR / "lib" / JAR_NAME
HELPER_SOURCE = PACKAGE_DIR / "java" / "RocketSim.java"
HELPER_CLASS = "RocketSim"
# Bump when the way the helper is compiled changes, so old caches are not reused.
COMPILE_FORMAT = 1

# JVM settings for every helper. A fixed English locale keeps OpenRocket's
# warning texts the same on every machine; the serial collector and a 512 MB heap
# keep many helpers side by side from fighting over cores and memory. Measured on
# 2026-11-19 (calibration/sim_speed.json): a helper peaks at 450-600 MB of memory;
# all 197 reference designs and a 13,600-step fine-time-step flight also ran with a
# 256 MB heap, so 512 MB leaves twice that. Running out of memory is reported by the
# helper as an internal error, which sim.py treats as a crash (retried, then a
# design fault), never as a number.
JVM_ARGS = (
    "-Djava.awt.headless=true",
    "-Dfile.encoding=UTF-8",
    "-Dstdout.encoding=UTF-8",
    "-Dstderr.encoding=UTF-8",
    "-Duser.language=en",
    "-Duser.country=US",
    "-XX:+UseSerialGC",
    "-Xmx512m",
)

# ---------------------------------------------------------------------------
# Wall-clock limits. These guard the machine; they never shape a score. A slow
# design is stopped by max_sim_time_s / max_steps inside the helper, which is
# repeatable; the wall clock only catches a helper that is truly stuck.

BOOT_TIMEOUT_S = 180.0          # start Java, load OpenRocket and its motor list, answer ping
RUN_TIMEOUT_BASE_S = 30.0       # one run: load + placement report ...
RUN_TIMEOUT_PER_FLIGHT_S = 10.0  # ... plus this much per flight
CANARY_TIMEOUT_S = 120.0
QUIT_GRACE_S = 3.0              # time a helper gets to exit after "quit"
POOL_WAIT_STEP_S = 0.5          # a caller waiting for a free helper checks this often whether the pool closed
DEFAULT_MAX_SIM_TIME_S = 1200.0
DEFAULT_MAX_STEPS = 400000

# Error kinds in a run reply.
DESIGN_FAULT_KINDS = ("load", "build")
REQUEST = "request"  # the helper could not read the request (sim.py checks arguments first)
HANG = "hang"
CRASH = "crash"
FLIGHT_CRASH = "flight_crash"  # internal label: a flight with error_kind "crash" in an ok reply

# OpenRocket 24.12's built-in motor list holds 1,452 entries (1,389 distinct thrust
# curves; some curves are listed under two or three names). A helper that
# reports far fewer lost its motor list, and every design would then look like a
# "no motor" build fault, so such a helper is refused at start-up.
MIN_MOTOR_DATABASE_SIZE = 1000

# Fields a run request's "launch" object may hold (PROTOCOL.md).
LAUNCH_NUMBER_FIELDS = frozenset({
    "altitude_m", "latitude_deg", "longitude_deg", "rod_angle_deg", "rod_direction_deg",
    "wind_turbulence", "time_step_s", "wind_direction_deg", "base_temperature_k", "base_pressure_pa"})
GEODETIC_MODELS = ("spherical", "flat", "wgs84")
LAUNCH_FIELDS = LAUNCH_NUMBER_FIELDS | {"launch_into_wind", "geodetic"}

# Launch settings every request carries unless the caller gives its own (owner's
# decision, 2026-11-19): nothing about the launch may come from a default or a
# saved preference inside OpenRocket. These equal the helper's own defaults, so
# the canary's stored numbers are unchanged.
FIXED_LAUNCH = {"launch_into_wind": False, "geodetic": "spherical", "wind_direction_deg": 90.0}

# Temporary .ork files older than this, left by a process that was killed, are
# removed when a Simulator starts.
STALE_TEMP_S = 3600.0
TEMP_PREFIX = "rocket_reward_"


class SimRequestError(RewardSetupError, ValueError):
    """The calling code asked the simulator for something it cannot do.

    For example a negative wind or a misspelt launch field. This is a fault of
    the code or configuration that called sim.py, never of the design being
    scored, so it is raised (it is both a RewardSetupError and a ValueError)
    and never turned into a score.
    """


# ---------------------------------------------------------------------------
# Java and the jar

@dataclasses.dataclass(frozen=True)
class JavaTools:
    """Where java and javac are, and which version they are."""

    java: Path
    javac: Path
    version: str
    major: int
    source: str  # which setting found it: ROCKET_REWARD_JAVA_HOME, JAVA_HOME or PATH


def _exe(bin_dir: Path, name: str) -> Path | None:
    for candidate in (bin_dir / (name + ".exe"), bin_dir / name):
        if candidate.is_file():
            return candidate
    return None


def _java_version(java: Path) -> tuple[str, int]:
    try:
        proc = subprocess.run([str(java), "-version"], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RewardSetupError(
            f"Java at {java} could not be run ({exc}). Install {JDK_DOWNLOAD_HINT} and set "
            f"{ENV_JAVA_HOME} to its folder (the one that holds bin)."
        ) from exc
    text = (proc.stderr + proc.stdout).decode("utf-8", "replace")
    parsed = parse_java_version(text)
    if proc.returncode != 0 or parsed is None:
        raise RewardSetupError(
            f"Java at {java} did not report its version (exit code {proc.returncode}): "
            f"{text.strip()[:300]!r}. Set {ENV_JAVA_HOME} to a working {JDK_DOWNLOAD_HINT}."
        )
    return parsed


def parse_java_version(text: str) -> tuple[str, int] | None:
    """(version, major) from the output of ``java -version``, or None.

    '17.0.21' -> 17, '21' -> 21, '1.8.0_402' -> 8.
    """
    match = re.search(r'version "([^"]+)"', text)
    if not match:
        return None
    version = match.group(1)
    parts = re.findall(r"\d+", version)
    if not parts:
        return None
    major = int(parts[0])
    if major == 1 and len(parts) > 1:
        major = int(parts[1])
    return version, major


def find_java() -> JavaTools:
    """Find java and javac, version 17 or newer.

    Looks at ROCKET_REWARD_JAVA_HOME, then JAVA_HOME, then the PATH. A folder
    named in ROCKET_REWARD_JAVA_HOME must be right: it is never skipped
    silently. Raises RewardSetupError saying what to set when nothing works.
    """
    tried: list[str] = []
    found: tuple[Path, Path | None, str] | None = None
    own = os.environ.get(ENV_JAVA_HOME, "").strip()
    if own:
        bin_dir = Path(own) / "bin"
        java = _exe(bin_dir, "java")
        if java is None:
            folder = Path(own)
            if folder.name.lower() == "bin" and _exe(folder, "java") is not None:
                hint = f"That is the bin folder itself: set {ENV_JAVA_HOME} to {folder.parent} instead."
            else:
                hint = ("Point it at the JDK folder that contains bin (for example a jdk-17... folder "
                        "under Program Files\\Eclipse Adoptium on Windows, or /usr/lib/jvm/java-17-openjdk-amd64 "
                        "on Linux), or unset it.")
            raise RewardSetupError(f"{ENV_JAVA_HOME} is set to {own}, but there is no bin/java there. {hint}")
        found = (java, _exe(bin_dir, "javac"), ENV_JAVA_HOME)
    if found is None:
        home = os.environ.get("JAVA_HOME", "").strip()
        if home:
            java = _exe(Path(home) / "bin", "java")
            if java is not None:
                found = (java, _exe(Path(home) / "bin", "javac"), "JAVA_HOME")
            else:
                tried.append(f"JAVA_HOME={home} has no bin/java")
    if found is None:
        on_path = shutil.which("java")
        if on_path:
            java = Path(on_path)
            javac_path = shutil.which("javac")
            found = (java, Path(javac_path) if javac_path else None, "PATH")
        else:
            tried.append("no java on PATH")
    if found is None:
        raise RewardSetupError(
            f"Java was not found ({'; '.join(tried)}). Install {JDK_DOWNLOAD_HINT} and set "
            f"{ENV_JAVA_HOME} to its folder (the one that holds bin), or put java and javac on PATH."
        )
    java, javac, source = found
    version, major = _java_version(java)
    if major < MIN_JAVA_MAJOR:
        raise RewardSetupError(
            f"Java at {java} (found through {source}) is version {version}; the reward needs "
            f"{MIN_JAVA_MAJOR} or newer. Install {JDK_DOWNLOAD_HINT} and set {ENV_JAVA_HOME} to its folder."
        )
    if javac is None:
        raise RewardSetupError(
            f"Found java at {java} (through {source}) but no javac next to it: that is a Java "
            f"runtime, not a development kit, and the helper must be compiled. Install "
            f"{JDK_DOWNLOAD_HINT} and set {ENV_JAVA_HOME} to its folder."
        )
    return JavaTools(java=java, javac=javac, version=version, major=major, source=source)


_HASH_CACHE: dict[tuple[str, int, int], str] = {}
_HASH_LOCK = threading.Lock()


def file_sha256(path: Path) -> str:
    """SHA-256 of a file, remembered while the file's size and time stay the same."""
    st = path.stat()
    key = (str(path.resolve()), st.st_size, st.st_mtime_ns)
    with _HASH_LOCK:
        if key in _HASH_CACHE:
            return _HASH_CACHE[key]
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    value = digest.hexdigest()
    with _HASH_LOCK:
        _HASH_CACHE[key] = value
    return value


def find_jar() -> Path:
    """Find the OpenRocket 24.12 jar and check it is exactly the pinned file.

    Looks at ROCKET_REWARD_JAR, then rocket_reward/lib/OpenRocket-24.12.jar.
    Raises RewardSetupError with download instructions when it is missing or
    is a different file.
    """
    own = os.environ.get(ENV_JAR, "").strip()
    path = Path(own) if own else DEFAULT_JAR_PATH
    where = f"{ENV_JAR}={own}" if own else "the default place"
    if not path.is_file():
        fix = (f"Correct {ENV_JAR}, or unset it and run `python -m rocket_reward fetch-jar`, which downloads "
               f"{OPENROCKET_JAR_URL} into {DEFAULT_JAR_PATH} and checks it." if own else
               f"Run `python -m rocket_reward fetch-jar` (it downloads the pinned file there and checks it), "
               f"or download {OPENROCKET_JAR_URL} yourself and save it there, or set {ENV_JAR} "
               f"to the full path of a jar you already have.")
        raise RewardSetupError(
            f"The OpenRocket {OPENROCKET_VERSION} jar was not found at {path} ({where}). {fix}"
        )
    actual = file_sha256(path)
    if actual != OPENROCKET_JAR_SHA256:
        raise RewardSetupError(
            f"The file at {path} is not the OpenRocket {OPENROCKET_VERSION} jar: its SHA-256 is "
            f"{actual}, expected {OPENROCKET_JAR_SHA256}. Get it again with `python -m rocket_reward fetch-jar` "
            f"or from {OPENROCKET_JAR_URL} (a partial download or another version gives this error)."
        )
    return path


# ---------------------------------------------------------------------------
# Compiling the helper

def cache_root() -> Path:
    """Folder for compiled helpers and helper logs.

    ROCKET_REWARD_CACHE when set, else the user's cache folder
    (%LOCALAPPDATA% on Windows, ~/Library/Caches on macOS, $XDG_CACHE_HOME or
    ~/.cache elsewhere), else the temp folder.
    """
    own = os.environ.get(ENV_CACHE, "").strip()
    if own:
        return Path(own)
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", "").strip()
        if base:
            return Path(base) / "rocket_reward" / "cache"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "rocket_reward"
    else:
        base = os.environ.get("XDG_CACHE_HOME", "").strip()
        if base:
            return Path(base) / "rocket_reward"
        if Path.home().is_dir():
            return Path.home() / ".cache" / "rocket_reward"
    return Path(tempfile.gettempdir()) / "rocket_reward-cache"


def java_arg_path(path: Path, what: str, setting: str, encoding: str | None = None) -> str:
    """``path`` as text that is safe to put on a java or javac command line.

    On Windows the Java launcher reads its command line in the system's ANSI
    code page, so a folder name with characters outside it (for example a
    Japanese user name in %LOCALAPPDATA%) reaches Java as "?" and breaks. Such
    a path is replaced by its short 8.3 name when Windows has one; otherwise a
    RewardSetupError says which ``setting`` to point at an ASCII-only folder.
    On other systems, and for paths the code page can hold, the path is
    returned as it is. ``encoding`` replaces the code page (for tests).
    """
    text = str(path)
    if sys.platform != "win32" and encoding is None:
        return text
    codec = encoding or "mbcs"
    try:
        text.encode(codec, "strict")
        return text
    except UnicodeEncodeError:
        pass
    short = _short_path(text)
    if short:
        try:
            short.encode(codec, "strict")
            return short
        except UnicodeEncodeError:
            pass
    raise RewardSetupError(
        f"The {what} {text} has characters that Java cannot read on this Windows system (it reads "
        f"command lines in the system code page). Set {setting} to a folder whose path uses only "
        f"plain ASCII letters, digits and punctuation, for example /srv/rocket_reward."
    )


def _short_path(text: str) -> str | None:
    """The Windows 8.3 short name of an existing path, or None."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        get = ctypes.windll.kernel32.GetShortPathNameW
        get.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        get.restype = wintypes.DWORD
        size = get(text, None, 0)
        if not size:
            return None
        buf = ctypes.create_unicode_buffer(size)
        if not get(text, buf, size):
            return None
        return buf.value or None
    except (OSError, AttributeError, ImportError):
        return None


def _main_class(source_text: str) -> str:
    match = re.search(r"^\s*package\s+([\w.]+)\s*;", source_text, re.M)
    return f"{match.group(1)}.{HELPER_CLASS}" if match else HELPER_CLASS


def compile_helper(java: JavaTools | None = None, jar: Path | None = None,
                   source: Path | None = None) -> tuple[Path, str]:
    """Compile the helper once and return (classes folder, main class name).

    The folder name is a hash of the helper source, the jar and the Java major
    version, so a changed source compiles again and an unchanged one never
    does. Several processes may call this at the same moment: each compiles
    into its own scratch folder and the first to rename it into place wins.
    """
    java = java or find_java()
    jar = jar or find_jar()
    source = Path(source) if source else HELPER_SOURCE
    if not source.is_file():
        raise RewardSetupError(
            f"The helper source {source} is missing. Reinstall the rocket_reward package; the "
            f"java folder must contain {HELPER_CLASS}.java."
        )
    data = source.read_bytes()
    main_class = _main_class(data.decode("utf-8", "replace"))
    key = hashlib.sha256()
    for part in (data, file_sha256(jar).encode(), str(java.major).encode(), str(COMPILE_FORMAT).encode()):
        key.update(part)
        key.update(b"\0")
    root = cache_root()
    final = root / f"helper-{key.hexdigest()[:20]}"
    stamp = final / "COMPILED"
    if stamp.is_file():
        return final, main_class
    try:
        root.mkdir(parents=True, exist_ok=True)
        scratch = Path(tempfile.mkdtemp(prefix="compile-", dir=root))
    except OSError as exc:
        raise RewardSetupError(
            f"Cannot write to the cache folder {root} ({exc}). Set {ENV_CACHE} to a folder you can write to."
        ) from exc
    try:
        # The source is copied next to the output so that only the cache folder and the jar
        # appear on javac's command line (both checked for characters Java cannot read).
        (scratch / "classes").mkdir()
        (scratch / "src").mkdir()
        copied = scratch / "src" / source.name
        copied.write_bytes(data)
        cmd = [java_arg_path(java.javac, "javac program", ENV_JAVA_HOME), "--release", str(MIN_JAVA_MAJOR),
               "-nowarn", "-encoding", "UTF-8",
               "-cp", java_arg_path(jar, "OpenRocket jar", ENV_JAR),
               "-d", java_arg_path(scratch / "classes", "cache folder", ENV_CACHE),
               java_arg_path(copied, "cache folder", ENV_CACHE)]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=600)
        except (OSError, subprocess.SubprocessError) as exc:
            raise RewardSetupError(f"javac at {java.javac} could not be run ({exc}). Check {ENV_JAVA_HOME}.") from exc
        if proc.returncode != 0:
            err = (proc.stderr + proc.stdout).decode("utf-8", "replace").strip()
            if "InvalidPathException" in err or "illegal argument for -d" in err:
                hint = (f"Java could not use one of the folders on its command line (cache {root}, jar {jar}). "
                        f"Set {ENV_CACHE} and {ENV_JAR} to paths that use only plain ASCII characters.")
            else:
                hint = (f"Check that {ENV_JAR} points at the OpenRocket {OPENROCKET_VERSION} jar and that "
                        f"{source} is the helper shipped with this package.")
            raise RewardSetupError(
                f"The helper {source.name} did not compile with {java.javac} (Java {java.version}):\n"
                f"{err[-2000:]}\n{hint}"
            )
        (scratch / "classes" / "COMPILED").write_text(
            f"{source.name} {main_class}\n", encoding="utf-8", newline="\n")
        try:
            os.replace(scratch / "classes", final)
        except OSError:
            if not stamp.is_file():  # nobody else finished either: a real problem
                raise RewardSetupError(
                    f"Could not move the compiled helper into {final}. Delete that folder and try "
                    f"again, or set {ENV_CACHE} to another folder."
                )
        return final, main_class
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def helper_command(java: JavaTools | None = None, jar: Path | None = None,
                   source: Path | None = None) -> list[str]:
    """The command line that starts the real helper (compiling it if needed)."""
    java = java or find_java()
    jar = jar or find_jar()
    classes, main_class = compile_helper(java, jar, source)
    class_path = os.pathsep.join([java_arg_path(jar, "OpenRocket jar", ENV_JAR),
                                  java_arg_path(classes, "cache folder", ENV_CACHE)])
    return [java_arg_path(java.java, "java program", ENV_JAVA_HOME), *JVM_ARGS, "-cp", class_path, main_class]


# ---------------------------------------------------------------------------
# The self-test rocket

@dataclasses.dataclass(frozen=True)
class Canary:
    """A rocket whose flight numbers are known, flown to prove the machine works.

    ``expected`` maps flight fields (as in PROTOCOL.md) to values; each must be
    within ``rel_tol`` of the value from the first flight of the reply.
    ``expected_rocket`` maps fields of the reply's "rocket" block to values that
    must match exactly (for example motor_count 1: the motor was found).
    """

    name: str
    ork_text: str
    rail_m: float
    flights: tuple[Mapping[str, Any], ...]
    expected: Mapping[str, float]
    rel_tol: float = 0.01
    launch: Mapping[str, Any] | None = None
    expected_rocket: Mapping[str, Any] = dataclasses.field(default_factory=dict)

    def problems(self, reply: Mapping[str, Any]) -> list[str]:
        """Why this reply is not the expected flight (empty when it is)."""
        if not reply.get("ok"):
            return [f"the self-test rocket did not fly: {reply.get('error_kind')}: {reply.get('message')}"]
        flights = reply.get("flights") or []
        if not flights or not flights[0].get("ok"):
            return ["the self-test rocket gave no flight"]
        first, out = flights[0], []
        rocket = reply.get("rocket") or {}
        for key, want in self.expected_rocket.items():
            if rocket.get(key) != want:
                out.append(f"rocket {key} is {rocket.get(key)!r}, expected {want!r}")
        for key, want in self.expected.items():
            got = first.get(key)
            if not isinstance(got, (int, float)) or isinstance(got, bool) or not math.isfinite(got):
                out.append(f"{key} is missing (expected {want})")
            elif abs(got - want) > self.rel_tol * abs(want):
                out.append(f"{key} is {got:.4g}, expected {want:.4g} within {self.rel_tol:.0%}")
        return out


CANARY_JSON = PACKAGE_DIR / "data" / "canary.json"
_CANARY_CACHE: dict[str, Canary] = {}
_CANARY_LOCK = threading.Lock()


def load_canary(path: str | os.PathLike | None = None) -> Canary:
    """Read the self-test rocket from data/canary.json and the .ork file it names.

    The JSON holds the flight request (rail, flights, launch), the expected
    numbers and the tolerance; see data/canary.json for where they came from.
    Read once per process. A missing or broken file is a broken install and
    raises RewardSetupError.
    """
    path = Path(path) if path is not None else CANARY_JSON
    key = str(path)
    with _CANARY_LOCK:
        if key in _CANARY_CACHE:
            return _CANARY_CACHE[key]
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
            ork_text = (path.parent / spec["ork_file"]).read_text(encoding="utf-8")
            canary = Canary(
                name=str(spec["name"]), ork_text=ork_text, rail_m=float(spec["rail_m"]),
                flights=tuple(dict(f) for f in spec["flights"]),
                expected={k: float(v) for k, v in spec["expected"].items()},
                rel_tol=float(spec["rel_tol"]), launch=spec.get("launch"),
                expected_rocket=dict(spec.get("expected_rocket") or {}))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise RewardSetupError(
                f"The self-test rocket could not be read from {path} ({type(exc).__name__}: {exc}). "
                f"Reinstall the rocket_reward package: its data folder must hold canary.json and canary.ork."
            ) from exc
        _CANARY_CACHE[key] = canary
        return canary


class _DefaultCanary:
    """Marker for "use data/canary.json" in Simulator and check_setup."""

    def __repr__(self) -> str:
        return "the packaged self-test rocket"


DEFAULT = _DefaultCanary()


def __getattr__(name: str) -> Any:
    # sim.DEFAULT_CANARY is read lazily so that importing this module reads no file.
    if name == "DEFAULT_CANARY":
        return load_canary()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ---------------------------------------------------------------------------
# One helper process

_LIVE: set[subprocess.Popen] = set()
_LIVE_LOCK = threading.Lock()
_SIM_COUNTER = itertools.count(1)
_ATEXIT_REGISTERED = False


def live_processes() -> list[subprocess.Popen]:
    """Helper processes started by this module that have not been stopped yet."""
    with _LIVE_LOCK:
        return [p for p in _LIVE if p.poll() is None]


def _kill_live_processes() -> None:
    """Kill every helper still running (registered with atexit when the first helper starts).

    A helper also exits by itself as soon as its standard input closes, which
    covers a Python process that is killed without running atexit.
    """
    for p in live_processes():
        try:
            p.kill()
            p.wait(10)
        except (OSError, subprocess.SubprocessError):
            pass


def _register_atexit() -> None:
    global _ATEXIT_REGISTERED
    with _LIVE_LOCK:
        if _ATEXIT_REGISTERED:
            return
        _ATEXIT_REGISTERED = True
    atexit.register(_kill_live_processes)


def _sweep_stale_temp_files(folder: Path, older_than_s: float = STALE_TEMP_S) -> int:
    """Remove rocket_reward_*.ork files in ``folder`` older than ``older_than_s``.

    Such files are left only when a process was killed while flying a design.
    Files of designs being flown right now are young and are kept. Returns the
    number removed.
    """
    removed = 0
    cutoff = time.time() - older_than_s
    try:
        candidates = list(folder.glob(TEMP_PREFIX + "*.ork"))
    except OSError:
        return 0
    for path in candidates:
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            pass
    return removed


class _Fault(Exception):
    """The helper hung, died or broke the protocol during one request."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind
        self.message = message


class _Process:
    """One running helper: the Popen, a reader thread and its reply queue."""

    def __init__(self, command: Sequence[str], log_fh, env: Mapping[str, str] | None, cwd: str | None):
        self.lines: queue.Queue = queue.Queue()
        kwargs: dict[str, Any] = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        _register_atexit()
        self.popen = subprocess.Popen(
            list(command), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log_fh,
            env=dict(env) if env is not None else None, cwd=cwd, **kwargs)
        with _LIVE_LOCK:
            _LIVE.add(self.popen)
        self.reader = threading.Thread(target=self._read, name="rocket-sim-reader", daemon=True)
        self.reader.start()

    def _read(self) -> None:
        stream = self.popen.stdout
        try:
            for raw in iter(stream.readline, b""):
                self.lines.put(raw.decode("utf-8", "replace").rstrip("\r\n"))
        except (OSError, ValueError):
            pass
        finally:
            self.lines.put(None)  # end of output: the process exited

    def send(self, obj: Mapping[str, Any]) -> None:
        data = (json.dumps(obj, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
        self.popen.stdin.write(data)
        self.popen.stdin.flush()

    def stop(self, polite: bool) -> None:
        p = self.popen
        try:
            if polite and p.poll() is None:
                try:
                    self.send({"op": "quit"})
                    p.stdin.close()
                except (OSError, ValueError):
                    pass
                try:
                    p.wait(QUIT_GRACE_S)
                except subprocess.TimeoutExpired:
                    pass
            if p.poll() is None:
                p.kill()
            p.wait(30)
        finally:
            for stream in (p.stdin, p.stdout):
                try:
                    if stream:
                        stream.close()
                except OSError:
                    pass
            self.reader.join(5)
            with _LIVE_LOCK:
                _LIVE.discard(p)


def _no_nan(text: str) -> float:
    raise ValueError(f"{text} is not allowed in a reply (the protocol uses null)")


class Simulator:
    """One OpenRocket helper process with timeouts, restarts and a self-test.

    ``command`` is the program to run (default: the real Java helper, compiled
    on first use). Tests pass a fake helper here. The process starts and is
    pinged in the constructor, and with ``self_test`` (the default) the
    self-test rocket flies once, so a machine that cannot fly rockets raises
    RewardSetupError here rather than scoring designs as faults. ``close()``
    (or leaving a ``with`` block) always stops it, also in the middle of a
    request. Standard error of the helper is appended to ``self.log_path``.
    """

    def __init__(self, command: Sequence[str] | None = None, *, canary: Canary | _DefaultCanary | None = DEFAULT,
                 log_path: str | os.PathLike | None = None, boot_timeout_s: float = BOOT_TIMEOUT_S,
                 env: Mapping[str, str] | None = None, cwd: str | os.PathLike | None = None,
                 self_test: bool = True):
        self.command = list(command) if command is not None else helper_command()
        self.canary = load_canary() if isinstance(canary, _DefaultCanary) else canary
        self.boot_timeout_s = boot_timeout_s
        self.env = env
        self.cwd = str(cwd) if cwd is not None else None
        number = next(_SIM_COUNTER)
        if log_path is None:
            log_dir = cache_root() / "logs"
            log_path = log_dir / f"helper-{os.getpid()}-{number}.log"
        self.log_path = Path(log_path)
        self.stats = {"starts": 0, "restarts": 0, "hangs": 0, "crashes": 0, "refused": 0,
                      "flight_crashes": 0, "canary_runs": 0, "runs": 0}
        self.ping_reply: dict[str, Any] = {}
        self._ids = itertools.count(1)
        self._lock = threading.Lock()
        self._proc: _Process | None = None
        self._closed = False
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self._log = open(self.log_path, "ab")
        except OSError as exc:
            raise RewardSetupError(
                f"Cannot write the helper log {self.log_path} ({exc}). Set {ENV_CACHE} to a folder you can write to."
            ) from exc
        swept = _sweep_stale_temp_files(Path(tempfile.gettempdir()))
        if swept:
            self._note(f"removed {swept} old temporary .ork file(s) left by a killed process")
        try:
            self._start()
            if self_test and self.canary is not None:
                with self._lock:
                    self._fly_canary()
        except BaseException:
            self.close()
            raise

    # -- lifecycle ---------------------------------------------------------

    def __enter__(self) -> "Simulator":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        """Stop the helper and close the log.

        A request that is running in another thread is cut short: its helper
        is killed at once and that ``run()`` raises RuntimeError instead of
        retrying. With no request running the helper is asked to quit first.
        """
        self._closed = True
        busy = not self._lock.acquire(blocking=False)
        if busy:
            proc = self._proc
            if proc is not None:
                try:
                    proc.popen.kill()
                except OSError:
                    pass
            self._lock.acquire()
        try:
            self._stop(polite=not busy)
            if not self._log.closed:
                self._log.close()
        finally:
            self._lock.release()

    @property
    def pid(self) -> int | None:
        """Process id of the running helper, or None."""
        return self._proc.popen.pid if self._proc else None

    def _note(self, text: str) -> None:
        if not self._log.closed:
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            self._log.write(f"--- [rocket_reward {stamp}] {text}\n".encode("utf-8", "replace"))
            self._log.flush()

    def _log_tail(self, lines: int = 15) -> str:
        try:
            self._log.flush()
            text = self.log_path.read_bytes()[-4000:].decode("utf-8", "replace")
        except OSError:
            return ""
        tail = [line for line in text.splitlines() if line.strip()][-lines:]
        return "\n".join(tail)

    def _setup_error(self, what: str) -> RewardSetupError:
        tail = self._log_tail()
        msg = (f"{what}\nCommand: {' '.join(self.command)}\nHelper log: {self.log_path}"
               + (f"\nLast lines of the log:\n{tail}" if tail else ""))
        return RewardSetupError(msg)

    def _stop(self, polite: bool) -> None:
        if self._proc is not None:
            proc, self._proc = self._proc, None
            proc.stop(polite)
            self._note(f"helper stopped (exit code {proc.popen.returncode})")

    def _start(self) -> None:
        if self._closed:
            raise RuntimeError("this Simulator is closed")
        self._note("starting helper: " + " ".join(self.command))
        try:
            self._proc = _Process(self.command, self._log, self.env, self.cwd)
        except OSError as exc:
            raise self._setup_error(
                f"The simulator helper could not start ({exc}). Check {ENV_JAVA_HOME} and {ENV_JAR}, "
                f"or run rocket_reward's check_setup() for details."
            ) from exc
        self.stats["starts"] += 1
        rid = f"p{next(self._ids)}"
        try:
            reply = self._request({"op": "ping", "id": rid}, rid, self.boot_timeout_s)
        except _Fault as fault:
            self._stop(polite=False)
            if fault.kind == HANG:
                what = f"The simulator helper did not answer ping within {self.boot_timeout_s:.0f} s."
            elif fault.kind == "exit":
                what = "The simulator helper exited before its first reply."
            else:
                what = f"The simulator helper's first reply is not valid protocol: {fault.message}"
            raise self._setup_error(what + " Java or the OpenRocket jar is probably broken.") from None
        if not reply.get("ok") or str(reply.get("openrocket")) != OPENROCKET_VERSION:
            self._stop(polite=False)
            raise self._setup_error(
                f"The simulator helper answered ping with {json.dumps(reply)[:300]}; expected ok and "
                f"OpenRocket {OPENROCKET_VERSION}. Set {ENV_JAR} to the OpenRocket {OPENROCKET_VERSION} jar."
            )
        motors = reply.get("motor_database_size")
        if not isinstance(motors, int) or isinstance(motors, bool) or motors < MIN_MOTOR_DATABASE_SIZE:
            self._stop(polite=False)
            raise self._setup_error(
                f"The simulator helper reports {motors!r} motors in OpenRocket's motor list; OpenRocket "
                f"{OPENROCKET_VERSION} lists 1,452 motors and at least {MIN_MOTOR_DATABASE_SIZE} are needed. "
                f"Every design would fly without its motor. Check that {ENV_JAR} is the unchanged "
                f"OpenRocket {OPENROCKET_VERSION} jar and that the helper log shows no motor-loading errors."
            )
        self.ping_reply = reply
        self._note(f"helper ready: {json.dumps(reply)}")

    def _restart(self) -> None:
        self._stop(polite=False)
        self.stats["restarts"] += 1
        self._start()

    # -- one request ---------------------------------------------------------

    def _request(self, obj: Mapping[str, Any], rid: str, timeout_s: float) -> dict[str, Any]:
        """Send one request and wait for its reply. Raises _Fault on any trouble."""
        proc = self._proc
        if proc is None or proc.popen.poll() is not None:
            raise _Fault("exit", "the helper is not running")
        try:
            proc.send(obj)
        except (OSError, ValueError) as exc:
            raise _Fault("exit", f"the helper stopped taking input ({exc})") from None
        deadline = time.monotonic() + timeout_s
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise _Fault(HANG, f"no reply within {timeout_s:.0f} s")
            try:
                line = proc.lines.get(timeout=remaining)
            except queue.Empty:
                continue
            if line is None:
                try:
                    code = proc.popen.wait(5)
                except subprocess.TimeoutExpired:
                    code = None
                raise _Fault("exit", f"the helper exited during the request (exit code {code})")
            if not line.strip():
                continue
            try:
                reply = json.loads(line, parse_constant=_no_nan)
            except ValueError:
                raise _Fault("protocol", f"not a JSON line: {line[:200]!r}") from None
            if not isinstance(reply, dict) or reply.get("id") != rid or not isinstance(reply.get("ok"), bool):
                raise _Fault("protocol", f"reply does not match request {rid}: {line[:200]!r}")
            return reply

    def _check_run_reply(self, reply: dict[str, Any], n_flights: int) -> None:
        if reply["ok"]:
            flights = reply.get("flights")
            if not isinstance(flights, list) or len(flights) != n_flights:
                raise _Fault("protocol", f"expected {n_flights} flights in the reply, got {flights!r:.200}")
            return
        kind = reply.get("error_kind")
        if kind in DESIGN_FAULT_KINDS or kind == REQUEST:  # REQUEST: judged by run() (_suspect)
            return
        if kind == "internal":
            raise _Fault("internal", f"the helper reported an internal error: {reply.get('message')}")
        raise _Fault("protocol", f"unknown error_kind {kind!r}")

    def _attempt(self, path: Path, rail_m: float, flights: list, launch, max_sim_time_s: float,
                 max_steps: int, timeout_s: float, config_id: str | None = None,
                 allow_motor_substitution: bool = False) -> dict[str, Any]:
        if self._proc is None or self._proc.popen.poll() is not None:
            self._note("helper was not running before a request; restarting it")
            self._restart()
        rid = f"r{next(self._ids)}"
        req: dict[str, Any] = {"op": "run", "id": rid, "ork": str(path), "rail_m": rail_m,
                               "flights": flights, "max_sim_time_s": max_sim_time_s, "max_steps": max_steps}
        if launch is not None:
            req["launch"] = dict(launch)
        if config_id is not None:
            req["config_id"] = config_id
        if allow_motor_substitution:
            req["allow_motor_substitution"] = True
        reply = self._request(req, rid, timeout_s)
        self._check_run_reply(reply, len(flights))
        return reply

    def _fly(self, ork: str | bytes | os.PathLike, rail_m: float, flights: list, launch,
             max_sim_time_s: float, max_steps: int, timeout_s: float,
             config_id: str | None = None, allow_motor_substitution: bool = False) -> dict[str, Any]:
        """One attempt with a temporary .ork when given text. Raises _Fault.

        When the attempt fails, the helper is stopped before the temporary file
        is deleted: a stuck helper may still hold the file open, and Windows
        cannot delete an open file.
        """
        args = (rail_m, flights, launch, max_sim_time_s, max_steps, timeout_s, config_id, allow_motor_substitution)
        if isinstance(ork, (str, bytes)) and not _looks_like_path(ork):
            fd, name = tempfile.mkstemp(prefix=TEMP_PREFIX, suffix=".ork")
            path = Path(name)
            try:
                with os.fdopen(fd, "wb") as fh:
                    fh.write(ork.encode("utf-8") if isinstance(ork, str) else ork)
                try:
                    return self._attempt(path, *args)
                except _Fault:
                    self._stop(polite=False)
                    raise
            finally:
                _remove(path)
        path = Path(os.fsdecode(ork))
        if not path.is_file():
            raise FileNotFoundError(f"no .ork file at {path}")
        return self._attempt(path.resolve(), *args)

    def _fly_canary(self) -> dict[str, Any]:
        c = self.canary
        assert c is not None
        self.stats["canary_runs"] += 1
        started = time.monotonic()
        try:
            reply = self._fly(c.ork_text, c.rail_m, [dict(f) for f in c.flights], _checked_launch(c.launch),
                              DEFAULT_MAX_SIM_TIME_S, DEFAULT_MAX_STEPS, CANARY_TIMEOUT_S)
        except _Fault as fault:
            self._stop(polite=False)
            if self._closed:
                raise RuntimeError("this Simulator was closed during its self-test") from None
            raise self._setup_error(
                f"The self-test rocket '{c.name}' failed ({fault.kind}: {fault.message}). The machine "
                f"cannot fly rockets correctly, so no answer can be scored."
            ) from None
        problems = c.problems(reply)
        if problems:
            self._stop(polite=False)
            raise self._setup_error(
                f"The self-test rocket '{c.name}' gave wrong numbers: {'; '.join(problems)}. Check that "
                f"{ENV_JAR} is the OpenRocket {OPENROCKET_VERSION} jar and the helper is unchanged."
            )
        self._note(f"self-test rocket passed in {time.monotonic() - started:.2f} s")
        return reply

    # -- public --------------------------------------------------------------

    def fly_canary(self) -> dict[str, Any]:
        """Fly the self-test rocket. Returns the reply or raises RewardSetupError."""
        if self.canary is None:
            raise ValueError("this Simulator has no self-test rocket")
        with self._lock:
            if self._proc is None or self._proc.popen.poll() is not None:
                self._restart()
            return self._fly_canary()

    def motor_list(self, timeout_s: float = 60.0) -> list[dict[str, Any]]:
        """Every motor in OpenRocket's built-in motor list (PROTOCOL.md, op "motors").

        Each entry has digest, manufacturer, designation, common_name,
        diameter_m, length_m and total_impulse_ns. A motor whose thrust-curve
        digest is not in this list cannot fly as written: the helper reports
        such a design as a build fault.
        """
        with self._lock:
            if self._closed:
                raise RuntimeError("this Simulator is closed")
            if self._proc is None or self._proc.popen.poll() is not None:
                self._restart()
            rid = f"m{next(self._ids)}"
            try:
                reply = self._request({"op": "motors", "id": rid}, rid, timeout_s)
            except _Fault as fault:
                self._stop(polite=False)
                raise self._setup_error(f"The helper did not list its motors ({fault.kind}: {fault.message}).") from None
            motors = reply.get("motors")
            if not reply.get("ok") or not isinstance(motors, list):
                raise self._setup_error(f"The helper did not list its motors: {json.dumps(reply)[:300]}")
            return motors

    def run(self, ork_text_or_path: str | bytes | os.PathLike, rail_m: float,
            flights: Sequence[Mapping[str, Any]], launch: Mapping[str, Any] | None = None,
            max_sim_time_s: float = DEFAULT_MAX_SIM_TIME_S, max_steps: int = DEFAULT_MAX_STEPS,
            timeout_s: float | None = None, config_id: str | None = None,
            allow_motor_substitution: bool = False) -> dict[str, Any]:
        """Load one design, report its parts and fly it once per entry in ``flights``.

        ``ork_text_or_path`` is .ork XML text (str starting with "<"), .ork
        bytes (plain or zipped), or a path to an .ork file. Text is written to a
        temporary file that is always deleted afterwards. ``config_id`` flies one
        flight configuration by its id (default: the file's selected one).
        ``allow_motor_substitution`` is for parity checks only: it lets a motor
        that OpenRocket replaced by another of the same name fly (the reward
        never sets it; then such a design is a build fault).

        Returns the helper's reply (PROTOCOL.md). A design fault is
        ``{"ok": False, "error_kind": "load" | "build" | "hang" | "crash", "message": ...}``.
        A single flight can also fail (``"ok": false`` with ``error_kind`` and
        ``error`` in that flight); the caller gives such a design the build floor.

        Hangs, helper crashes, a request the helper refuses as malformed and a
        flight on which OpenRocket threw an error (flight ``error_kind``
        "crash") are first taken to be machine or helper trouble: the helper is
        restarted, the self-test rocket must fly, and the design is tried once
        more. Only when it fails again does it count as the design's fault: a
        second hang gives "hang", a second helper crash or refusal "crash", and
        a second crashed flight is returned as it is (that flight has ok false).

        Raises RewardSetupError when the machine is broken, SimRequestError
        (a RewardSetupError and a ValueError) when the arguments are wrong (they
        are checked before anything is sent), and RuntimeError when the
        Simulator is closed, also by close() from another thread while this
        request runs.
        """
        flights = _checked_flights(flights)
        if not (_is_number(rail_m) and rail_m > 0):
            raise SimRequestError(f"rail_m must be a positive number, got {rail_m!r}")
        launch = _checked_launch(launch)
        _check_run_limits(max_sim_time_s, max_steps, config_id)
        if isinstance(max_steps, float):
            max_steps = int(max_steps)
        if timeout_s is None:
            timeout_s = RUN_TIMEOUT_BASE_S + RUN_TIMEOUT_PER_FLIGHT_S * len(flights)
        args = (rail_m, flights, launch, max_sim_time_s, max_steps, timeout_s, config_id,
                bool(allow_motor_substitution))
        with self._lock:
            if self._closed:
                raise RuntimeError("this Simulator is closed")
            self.stats["runs"] += 1
            try:
                reply = self._fly(ork_text_or_path, *args)
                trouble = _suspect(reply)
                if trouble is None:
                    return reply
                first_kind, first = trouble
                self._count(first_kind)
                self._stop(polite=False)
            except _Fault as fault:
                if self._closed:
                    raise RuntimeError("this Simulator was closed while the design was flying") from None
                first, first_kind = fault.message, _fault_kind(fault)
                self._count(first_kind)
            self._note(f"design failed ({first_kind}: {first}); restarting the helper and flying the self-test rocket")
            # Prove the machine works, then retry once on a fresh helper.
            self._restart()
            if self.canary is not None:
                self._fly_canary()
            try:
                reply = self._fly(ork_text_or_path, *args)
            except _Fault as second:
                if self._closed:
                    raise RuntimeError("this Simulator was closed while the design was flying") from None
                kind = _fault_kind(second)
                self._count(kind)
                self._note(f"design failed again ({second.kind}: {second.message}); it counts as a design fault")
                self._stop(polite=False)  # the next run starts a fresh helper
                what = ("OpenRocket did not finish this design in time" if kind == HANG
                        else "OpenRocket crashed on this design")
                return {"ok": False, "error_kind": kind,
                        "message": f"{what} twice ({first}; then {second.message})"}
            trouble = _suspect(reply)
            if trouble is None:
                self._note("the design worked on the second try; the first failure was machine or helper trouble")
                return reply
            kind, second_msg = trouble
            self._count(kind)
            self._note(f"design failed again ({kind}: {second_msg}); it counts as a design fault")
            if kind == REQUEST:
                return {"ok": False, "error_kind": CRASH,
                        "message": f"the simulator helper refused the request for this design twice, also after "
                                   f"the self-test rocket flew ({first}; then {second_msg})"}
            return reply  # a flight crashed again: that flight has ok false and error_kind "crash"

    def _count(self, kind: str) -> None:
        key = {HANG: "hangs", REQUEST: "refused", FLIGHT_CRASH: "flight_crashes"}.get(kind, "crashes")
        self.stats[key] = self.stats.get(key, 0) + 1


def _fault_kind(fault: _Fault) -> str:
    return HANG if fault.kind == HANG else CRASH


def _suspect(reply: Mapping[str, Any]) -> tuple[str, str] | None:
    """(kind, message) when a well-formed reply still points at machine or helper trouble.

    REQUEST: the helper refused the request as malformed. FLIGHT_CRASH: on
    some flight OpenRocket threw an error (flight error_kind "crash"); an
    aborted flight (``abort`` text, ``ok`` true) is a normal result, not this.
    None for every other reply.
    """
    if not reply.get("ok"):
        if reply.get("error_kind") == REQUEST:
            return REQUEST, str(reply.get("message"))
        return None
    for i, f in enumerate(reply.get("flights") or []):
        if isinstance(f, Mapping) and f.get("ok") is False and f.get("error_kind") == CRASH:
            return FLIGHT_CRASH, f"flight {i}: {f.get('error')}"
    return None


def _checked_flights(flights: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The flights as plain dicts, each with a wind of 0 or more and a whole 32-bit seed.

    Raises SimRequestError otherwise: a wrong flight list is a fault of the
    calling code and must never be scored as a fault of the design.
    """
    out = [dict(f) for f in flights]
    if not out:
        raise SimRequestError("flights must hold at least one flight")
    for i, f in enumerate(out):
        wind, seed = f.get("wind_ms"), f.get("seed")
        if not (isinstance(wind, (int, float)) and not isinstance(wind, bool) and math.isfinite(wind) and wind >= 0):
            raise SimRequestError(f"flight {i}: wind_ms must be a number of 0 or more, got {wind!r}")
        if isinstance(seed, float) and seed.is_integer():
            seed = int(seed)
        if not (isinstance(seed, int) and not isinstance(seed, bool) and -2**31 <= seed < 2**31):
            raise SimRequestError(f"flight {i}: seed must be a whole number that fits in 32 bits, got {f.get('seed')!r}")
        f["seed"] = seed
        unknown = set(f) - {"wind_ms", "seed"}
        if unknown:
            raise SimRequestError(f"flight {i}: unknown field(s) {sorted(unknown)}; a flight has wind_ms and seed")
    return out


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _checked_launch(launch: Mapping[str, Any] | None) -> dict[str, Any]:
    """The launch settings to send: the caller's, with FIXED_LAUNCH filling the gaps.

    Raises SimRequestError for anything the helper would refuse (PROTOCOL.md):
    an unknown field, a value that is not a finite number, a time step or
    pressure that is not above 0, a negative turbulence, a geodetic model other
    than spherical, flat or wgs84, a launch_into_wind that is not true/false.
    Checking here keeps the calling code's mistakes from ever reaching the
    helper, where they could be mistaken for a fault of the design.
    """
    if launch is None:
        launch = {}
    if not isinstance(launch, Mapping):
        raise SimRequestError(f"launch must be a mapping of launch fields, got {type(launch).__name__}")
    unknown = set(launch) - LAUNCH_FIELDS
    if unknown:
        raise SimRequestError(f"unknown launch field(s) {sorted(unknown)}; allowed: {sorted(LAUNCH_FIELDS)}")
    out = {**FIXED_LAUNCH, **launch}
    for key in LAUNCH_NUMBER_FIELDS & set(out):
        if not _is_number(out[key]):
            raise SimRequestError(f"launch field {key} must be a finite number, got {out[key]!r}")
    for key in ("time_step_s", "base_temperature_k", "base_pressure_pa"):
        if key in out and not out[key] > 0:
            raise SimRequestError(f"launch field {key} must be above 0, got {out[key]!r}")
    if "wind_turbulence" in out and not out["wind_turbulence"] >= 0:
        raise SimRequestError(f"launch field wind_turbulence must be 0 or more, got {out['wind_turbulence']!r}")
    if not isinstance(out["launch_into_wind"], bool):
        raise SimRequestError(f"launch field launch_into_wind must be true or false, got {out['launch_into_wind']!r}")
    if out["geodetic"] not in GEODETIC_MODELS:
        raise SimRequestError(f"launch field geodetic must be one of {list(GEODETIC_MODELS)}, got {out['geodetic']!r}")
    return out


def _check_run_limits(max_sim_time_s: Any, max_steps: Any, config_id: Any) -> None:
    """Raise SimRequestError for caps or a configuration id the helper would refuse."""
    if not (_is_number(max_sim_time_s) and max_sim_time_s > 0):
        raise SimRequestError(f"max_sim_time_s must be a number above 0, got {max_sim_time_s!r}")
    if isinstance(max_steps, float) and max_steps.is_integer():
        max_steps = int(max_steps)
    if not (isinstance(max_steps, int) and not isinstance(max_steps, bool) and 1 <= max_steps < 2 ** 53):
        raise SimRequestError(f"max_steps must be a whole number of 1 or more, got {max_steps!r}")
    if config_id is not None and not isinstance(config_id, str):
        raise SimRequestError(f"config_id must be text or None, got {type(config_id).__name__}")


def _looks_like_path(value: str | bytes) -> bool:
    if isinstance(value, bytes):
        return False
    stripped = value.lstrip()
    return not stripped.startswith("<") and "\n" not in value


def _remove(path: Path) -> None:
    for _ in range(20):
        try:
            path.unlink()
            return
        except FileNotFoundError:
            return
        except PermissionError:  # Windows: the helper may still hold the file for a moment
            time.sleep(0.05)
        except OSError:
            return


# ---------------------------------------------------------------------------
# Several helpers

def default_pool_size() -> int:
    """min(8, CPU count - 1), at least 1."""
    return max(1, min(8, (os.cpu_count() or 2) - 1))


class SimPool:
    """N Simulators side by side. ``run_many`` keeps the order of the requests.

    Each request is a dict of ``Simulator.run`` keyword arguments
    (``ork_text_or_path``, ``rail_m``, ``flights``, ...). A slow or hung design
    holds only its own helper; the others keep working.
    """

    def __init__(self, size: int | None = None, command: Sequence[str] | None = None, **simulator_kwargs: Any):
        self.size = size if size is not None else default_pool_size()
        if self.size < 1:
            raise ValueError("a pool needs at least one simulator")
        if command is None:
            command = helper_command()  # compile once, before the helpers start
        self.simulators: list[Simulator] = []
        self._free: queue.Queue = queue.Queue()
        self._closed = False
        errors: list[BaseException] = []
        lock = threading.Lock()

        def start_one() -> None:
            try:
                sim = Simulator(command, **simulator_kwargs)
            except BaseException as exc:  # collected and raised below
                errors.append(exc)
                return
            with lock:
                self.simulators.append(sim)

        threads = [threading.Thread(target=start_one) for _ in range(self.size)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        if errors:
            self.close()
            raise errors[0]
        for sim in self.simulators:
            self._free.put(sim)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.size,
                                                               thread_name_prefix="rocket-sim")

    def __enter__(self) -> "SimPool":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _take(self) -> Simulator:
        """Wait for a free helper. Raises RuntimeError once the pool is closed."""
        while True:
            if self._closed:
                raise RuntimeError("this SimPool is closed")
            try:
                return self._free.get(timeout=POOL_WAIT_STEP_S)
            except queue.Empty:
                continue

    def _one(self, request: Mapping[str, Any]) -> dict[str, Any]:
        return self.run(**request)

    def run(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """``Simulator.run`` on the first free helper, with the same arguments and reply.

        Safe to call from many threads at once: each call holds one helper
        for itself and gives it back when done, so at most ``size`` designs
        fly at the same time and the others wait for a helper.
        """
        sim = self._take()
        try:
            return sim.run(*args, **kwargs)
        finally:
            self._free.put(sim)

    def run_many(self, requests: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        """Run every request and return the replies in the same order.

        If any request raises (RewardSetupError), the others still finish and
        then the first error is raised.
        """
        futures = [self._executor.submit(self._one, dict(r)) for r in requests]
        concurrent.futures.wait(futures)
        for f in futures:
            exc = f.exception()
            if exc is not None:
                raise exc
        return [f.result() for f in futures]

    def close(self) -> None:
        """Stop every helper at once, also those flying a design right now.

        Requests still waiting are cancelled; requests in flight end with
        RuntimeError in run_many (and in run, also for callers still waiting
        for a free helper).
        """
        self._closed = True
        for sim in self.simulators:
            sim.close()
        executor = getattr(self, "_executor", None)
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)


# ---------------------------------------------------------------------------
# Whole-chain check

def check_setup(command: Sequence[str] | None = None,
                canary: Canary | _DefaultCanary = DEFAULT) -> dict[str, Any]:
    """Find Java and the jar, compile the helper, start it, ping it and fly the
    self-test rocket. Returns a few facts; raises RewardSetupError on any problem.

    ``command`` replaces the real helper (tests use the fake one); Java and the
    jar are then not looked up.
    """
    facts: dict[str, Any] = {}
    t0 = time.monotonic()
    if isinstance(canary, _DefaultCanary):
        canary = load_canary()
    if command is None:
        java = find_java()
        jar = find_jar()
        facts.update(java=java.version, java_path=str(java.java), java_found_by=java.source, jar=str(jar))
        t1 = time.monotonic()
        command = helper_command(java, jar)
        facts["compile_s"] = round(time.monotonic() - t1, 3)
    t2 = time.monotonic()
    with Simulator(command, canary=canary, self_test=False) as sim:
        facts["boot_s"] = round(time.monotonic() - t2, 3)
        facts["openrocket"] = sim.ping_reply.get("openrocket")
        facts["helper"] = sim.ping_reply.get("helper")
        facts["helper_java"] = sim.ping_reply.get("java")
        t3 = time.monotonic()
        reply = sim.fly_canary()
        facts["canary_s"] = round(time.monotonic() - t3, 3)
        first = reply["flights"][0]
        facts["canary"] = {k: first.get(k) for k in canary.expected}
        facts["log"] = str(sim.log_path)
    facts["total_s"] = round(time.monotonic() - t0, 3)
    return facts
