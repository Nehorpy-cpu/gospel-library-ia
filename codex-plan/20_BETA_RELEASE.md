Ejecuta la Fase 20: BETA\_RELEASE.



Objetivo:

Preparar Gospel Library IA para una beta privada con usuarios reales.



No hacer lanzamiento público todavía.

No permitir uso ilimitado.

No exponer datos privados.

No dejar admin abierto.



Tareas obligatorias:



1\. Definir versión beta:

&#x20;  - nombre: Gospel Library IA Beta

&#x20;  - versión: 0.1.0-beta

&#x20;  - entorno: beta

&#x20;  - changelog inicial



2\. Landing beta:

&#x20;  - página /beta

&#x20;  - explicación breve

&#x20;  - beneficios

&#x20;  - limitaciones

&#x20;  - aviso de que está en prueba

&#x20;  - botón solicitar acceso o iniciar sesión



3\. Onboarding:

&#x20;  - primer ingreso del usuario

&#x20;  - elegir llamamiento o perfil de estudio:

&#x20;    - miembro

&#x20;    - maestro de Escuela Dominical

&#x20;    - maestro de Instituto/Seminario

&#x20;    - líder de jóvenes

&#x20;    - obispo

&#x20;    - presidente de estaca

&#x20;    - Setenta de Área

&#x20;    - misionero

&#x20;    - investigador doctrinal

&#x20;  - idioma preferido

&#x20;  - fuentes preferidas



4\. Límites beta:

&#x20;  - máximo workspaces por usuario

&#x20;  - máximo búsquedas IA por día

&#x20;  - máximo generación de discursos por día

&#x20;  - máximo exportaciones por día

&#x20;  - fallback textual ilimitado o con límite alto



5\. Feedback:

&#x20;  - botón “Enviar feedback”

&#x20;  - endpoint para feedback

&#x20;  - tabla feedback

&#x20;  - admin feedback panel

&#x20;  - campos:

&#x20;    - userId

&#x20;    - page

&#x20;    - type: bug | suggestion | doctrinal\_source\_issue | ui\_issue | other

&#x20;    - message

&#x20;    - screenshotUrl opcional

&#x20;    - createdAt

&#x20;    - status



6\. Error reporting:

&#x20;  - preparar Sentry o logger equivalente

&#x20;  - capturar errores frontend

&#x20;  - capturar errores backend

&#x20;  - no capturar datos sensibles

&#x20;  - documentar variables



7\. Beta admin panel:

&#x20;  - usuarios beta

&#x20;  - actividad básica

&#x20;  - feedback recibido

&#x20;  - errores recientes

&#x20;  - uso IA

&#x20;  - documentos indexados

&#x20;  - estado de fuentes



8\. Políticas básicas:

&#x20;  - crear página /privacy

&#x20;  - crear página /terms

&#x20;  - explicar:

&#x20;    - notas personales privadas

&#x20;    - uso de IA

&#x20;    - fuentes consultadas

&#x20;    - limitaciones doctrinales

&#x20;    - no reemplaza el estudio personal ni las fuentes oficiales



9\. Mensajes doctrinales de seguridad:

&#x20;  - la app debe indicar que las fuentes oficiales de la Iglesia tienen prioridad

&#x20;  - diferenciar doctrina oficial, comentario académico y reflexión personal

&#x20;  - no presentar respuestas IA como revelación

&#x20;  - recordar que el usuario debe verificar las fuentes



10\. Email o invitaciones:

&#x20;  - preparar sistema simple de allowlist beta por email

&#x20;  - admin puede aprobar usuarios beta

&#x20;  - si no está aprobado, mostrar mensaje de espera



11\. Métricas beta:

&#x20;  - usuarios activos

&#x20;  - búsquedas

&#x20;  - workspaces creados

&#x20;  - citas guardadas

&#x20;  - post-it creados

&#x20;  - exportaciones

&#x20;  - feedback

&#x20;  - errores



12\. Checklist beta:

&#x20;  Crear docs/beta-checklist.md con:

&#x20;  - deploy listo

&#x20;  - auth listo

&#x20;  - admin protegido

&#x20;  - privacidad probada

&#x20;  - backup activo

&#x20;  - costos IA controlados

&#x20;  - feedback activo

&#x20;  - términos y privacidad publicados



13\. Changelog:

&#x20;  Crear CHANGELOG.md:

&#x20;  - 0.1.0-beta

&#x20;  - funciones incluidas

&#x20;  - limitaciones conocidas

&#x20;  - próximos pasos



14\. Preparar demo:

&#x20;  Crear docs/demo-script.md con flujo:

&#x20;  - abrir app

&#x20;  - buscar Mosíah 14:11

&#x20;  - crear estudio

&#x20;  - agregar pensamiento

&#x20;  - agregar cita

&#x20;  - crear post-it

&#x20;  - buscar fuentes

&#x20;  - construir discurso

&#x20;  - exportar



15\. Validaciones:

&#x20;  - beta landing funciona

&#x20;  - login funciona

&#x20;  - usuario no aprobado no entra si allowlist está activa

&#x20;  - usuario aprobado entra

&#x20;  - feedback se guarda

&#x20;  - admin ve feedback

&#x20;  - límites funcionan

&#x20;  - privacidad funciona

&#x20;  - build pasa

&#x20;  - tests pasan



Resultado esperado:

La app queda lista para beta privada controlada.



Al terminar:

1\. Marcar 20\_BETA\_RELEASE como DONE.

2\. Hacer commit:

&#x20;  release: fase 20 - beta release

3\. Entregar resumen:

&#x20;  - URL beta local

&#x20;  - funciones listas

&#x20;  - límites activos

&#x20;  - checklist pendiente para producción

&#x20;  - recomendación para primeros usuarios beta

