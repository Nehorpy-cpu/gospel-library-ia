from typing import Protocol


class CallingFocusLike(Protocol):
    callingCategory: str | None
    callingName: str | None
    customCallingName: str | None
    callingFocusEnabled: bool


def calling_display_name(focus: CallingFocusLike | None) -> str | None:
    if not focus or not focus.callingFocusEnabled:
        return None
    if focus.callingName and "otro" in focus.callingName.lower() and focus.customCallingName:
        return focus.customCallingName.strip() or None
    return (focus.callingName or focus.customCallingName or "").strip() or None


def calling_application_note(focus: CallingFocusLike | None) -> str:
    calling_name = calling_display_name(focus)
    if not calling_name:
        return (
            "Aplicacion segun mi llamamiento: discipulado general. La doctrina no cambia; "
            "el enfoque practico se centra en discipulado personal, familia, ministracion, "
            "convenios, templo y preparacion para servir."
        )
    return (
        f"Aplicacion segun mi llamamiento: {calling_name}. La doctrina no cambia por el "
        "llamamiento; el enfoque practico se ajusta a la aplicacion, preguntas, ejemplos "
        "y responsabilidades de servicio del usuario."
    )
