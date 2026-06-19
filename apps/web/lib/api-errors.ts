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
    return "Debes iniciar sesión para crear estudios.";
  }
  if (status === 404) {
    return "El endpoint de estudios no está disponible en la API desplegada.";
  }
  if (status === 422) {
    return "Revisá los campos del estudio.";
  }
  if (status >= 500) {
    return "La API tuvo un error al crear el estudio.";
  }
  return apiErrorMessage(status);
}
