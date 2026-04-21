import type { FormEvent } from "react";
import { useMemo, useState } from "react";
import { Loader2, Upload } from "lucide-react";

import { Button } from "./components/ui/button";
import FileUploadDropzone1 from "./components/file-upload-dropzone-1";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./components/ui/select";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

const RESOLUTION_OPTIONS = ["240p", "480p", "720p", "1080p"];
const VIDEO_CODEC_OPTIONS = ["libx264", "libx265", "vp9", "av1"];
const AUDIO_CODEC_OPTIONS = ["aac", "opus", "mp3", "copy"];
const PRESET_OPTIONS = [
  "ultrafast",
  "superfast",
  "veryfast",
  "faster",
  "fast",
  "medium",
  "slow",
  "slower",
  "veryslow",
];

type SubmitJobResponse = {
  job_id: string;
  s3_input_key: string;
  sqs_message_id: string;
  status: string;
};

type FormState = {
  resolution: string;
  videoCodec: string;
  audioCodec: string;
  ffmpegPreset: string;
  crf: number;
  videoBitrate: string;
};

const initialForm: FormState = {
  resolution: "480p",
  videoCodec: "libx264",
  audioCodec: "aac",
  ffmpegPreset: "medium",
  crf: 23,
  videoBitrate: "",
};

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [form, setForm] = useState<FormState>(initialForm);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [response, setResponse] = useState<SubmitJobResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const isSubmitDisabled = useMemo(
    () => isSubmitting || file === null,
    [file, isSubmitting],
  );

  const handleFileChange = (nextFile: File | null) => {
    setFile(nextFile);
    setResponse(null);
    setErrorMessage("");
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setErrorMessage("Please select a video file before submitting.");
      return;
    }

    setIsSubmitting(true);
    setResponse(null);
    setErrorMessage("");

    const requestedProfile = {
      resolution: form.resolution,
      video_codec: form.videoCodec,
      audio_codec: form.audioCodec,
      ffmpeg_preset: form.ffmpegPreset,
      crf: form.crf,
      video_bitrate: form.videoBitrate || null,
    };

    const payload = new FormData();
    payload.append("file", file);
    payload.append("target_resolution", form.resolution);
    payload.append("target_video_codec", form.videoCodec);
    payload.append("target_audio_codec", form.audioCodec);
    payload.append("requested_profile", JSON.stringify(requestedProfile));

    try {
      const uploadResponse = await fetch(`${API_BASE_URL}/jobs/transcode`, {
        method: "POST",
        body: payload,
      });

      const data = await uploadResponse.json();
      if (!uploadResponse.ok) {
        const detail =
          typeof data.detail === "string"
            ? data.detail
            : "Failed to submit job.";
        throw new Error(detail);
      }

      setResponse(data as SubmitJobResponse);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Unexpected error while submitting.";
      setErrorMessage(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#f4f5f8_10%,_#f2efea_45%,_#ece9e2_100%)] px-4 py-10 text-slate-900">
      <div className="mx-auto w-full max-w-4xl">
        <header className="mb-8">
          <p className="mb-2 inline-flex rounded-full border border-slate-300/70 bg-white/80 px-3 py-1 font-mono text-xs uppercase tracking-[0.2em] text-slate-600">
            BudakBandar
          </p>
          <h1 className="text-balance font-heading text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
            Edge vs Cloud Video Transcoding Uploader
          </h1>
        </header>

        <Card className="border-slate-300/70 bg-white/90 shadow-2xl shadow-slate-400/20 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>Submit Transcoding Job</CardTitle>
            <CardDescription>
              Configure requested_profile options and send the file to the
              gateway API.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form className="grid gap-6" onSubmit={handleSubmit}>
              <div className="grid gap-2">
                <Label htmlFor="video-file">Video file</Label>
                <FileUploadDropzone1
                  value={file}
                  onValueChange={handleFileChange}
                  accept="video/*"
                  maxSizeMb={500}
                />
                {file && (
                  <p className="text-sm text-slate-600">
                    Selected: {file.name}
                  </p>
                )}
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="grid gap-2">
                  <Label htmlFor="resolution">Resolution</Label>
                  <Select
                    value={form.resolution}
                    onValueChange={(value) =>
                      setForm((prev) => ({ ...prev, resolution: value }))
                    }
                  >
                    <SelectTrigger id="resolution">
                      <SelectValue placeholder="Select resolution" />
                    </SelectTrigger>
                    <SelectContent>
                      {RESOLUTION_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {option}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="video-codec">Video codec</Label>
                  <Select
                    value={form.videoCodec}
                    onValueChange={(value) =>
                      setForm((prev) => ({ ...prev, videoCodec: value }))
                    }
                  >
                    <SelectTrigger id="video-codec">
                      <SelectValue placeholder="Select video codec" />
                    </SelectTrigger>
                    <SelectContent>
                      {VIDEO_CODEC_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {option}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="audio-codec">Audio codec</Label>
                  <Select
                    value={form.audioCodec}
                    onValueChange={(value) =>
                      setForm((prev) => ({ ...prev, audioCodec: value }))
                    }
                  >
                    <SelectTrigger id="audio-codec">
                      <SelectValue placeholder="Select audio codec" />
                    </SelectTrigger>
                    <SelectContent>
                      {AUDIO_CODEC_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {option}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="ffmpeg-preset">FFmpeg preset</Label>
                  <Select
                    value={form.ffmpegPreset}
                    onValueChange={(value) =>
                      setForm((prev) => ({ ...prev, ffmpegPreset: value }))
                    }
                  >
                    <SelectTrigger id="ffmpeg-preset">
                      <SelectValue placeholder="Select preset" />
                    </SelectTrigger>
                    <SelectContent>
                      {PRESET_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {option}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="crf">CRF (0-51)</Label>
                  <Input
                    id="crf"
                    type="number"
                    min={0}
                    max={51}
                    value={form.crf}
                    onChange={(event) =>
                      setForm((prev) => ({
                        ...prev,
                        crf: Number.parseInt(event.target.value, 10) || 0,
                      }))
                    }
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="video-bitrate">
                    Video bitrate (optional)
                  </Label>
                  <Input
                    id="video-bitrate"
                    type="text"
                    placeholder="e.g. 2M"
                    value={form.videoBitrate}
                    onChange={(event) =>
                      setForm((prev) => ({
                        ...prev,
                        videoBitrate: event.target.value,
                      }))
                    }
                  />
                </div>
              </div>

              <Button type="submit" disabled={isSubmitDisabled}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="size-4" />
                    Upload
                  </>
                )}
              </Button>
            </form>

            {errorMessage && (
              <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {errorMessage}
              </div>
            )}

            {response && (
              <div className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
                <p className="font-semibold">Job submitted successfully</p>
                <p className="mt-1">job_id: {response.job_id}</p>
                <p>s3_input_key: {response.s3_input_key}</p>
                <p>sqs_message_id: {response.sqs_message_id}</p>
                <p>status: {response.status}</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

export default App;
