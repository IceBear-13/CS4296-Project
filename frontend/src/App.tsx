import type { SubmitEvent } from "react";
import { useMemo, useState } from "react";
import { Download, Loader2, Upload } from "lucide-react";

import { Button } from "./components/ui/button";
import FileUploadDropzone1 from "./components/file-upload-dropzone-1";
import {
  Card,
  CardContent,
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
import {
  fetchTranscodedVideo,
  fetchTranscodedVideoEdge,
  type UploadResult,
  uploadVideo,
  uploadVideoEdge,
} from "./api";

// const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

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

type UploadTarget = "cloud" | "edge";

// type SubmitJobResponse = {
//   job_id: string;
//   s3_input_key: string;
//   sqs_message_id: string;
//   status: string;
// };

type FormState = {
  resolution: string;
  video_codec: string;
  audio_codec: string;
  ffmpeg_preset: string;
  crf: number;
  video_bitrate: string;
};

const initialForm: FormState = {
  resolution: "480p",
  video_codec: "libx264",
  audio_codec: "aac",
  ffmpeg_preset: "medium",
  crf: 23,
  video_bitrate: "",
};

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [form, setForm] = useState<FormState>(initialForm);
  const [uploadTarget, setUploadTarget] = useState<UploadTarget>("cloud");
  const [edgeHostAddress, setEdgeHostAddress] = useState("http://127.0.0.1:8000");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isFetching, setIsFetching] = useState(false);
  const [fetchFileName, setFetchFileName] = useState("");
  const [response, setResponse] = useState<UploadResult | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const normalizedEdgeHostAddress = edgeHostAddress.trim().replace(/\/$/, "");

  const isSubmitDisabled = useMemo(
    () =>
      isSubmitting ||
      file === null ||
      (uploadTarget === "edge" && !normalizedEdgeHostAddress),
    [file, isSubmitting, uploadTarget, normalizedEdgeHostAddress],
  );

  const handleFileChange = (nextFile: File | null) => {
    setFile(nextFile);
    setResponse(null);
    setErrorMessage("");
  };

  const handleSubmit = async (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setErrorMessage("Please select a video file before submitting.");
      return;
    }

    setIsSubmitting(true);
    setResponse(null);
    setErrorMessage("");

    try {
      if (uploadTarget === "edge" && !normalizedEdgeHostAddress) {
        throw new Error("Please enter an Edge host address.");
      }

      const uploadResponse =
        uploadTarget === "edge"
          ? await uploadVideoEdge(
              file,
              form.resolution,
              form.video_codec,
              form.audio_codec,
              form.ffmpeg_preset,
              form.crf,
              form.video_bitrate,
              normalizedEdgeHostAddress,
            )
          : await uploadVideo(
              file,
              form.resolution,
              form.video_codec,
              form.audio_codec,
              form.ffmpeg_preset,
              form.crf,
              form.video_bitrate,
            );

      setResponse(uploadResponse);
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

  const handleDownload = () => {
    if (!response) {
      return;
    }

    const blobUrl = URL.createObjectURL(response.blob);
    const downloadLink = document.createElement("a");
    downloadLink.href = blobUrl;
    downloadLink.download = response.downloadedFileName;
    document.body.appendChild(downloadLink);
    downloadLink.click();
    downloadLink.remove();
    URL.revokeObjectURL(blobUrl);
  };

  const handleFetchTranscodedVideo = async () => {
    if (!fetchFileName.trim()) {
      setErrorMessage("Please enter a transcoded filename to fetch.");
      return;
    }

    setIsFetching(true);
    setResponse(null);
    setErrorMessage("");

    try {
      if (uploadTarget === "edge" && !normalizedEdgeHostAddress) {
        throw new Error("Please enter an Edge host address.");
      }

      const fetchResponse =
        uploadTarget === "edge"
          ? await fetchTranscodedVideoEdge(
              fetchFileName.trim(),
              normalizedEdgeHostAddress,
            )
          : await fetchTranscodedVideo(fetchFileName.trim());

      setResponse(fetchResponse);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Unexpected error while fetching transcoded video.";
      setErrorMessage(message);
    } finally {
      setIsFetching(false);
    }
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,#f4f5f8_10%,#f2efea_45%,#ece9e2_100%)] px-4 py-10 text-slate-900">
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
          </CardHeader>

          <CardContent>
            <form className="grid gap-6" onSubmit={handleSubmit}>
              <div className="grid gap-2">
                <Label htmlFor="upload-target">Upload target</Label>
                <Select
                  value={uploadTarget}
                  onValueChange={(value) =>
                    setUploadTarget(value as UploadTarget)
                  }
                >
                  <SelectTrigger id="upload-target">
                    <SelectValue placeholder="Select upload target" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cloud">Cloud</SelectItem>
                    <SelectItem value="edge">Edge</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {uploadTarget === "edge" && (
                <div className="grid gap-2">
                  <Label htmlFor="edge-host-address">Edge host address</Label>
                  <Input
                    id="edge-host-address"
                    type="url"
                    placeholder="e.g. http://127.0.0.1:8000"
                    value={edgeHostAddress}
                    onChange={(event) => setEdgeHostAddress(event.target.value)}
                  />
                </div>
              )}

              <div className="grid gap-2">
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
                    value={form.video_codec}
                    onValueChange={(value) =>
                      setForm((prev) => ({ ...prev, video_codec: value }))
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
                    value={form.audio_codec}
                    onValueChange={(value) =>
                      setForm((prev) => ({ ...prev, audio_codec: value }))
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
                    value={form.ffmpeg_preset}
                    onValueChange={(value) =>
                      setForm((prev) => ({ ...prev, ffmpeg_preset: value }))
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
                    value={form.video_bitrate}
                    onChange={(event) =>
                      setForm((prev) => ({
                        ...prev,
                        video_bitrate: event.target.value,
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

            <div className="mt-6 border-t border-slate-200 pt-6">
              <p className="mb-3 text-sm font-semibold text-slate-800">
                Fetch existing transcoded video
              </p>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                <div className="grid flex-1 gap-2">
                  <Label htmlFor="fetch-video-name">Transcoded file name</Label>
                  <Input
                    id="fetch-video-name"
                    type="text"
                    placeholder="e.g. my-video.mp4"
                    value={fetchFileName}
                    onChange={(event) => setFetchFileName(event.target.value)}
                  />
                </div>
                <Button
                  type="button"
                  onClick={handleFetchTranscodedVideo}
                  disabled={isFetching || isSubmitting}
                >
                  {isFetching ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Fetching...
                    </>
                  ) : (
                    <>
                      <Download className="size-4" />
                      Fetch video
                    </>
                  )}
                </Button>
              </div>
            </div>

            {errorMessage && (
              <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {errorMessage}
              </div>
            )}

            {response && (
              <div className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
                <p className="font-semibold">Transcoding complete</p>
                <p className="mt-1">Ready to download: {response.downloadedFileName}</p>
                <Button type="button" className="mt-3" onClick={handleDownload}>
                  <Download className="size-4" />
                  Download file
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

export default App;
