import { apiSpecService } from "./apiSpec";
import { config } from "../config";

export async function getEndpoint(endpointName: string, method: string) {
  const spec = await apiSpecService.getSpec();
  const path = spec.paths[endpointName];
  if (!path) {
    return null;
  }
  return path[method.toLowerCase()];
}

export function getApiUrl(path: string) {
  return `${config.api.baseUrl}${path}`;
}