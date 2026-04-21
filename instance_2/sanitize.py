import os
import re
import unicodedata


def sanitize_movie_filename(
	filename: str,
	replacement: str = "_",
	max_length: int = 180,
) -> str:
	"""Return a Linux-safe movie filename suitable for ffmpeg temp paths.

	- Removes path components (keeps basename only).
	- Normalizes unicode to ASCII.
	- Replaces spaces and unsafe characters.
	- Preserves extension when possible.
	"""
	if not filename or not filename.strip():
		return "video.mp4"

	base_name = os.path.basename(filename.strip().replace("\x00", ""))
	name, ext = os.path.splitext(base_name)

	# Normalize unicode and keep only printable ASCII.
	name = (
		unicodedata.normalize("NFKD", name)
		.encode("ascii", "ignore")
		.decode("ascii")
	)
	ext = (
		unicodedata.normalize("NFKD", ext)
		.encode("ascii", "ignore")
		.decode("ascii")
	)

	name = re.sub(r"\s+", replacement, name)
	name = re.sub(r"[^A-Za-z0-9._-]", replacement, name)
	name = re.sub(rf"{re.escape(replacement)}+", replacement, name)
	name = name.strip("._-")

	ext = re.sub(r"[^A-Za-z0-9.]", "", ext)
	if ext and not ext.startswith("."):
		ext = f".{ext}"

	if not name:
		name = "video"

	allowed_name_len = max(1, max_length - len(ext))
	name = name[:allowed_name_len]

	sanitized = f"{name}{ext}" if ext else name
	return sanitized or "video.mp4"
