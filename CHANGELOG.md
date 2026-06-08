# Changelog

## 0.1.0-beta

Nombre: Gospel Library IA Beta

Entorno: beta

### Incluido

- Biblioteca doctrinal con documentos reales desde PostgreSQL.
- Busqueda textual fallback y preparacion para busqueda semantica Qdrant.
- Chat doctrinal con atribucion de fuentes y modo seguro cuando no hay embeddings.
- Estudio Personal Inteligente con workspaces, notas, citas guardadas y post-it.
- Constructor de discursos basado en fuentes reales disponibles.
- Exportacion Markdown/PDF de material propio de estudio.
- Admin panel con estado de datos, fuentes, indexing, costos IA y feedback beta.
- Allowlist beta por email, onboarding inicial, limites diarios y feedback.

### Limitaciones conocidas

- La app no es oficial de La Iglesia de Jesucristo de los Santos de los Ultimos Dias.
- Qdrant puede tener cero vectores si no hay credito OpenAI; en ese caso se usa busqueda textual.
- Metadata historica de algunos documentos puede requerir limpieza manual.
- La beta privada no esta preparada para uso publico o ilimitado.

### Proximos pasos

- Invitar un grupo pequeno de usuarios beta aprobados.
- Revisar feedback doctrinal y problemas de fuentes.
- Completar embeddings cuando haya credito OpenAI.
- Medir costos, errores y retencion antes de ampliar la beta.
