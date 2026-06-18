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
