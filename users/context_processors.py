from django.utils.translation import get_language


def user_role_context(request):
    """Inject role flags and language info into all templates."""
    ctx = {
        'CURRENT_LANGUAGE': get_language() or 'ar',
        'IS_RTL': (get_language() or 'ar').startswith('ar'),
    }
    if request.user.is_authenticated:
        u = request.user
        ctx.update({
            'is_admin_user': u.is_admin,
            'is_coach_user': u.is_coach,
            'is_coach_manager_user': u.is_coach_manager,
            'is_parent_user': u.is_parent,
            'is_youth_user': u.is_youth,
            'primary_role': (u.roles[0] if u.roles else 'youth'),
        })
    return ctx
