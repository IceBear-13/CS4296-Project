const API_URL = "http://54.204.234.7";

export type UploadResult = {
    downloadedFileName: string;
    blob: Blob;
};

const getFilenameFromContentDisposition = (headerValue: string | null): string | null => {
    if (!headerValue) {
        return null;
    }

    const utf8NameMatch = headerValue.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8NameMatch?.[1]) {
        try {
            return decodeURIComponent(utf8NameMatch[1]);
        } catch {
            return utf8NameMatch[1];
        }
    }

    const asciiNameMatch = headerValue.match(/filename="?([^";]+)"?/i);
    return asciiNameMatch?.[1] ?? null;
};

const resolve_resolution = (resolution: string): { width: number, height: number } => {
    if (resolution === "240p") {
        return { width: 426, height: 240 };
    } else if (resolution === "480p") {
        return { width: 854, height: 480 };
    } else if (resolution === "720p") {
        return { width: 1280, height: 720 };
    } else if (resolution === "1080p") {
        return { width: 1920, height: 1080 };
    } else if (resolution === "4K") {
        return { width: 3840, height: 2160 };
    } else {
        throw new Error("Unsupported resolution");
    }
}

export const uploadVideo = async (
    file: File,
    resolution: string,
    video_codec: string,
    audio_codec: string,
    FFmpeg_preset: string,
    crf: number,
    video_bitrate: string
) : Promise<UploadResult> => {
    const start = Date.now();
    const { width, height } = resolve_resolution(resolution);
    const requestedProfile = {
        resolution: `${width}:${height}`,
        video_codec,
        audio_codec,
        ffmpeg_preset: FFmpeg_preset,
        crf,
        video_bitrate,
    };

    const formData = new FormData();
    formData.append("file", file);
    formData.append("requested_profile", JSON.stringify(requestedProfile));

    const response = await fetch(`${API_URL}/transcode`, {
        method: "POST",
        body: formData,
    });
    
    if (!response.ok) {
        const detail = await response.text();
        throw new Error(`Failed to upload video (${response.status}): ${detail}`);
    }

    const contentDisposition = response.headers.get("content-disposition");
    const fileName = getFilenameFromContentDisposition(contentDisposition) || `output_${file.name}`;
    const blob = await response.blob();

    const end = Date.now();
    console.log(`Transcoding completed in ${(end - start) / 1000} seconds`);

    return { downloadedFileName: fileName, blob };
}

export const fetchTranscodedVideo = async (video_name: string): Promise<UploadResult> => {
    const response = await fetch(`${API_URL}/transcoded/${encodeURIComponent(video_name)}`);
    if (!response.ok) {
        const detail = await response.text();
        throw new Error(`Failed to fetch transcoded video (${response.status}): ${detail}`);
    }

    const contentDisposition = response.headers.get("content-disposition");
    const fileName = getFilenameFromContentDisposition(contentDisposition) || `output_${video_name}`;
    const blob = await response.blob();
    return { downloadedFileName: fileName, blob };
}