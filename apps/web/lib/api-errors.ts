export function apiErrorMessage(status: number, fallback?: string): string {
  if (status === 401) {
    return "Debes iniciar sesion para continuar.";
  }
  if (status === 404) {
    return "No se encontro el endpoint de la API. Verifica que Render tenga desplegada la version mas reciente.";
  }
  if (status === 422) {
    return "Los datos enviados no son validos. Revisa el formulario e intentalo nuevamente.";
  }
  if (status >= 500) {
    return "La API respondio con un error interno. Intentalo nuevamente mas tarde.";
  }
  return fallback || `La API respondio con estado ${status}.`;
}

export function studyWorkspaceCreateErrorMessage(status: number): string {
  if (status === 401) {
    return "Debes iniciar sesion para crear estudios.";
  }
  if (status === 404) {
    return "El endpoint de estudios no esta disponible en la API desplegada.";
  }
  if (status === 422) {
    return "Revisa los campos del estudio.";
  }
  if (status >= 500) {
    return "La API tuvo un error al crear el estudio.";
  }
  return apiErrorMessage(status);
}

export function studyWorkspaceAiErrorMessage(status: number, source?: string, retryAfterSeconds?: number): string {
  const waitText = retryAfterSeconds ? ` Espera ${retryAfterSeconds} segundos.` : "";
  if (status === 401) {
    return "Debes iniciar sesion para usar la IA del estudio.";
  }
  if (status === 404) {
    return "No se encontro el estudio.";
  }
  if (status === 422) {
    return "Revisa los campos del pedido de IA.";
  }
  if (status === 429) {
    if (source === "openai_rate_limit") {
      return `OpenAI alcanzo un limite temporal.${waitText || " Espera unos segundos."}`;
    }
    if (source === "internal_rate_limit") {
      return `Alcanzaste un limite temporal.${waitText || " Espera unos segundos y volve a intentar."}`;
    }
    return `Alcanzaste un limite temporal.${waitText || " Intenta nuevamente mas tarde."}`;
  }
  if (status === 409) {
    return "Ya hay una generacion de IA en curso para este estudio. Espera a que termine.";
  }
  if (status === 502) {
    return "La IA respondio con un formato inesperado o invalido.";
  }
  if (status === 503) {
    return "La funcion de IA todavia no esta configurada en el servidor.";
  }
  if (status === 504) {
    return "La IA tardo demasiado en responder.";
  }
  if (status >= 500) {
    return "No se pudo generar informacion con IA.";
  }
  return apiErrorMessage(status);
}
