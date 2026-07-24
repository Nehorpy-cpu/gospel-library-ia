# Mis fuentes privadas

Permite guardar citas breves, referencias y notas personales para uso privado o familiar. No admite libros completos ni publica contenido en la biblioteca.

Cada fuente pertenece a `user_id`; la API filtra siempre por ese identificador y la tabla debe mantener RLS equivalente a `user_id = auth.uid()`.

Endpoints: `GET/POST /api/user-private-sources`, `GET/PATCH/DELETE /api/user-private-sources/{id}` y los alias de estudio. Los fragmentos se limitan a 3000 caracteres y las notas a 5000.

Study AI recibe `includePrivateSources: true`, incorpora como máximo cinco fuentes activas del propietario, las marca como `user_private` y no debe presentarlas como citas oficiales. Para probar, cree una fuente, active **Incluir mis fuentes privadas** en el panel IA y confirme que no se muestran fuentes de otro usuario.
