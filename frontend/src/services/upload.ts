import axios from "axios";

export interface UploadResult {
  saved: string[];
  errors: string[];
}

export async function uploadRedfinFiles(
  files: File[],
  onProgress?: (percent: number) => void,
): Promise<UploadResult> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  const token = localStorage.getItem("pricepoint-auth-token");

  const { data } = await axios.post<UploadResult>("/api/upload/redfin", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded * 100) / e.total));
      }
    },
  });

  return data;
}
