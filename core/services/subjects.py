def split_subject_name(name):
    normalized_name = " ".join(str(name or "").strip().split())
    if not normalized_name:
        return "", ""

    if " " in normalized_name:
        last_name, first_name = normalized_name.split(" ", 1)
        return last_name.strip(), first_name.strip()

    if len(normalized_name) == 1:
        return "", normalized_name

    return normalized_name[0], normalized_name[1:]


def get_account_full_name(user):
    if not user:
        return ""

    first_name = (user.first_name or "").strip()
    last_name = (user.last_name or "").strip()

    if last_name:
        return f"{last_name}{first_name}".strip()
    return first_name


def get_user_identity_name(user):
    if not user:
        return ""

    questionnaire = getattr(user, "questionnaire", None)
    questionnaire_name = getattr(questionnaire, "name", "")
    full_name = get_account_full_name(user)

    return (full_name or questionnaire_name).strip()


def get_subject_display_name(user):
    return get_user_identity_name(user) or "尚未填姓名"


def get_subject_contact_line(user):
    if not user:
        return "未綁定帳號"

    contact_parts = [user.username]
    if user.email:
        contact_parts.append(user.email)
    return " / ".join(contact_parts)
