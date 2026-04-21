"use client";

import { Upload, X } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import {
  FileUpload,
  FileUploadDropzone,
  FileUploadItem,
  FileUploadItemDelete,
  FileUploadItemMetadata,
  FileUploadItemPreview,
  FileUploadList,
  FileUploadTrigger,
} from "@/components/ui/file-upload";

type FileUploadDropzone1Props = {
  value: File | null;
  onValueChange: (file: File | null) => void;
  accept?: string;
  disabled?: boolean;
  maxSizeMb?: number;
};

const FileUploadDropzone1 = ({
  value,
  onValueChange,
  accept = "video/*",
  disabled = false,
  maxSizeMb = 500,
}: FileUploadDropzone1Props) => {
  const files = value ? [value] : [];

  const maxSizeBytes = maxSizeMb * 1024 * 1024;

  const handleValueChange = React.useCallback(
    (nextFiles: File[]) => {
      const firstFile = nextFiles[0] ?? null;
      onValueChange(firstFile);
    },
    [onValueChange],
  );

  const onFileReject = React.useCallback(
    (file: File, message: string) => {
      void file;
      void message;
      onValueChange(null);
    },
    [onValueChange],
  );

  return (
    <FileUpload
      maxFiles={1}
      maxSize={maxSizeBytes}
      className="w-full"
      value={files}
      onValueChange={handleValueChange}
      onFileReject={onFileReject}
      accept={accept}
      disabled={disabled}
    >
      <FileUploadDropzone>
        <div className="flex flex-col items-center gap-1 text-center">
          <div className="flex items-center justify-center rounded-full border p-2.5">
            <Upload className="size-6 text-muted-foreground" />
          </div>
          <p className="text-sm font-medium">Drag & drop a video file here</p>
          <p className="text-xs text-muted-foreground">
            Or click to browse (max 1 file, up to {maxSizeMb}MB)
          </p>
        </div>
        <FileUploadTrigger asChild>
          <Button variant="outline" size="sm" className="mt-2 w-fit">
            Browse video
          </Button>
        </FileUploadTrigger>
      </FileUploadDropzone>
      <FileUploadList>
        {files.map((file, index) => (
          <FileUploadItem key={index} value={file}>
            <FileUploadItemPreview />
            <FileUploadItemMetadata />
            <FileUploadItemDelete asChild>
              <Button variant="ghost" size="icon" className="size-7">
                <X className="size-4" />
              </Button>
            </FileUploadItemDelete>
          </FileUploadItem>
        ))}
      </FileUploadList>
    </FileUpload>
  );
};

export default FileUploadDropzone1;
