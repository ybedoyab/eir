export const VOX_PREVIEW_USER = "eir-preview-user";
export const VOX_PREVIEW_APP = "eir-recovery";
export const VOX_PREVIEW_ACCOUNT = "ysbedoya0";
export const VOX_PREVIEW_NODE = "NODE_2";

export function previewSipLogin(): string {
  return `${VOX_PREVIEW_USER}@${VOX_PREVIEW_APP}.${VOX_PREVIEW_ACCOUNT}.voximplant.com`;
}
