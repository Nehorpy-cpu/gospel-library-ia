const API_PATH_PREFIX = "/api";
const PRODUCTION_API_ORIGIN = "https://api.estudiopy.com";

let hasLoggedApiOrigin = false;

export class ApiConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiConfigurationError";
  }
}

export function normalizeApiOrigin(value: string | undefined): string {
  const configuredValue = value?.trim();
  if (!configuredValue) {
    throw new ApiConfigurationError(
      "Falta NEXT_PUBLIC_API_URL. Configurala con https://api.estudiopy.com y vuelve a desplegar el frontend."
    );
  }

  let url: URL;
  try {
    url = new URL(configuredValue);
  } catch {
    throw new ApiConfigurationError(
      "NEXT_PUBLIC_API_URL no es una URL valida. Usa https://api.estudiopy.com."
    );
  }

  if (!["http:", "https:"].includes(url.protocol)) {
    throw new ApiConfigurationError("NEXT_PUBLIC_API_URL debe usar http o https.");
  }
  if (url.username || url.password || url.search || url.hash) {
    throw new ApiConfigurationError("NEXT_PUBLIC_API_URL no debe incluir credenciales, query string ni fragmentos.");
  }

  const pathname = url.pathname.replace(/\/+$/, "");
  if (pathname && pathname !== API_PATH_PREFIX) {
    throw new ApiConfigurationError(
      "NEXT_PUBLIC_API_URL debe contener solo el origen de la API, por ejemplo https://api.estudiopy.com."
    );
  }

  const origin = url.origin;
  if (process.env.NEXT_PUBLIC_ENVIRONMENT === "production" && origin !== PRODUCTION_API_ORIGIN) {
    throw new ApiConfigurationError(
      `NEXT_PUBLIC_API_URL debe ser ${PRODUCTION_API_ORIGIN} en produccion.`
    );
  }

  return origin;
}

export function getApiOrigin(): string {
  const origin = normalizeApiOrigin(process.env.NEXT_PUBLIC_API_URL);
  if (!hasLoggedApiOrigin) {
    console.info(`[api] Base URL: ${origin}`);
    hasLoggedApiOrigin = true;
  }
  return origin;
}

export function buildApiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${getApiOrigin()}${API_PATH_PREFIX}${normalizedPath}`;
}

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const url = buildApiUrl(path);
  try {
    return await fetch(url, init);
  } catch {
    throw new Error(`No se pudo establecer conexión con la API en ${getApiOrigin()}. Inténtalo nuevamente más tarde.`);
  }
}
