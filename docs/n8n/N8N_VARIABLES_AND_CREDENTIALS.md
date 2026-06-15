# Variables y credenciales de n8n

## Render

Configura una variable secreta en el servicio de la API:

```env
INGESTION_API_KEY=<CLAVE_ALEATORIA_REAL>
```

No expongas esta clave en Vercel ni en variables `NEXT_PUBLIC_*`. Después de
crear o cambiar la variable, vuelve a desplegar el servicio de Render.

## n8n

Configura:

```env
GOSPEL_LIBRARY_API_URL=https://api.estudiopy.com
INGESTION_API_KEY=<LA_MISMA_CLAVE_SECRETA_CONFIGURADA_EN_RENDER>
```

Los valores entre ángulos son instrucciones, no claves literales. Reinicia n8n
si su instalación solo carga variables al iniciar.

El workflow utiliza:

```text
$env.GOSPEL_LIBRARY_API_URL
$env.INGESTION_API_KEY
```

## Opción recomendada: Header Auth

Cuando la política de n8n restringe `$env`, crea una credencial **Header Auth**:

- Nombre del header: `X-Ingestion-Key`
- Valor: la misma clave secreta de Render

Asocia la credencial al nodo **Enviar documento a Gospel Library IA** y elimina
el header manual para no enviarlo dos veces. Las credenciales de n8n no se
incluyen al exportar el workflow.

## Verificación segura

Comprueba únicamente la salud pública:

```powershell
Invoke-RestMethod "https://api.estudiopy.com/api/ingestion/documents/health"
```

No imprimas variables de entorno, headers completos ni datos de ejecución que
puedan contener la clave.
