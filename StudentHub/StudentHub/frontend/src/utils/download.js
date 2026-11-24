import api from "../services/api";

/**
 * Downloads a report from an authenticated backend endpoint. A plain <a href> can't carry
 * the Bearer token, so this fetches as a blob (with the token already attached by the axios
 * interceptor in services/api.js) and triggers the browser's save dialog from that blob.
 */
export async function downloadReport(url, params, fallbackName) {
  const { data, headers } = await api.get(url, { params, responseType: "blob" });
  const disposition = headers["content-disposition"] || "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : fallbackName;

  const blobUrl = window.URL.createObjectURL(data);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}
