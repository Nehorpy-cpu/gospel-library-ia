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


def calling_application_guidance(calling_name: str | None) -> str:
    if not calling_name:
        return (
            "Aplicacion segun mi llamamiento: discipulado general. Enfoca la aplicacion en "
            "discipulado personal, familia, ministracion, convenios, estudio personal, templo "
            "y preparacion para servir."
        )
    normalized = calling_name.lower()
    if "obispo" in normalized:
        emphasis = (
            "ministrar a familias, presidir el Sacerdocio Aaronico, cuidar a los jovenes, "
            "ayudar al arrepentimiento, fortalecer el consejo de barrio, templo, obra misional "
            "y bienestar espiritual"
        )
    elif "presidente de estaca" in normalized:
        emphasis = (
            "fortalecer obispos, cuidar la doctrina, elevar la vision de la estaca, activar "
            "consejos, apoyar obra misional, templo, nueva generacion y autosuficiencia espiritual"
        )
    elif "setenta de area" in normalized:
        emphasis = (
            "fortalecer presidentes de estaca, ministrar a lideres, elevar la vision de Area, "
            "recoger a Israel, fortalecer la nueva generacion, templo, obra misional y conversion profunda"
        )
    elif "sociedad de socorro" in normalized:
        emphasis = (
            "ministracion, cuidado de las hermanas, alivio temporal y espiritual, convenios, "
            "templo, unidad con el cuorum de elderes y consejo de barrio"
        )
    elif "maestro" in normalized or "ensenanza" in normalized or "instituto" in normalized or "seminario" in normalized:
        emphasis = (
            "ensenar a la manera del Salvador, ayudar a descubrir doctrina, invitar a actuar, "
            "hacer preguntas inspiradas y centrar la clase en Jesucristo"
        )
    elif "joven" in normalized or "diaconos" in normalized or "maestros" in normalized or "presbiteros" in normalized:
        emphasis = (
            "ejemplo, testimonio, unidad del cuorum o clase, participacion en la obra de salvacion "
            "y exaltacion, y preparacion espiritual"
        )
    else:
        emphasis = (
            "responsabilidades reales del llamamiento, ministracion, convenios, consejo, templo, "
            "obra misional, servicio cristiano y aplicacion personal centrada en Jesucristo"
        )
    return f"Aplicacion segun mi llamamiento: {calling_name}. Enfoca ejemplos y preguntas en {emphasis}."


def calling_focus_prompt_block(focus: CallingFocusLike | None) -> str:
    calling_name = calling_display_name(focus)
    return f"""
Enfoque por llamamiento:
- La doctrina no se adapta ni se cambia por llamamiento.
- Lo que cambia es la aplicacion, el enfasis, las preguntas de reflexion y los ejemplos practicos.
- Reemplaza cualquier seccion fija de liderazgo por: "Aplicacion segun mi llamamiento: {calling_name or 'discipulado general'}".
- {calling_application_guidance(calling_name)}
""".strip()
