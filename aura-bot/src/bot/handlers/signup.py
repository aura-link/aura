"""Handlers /alta y /plan: gestion de clientes desde campo.

/alta nombre-zona,perfil  → Registra cliente nuevo (PPPoE + CRM)
/plan nombre,perfil       → Cambia plan PPPoE de cliente existente
"""

import unicodedata
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.roles import is_admin
from src.utils.logger import log


def _strip_accents(text: str) -> str:
    """Remueve acentos para generar el secret limpio."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _parse_alta(text: str) -> dict | None:
    """Parsea el texto del comando /alta.

    Formato: nombre completo-zona,perfil
    Retorna dict con: name, zone, profile_keyword, secret
    """
    text = text.strip()
    if not text:
        return None

    # Separar perfil (despues de la ultima coma)
    if "," not in text:
        return None
    parts = text.rsplit(",", 1)
    name_zone = parts[0].strip()
    profile_keyword = parts[1].strip().lower()

    if not profile_keyword:
        return None

    # Separar nombre y zona (por el ultimo guion)
    if "-" not in name_zone:
        return None
    name_parts = name_zone.rsplit("-", 1)
    name = name_parts[0].strip()
    zone = name_parts[1].strip()

    if not name or not zone:
        return None

    # Generar secret: todo junto, minusculas, sin acentos, sin espacios
    secret = _strip_accents(f"{name}{zone}").lower().replace(" ", "")

    return {
        "name": name.title(),
        "zone": zone.title(),
        "profile_keyword": profile_keyword,
        "secret": secret,
    }


def _match_profile(keyword: str, profiles: list[dict]) -> str | None:
    """Busca un perfil MikroTik por palabra clave.

    Ejemplo: 'basico' matchea '$300 Basico 3M/8M'
    Los perfiles del sistema (default, default-encryption, Morosos) se excluyen.
    """
    keyword = _strip_accents(keyword).lower()
    skip = {"default", "default-encryption", "default_matriz", "morosos"}
    for p in profiles:
        pname = p.get("name", "")
        if pname.lower() in skip:
            continue
        # Match si la keyword esta contenida en el nombre del perfil
        pname_clean = _strip_accents(pname).lower()
        if keyword in pname_clean:
            return pname
    return None


async def _reply(update: Update, text: str, **kwargs):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, **kwargs)
    elif update.message:
        await update.message.reply_text(text, **kwargs)


async def alta_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /alta: registra cliente nuevo."""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await _reply(update, "Solo administradores pueden usar /alta.")
        return

    mk = context.bot_data.get("mikrotik")

    # Sin argumentos: mostrar ayuda con perfiles del MikroTik
    if not context.args:
        profiles_text = ""
        if mk:
            try:
                profiles = await mk.get_ppp_profiles()
                skip = {"default", "default-encryption", "default_matriz", "morosos"}
                for p in profiles:
                    pname = p.get("name", "")
                    if pname.lower() in skip:
                        continue
                    rate = p.get("rate-limit", "sin limite")
                    profiles_text += f"  `{pname}`\n"
            except Exception:
                profiles_text = "  (no se pudo consultar MikroTik)\n"

        await _reply(
            update,
            "*Uso:* `/alta nombre-zona,perfil`\n\n"
            "*Ejemplo:*\n"
            "`/alta jesus arreola-cumbre,basico`\n\n"
            "*El bot:*\n"
            "1. Crea secret PPPoE: `jesusarreolacumbre`\n"
            "2. Crea cliente CRM: Jesus Arreola (Cumbre)\n"
            "3. Busca antena en UISP\n\n"
            f"*Perfiles MikroTik:*\n{profiles_text}"
            "\nUsa una palabra clave del perfil (ej: basico, residencial, profesional)",
            parse_mode="Markdown",
        )
        return

    raw = " ".join(context.args)
    parsed = _parse_alta(raw)

    if not parsed:
        await _reply(
            update,
            "Formato incorrecto.\n\n"
            "*Uso:* `/alta nombre-zona,perfil`\n"
            "*Ejemplo:* `/alta jesus arreola-cumbre,basico`",
            parse_mode="Markdown",
        )
        return

    name = parsed["name"]
    zone = parsed["zone"]
    secret = parsed["secret"]
    profile_keyword = parsed["profile_keyword"]

    crm = context.bot_data["uisp_crm"]
    nms = context.bot_data["uisp_nms"]

    # Buscar perfil en MikroTik
    profile_full = None
    if mk:
        try:
            profiles = await mk.get_ppp_profiles()
            profile_full = _match_profile(profile_keyword, profiles)
        except Exception as e:
            log.error("Error obteniendo perfiles MikroTik: %s", e)

    if not profile_full:
        await _reply(
            update,
            f"No se encontro perfil con '{profile_keyword}'.\n\n"
            "Usa /alta sin argumentos para ver perfiles disponibles.",
        )
        return

    # Resumen antes de ejecutar
    await _reply(
        update,
        f"*Registrando cliente nuevo...*\n\n"
        f"Nombre: *{name}*\n"
        f"Zona: *{zone}*\n"
        f"Secret PPPoE: `{secret}`\n"
        f"Perfil: *{profile_full}*\n\n"
        f"Procesando...",
        parse_mode="Markdown",
    )

    results = []
    errors = []

    # --- 1. Crear secret PPPoE en MikroTik ---
    try:
        secrets = await mk.get_ppp_secrets()
        exists = any(s.get("name") == secret for s in secrets)
        if exists:
            results.append(f"PPPoE: Secret `{secret}` ya existe")
        else:
            await mk.create_ppp_secret(
                name=secret,
                password=secret,
                profile=profile_full,
            )
            results.append(f"PPPoE: Secret `{secret}` creado")
    except Exception as e:
        log.error("Error creando PPPoE secret: %s", e)
        errors.append(f"PPPoE: Error - {e}")

    # --- 2. Crear cliente en CRM ---
    try:
        client = await crm.create_client(
            first_name=name,
            last_name=zone,
        )
        if client:
            client_id = client.get("id", "?")
            results.append(f"CRM: Cliente #{client_id} creado")
        else:
            errors.append("CRM: No se pudo crear el cliente")
    except Exception as e:
        log.error("Error creando cliente CRM: %s", e)
        errors.append(f"CRM: Error - {e}")

    # --- 3. Buscar dispositivo en UISP ---
    try:
        devices = await nms.get_devices()
        name_lower = name.lower()
        matches = []
        for d in devices:
            ident = d.get("identification", {})
            dname = (ident.get("name") or "").lower()
            if name_lower in dname or dname in name_lower:
                matches.append(d)

        if matches:
            match = matches[0]
            mname = match.get("identification", {}).get("name", "?")
            mip = match.get("ipAddress", "sin IP")
            results.append(f"UISP: Dispositivo encontrado - {mname} ({mip})")
        else:
            results.append(
                f"UISP: Dispositivo '{name}' no encontrado aun"
            )
    except Exception as e:
        log.error("Error buscando en UISP: %s", e)

    # --- Resultado final ---
    text = f"*Alta: {name} {zone}*\n\n"

    for r in results:
        text += f"  {r}\n"

    if errors:
        text += f"\n*Errores:*\n"
        for e in errors:
            text += f"  {e}\n"
    else:
        text += f"\nCliente registrado correctamente."

    await _reply(update, text, parse_mode="Markdown")

    log.info(
        "Alta: %s %s | secret=%s | profile=%s | by=%s",
        name, zone, secret, profile_full,
        user.username or user.id,
    )


def _find_secret(query: str, secrets: list[dict]) -> dict | None:
    """Busca un secret PPPoE por nombre parcial.

    Convierte query a formato secret (minusculas, sin espacios, sin acentos)
    y busca secrets que contengan ese texto.
    """
    query_clean = _strip_accents(query).lower().replace(" ", "")
    if not query_clean:
        return None

    # Primero busca match exacto
    for s in secrets:
        sname = s.get("name", "")
        if sname == query_clean:
            return s

    # Luego busca que el secret empiece con el query
    for s in secrets:
        sname = s.get("name", "")
        if sname.startswith(query_clean):
            return s

    # Finalmente busca que el query este contenido en el secret
    for s in secrets:
        sname = s.get("name", "")
        if query_clean in sname:
            return s

    return None


async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /plan: cambia el perfil PPPoE de un cliente."""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await _reply(update, "Solo administradores pueden usar /plan.")
        return

    mk = context.bot_data.get("mikrotik")
    if not mk:
        await _reply(update, "MikroTik no disponible.")
        return

    if not context.args:
        await _reply(
            update,
            "*Uso:* `/plan nombre,nuevo perfil`\n\n"
            "*Ejemplo:*\n"
            "`/plan jesus valencia,residencial`\n\n"
            "Busca el secret PPPoE que coincida con 'jesus valencia' "
            "y cambia su perfil al que contenga 'residencial'.",
            parse_mode="Markdown",
        )
        return

    raw = " ".join(context.args)

    if "," not in raw:
        await _reply(
            update,
            "Formato: `/plan nombre,perfil`\n"
            "Ejemplo: `/plan jesus valencia,residencial`",
            parse_mode="Markdown",
        )
        return

    parts = raw.rsplit(",", 1)
    query = parts[0].strip()
    profile_keyword = parts[1].strip().lower()

    if not query or not profile_keyword:
        await _reply(update, "Nombre y perfil son requeridos.")
        return

    # Buscar perfil
    try:
        profiles = await mk.get_ppp_profiles()
        new_profile = _match_profile(profile_keyword, profiles)
    except Exception as e:
        await _reply(update, f"Error consultando MikroTik: {e}")
        return

    if not new_profile:
        await _reply(
            update,
            f"No se encontro perfil con '{profile_keyword}'.\n"
            "Usa /alta sin argumentos para ver perfiles.",
        )
        return

    # Buscar secret
    try:
        secrets = await mk.get_ppp_secrets()
        secret = _find_secret(query, secrets)
    except Exception as e:
        await _reply(update, f"Error consultando secrets: {e}")
        return

    if not secret:
        await _reply(
            update,
            f"No se encontro secret PPPoE para '{query}'.\n"
            "Verifica el nombre del cliente.",
        )
        return

    secret_name = secret.get("name", "?")
    secret_id = secret.get(".id", "")
    old_profile = secret.get("profile", "?")

    if old_profile == new_profile:
        await _reply(
            update,
            f"El secret `{secret_name}` ya tiene el perfil *{new_profile}*.",
            parse_mode="Markdown",
        )
        return

    # Cambiar perfil
    try:
        await mk.update_ppp_secret(secret_id, profile=new_profile)
    except Exception as e:
        await _reply(update, f"Error cambiando perfil: {e}")
        return

    await _reply(
        update,
        f"*Plan actualizado*\n\n"
        f"Cliente: `{secret_name}`\n"
        f"Anterior: *{old_profile}*\n"
        f"Nuevo: *{new_profile}*\n\n"
        f"El cambio aplica en la proxima reconexion PPPoE.",
        parse_mode="Markdown",
    )

    log.info(
        "Plan: %s | %s -> %s | by=%s",
        secret_name, old_profile, new_profile,
        user.username or user.id,
    )
