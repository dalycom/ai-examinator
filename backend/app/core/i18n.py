from app.core.enums import Locale

MESSAGES: dict[str, dict[str, str]] = {
    "errors.validation_failed": {
        "en": "Validation failed",
        "ar": "فشل التحقق",
        "fr": "Échec de la validation",
    },
    "errors.http_error": {
        "en": "Request could not be completed",
        "ar": "تعذر إكمال الطلب",
        "fr": "La requête n'a pas pu être traitée",
    },
    "errors.unauthorized": {
        "en": "Authentication required",
        "ar": "المصادقة مطلوبة",
        "fr": "Authentification requise",
    },
    "errors.forbidden": {
        "en": "You do not have permission to perform this action",
        "ar": "ليس لديك إذن لتنفيذ هذا الإجراء",
        "fr": "Vous n'avez pas la permission d'effectuer cette action",
    },
    "errors.invalid_credentials": {
        "en": "Invalid email or password",
        "ar": "البريد الإلكتروني أو كلمة المرور غير صحيحة",
        "fr": "E-mail ou mot de passe invalide",
    },
    "errors.user_disabled": {
        "en": "This account is disabled",
        "ar": "هذا الحساب معطل",
        "fr": "Ce compte est désactivé",
    },
    "errors.organization_exists": {
        "en": "An organization with this slug already exists",
        "ar": "توجد منظمة بهذا المعرّف بالفعل",
        "fr": "Une organisation avec ce slug existe déjà",
    },
    "errors.mfa_required": {
        "en": "Multi-factor authentication is required",
        "ar": "المصادقة متعددة العوامل مطلوبة",
        "fr": "L'authentification multifacteur est requise",
    },
    "errors.invalid_mfa_code": {
        "en": "Invalid MFA code",
        "ar": "رمز المصادقة غير صالح",
        "fr": "Code MFA invalide",
    },
    "errors.refresh_token_invalid": {
        "en": "Refresh token is invalid or expired",
        "ar": "رمز التحديث غير صالح أو منتهٍ",
        "fr": "Le jeton de rafraîchissement est invalide ou expiré",
    },
    "errors.consent_required": {
        "en": "Active patient consent is required before recording or AI processing",
        "ar": "موافقة المريض النشطة مطلوبة قبل التسجيل أو معالجة الذكاء الاصطناعي",
        "fr": "Le consentement actif du patient est requis avant l'enregistrement ou le traitement IA",
    },
    "errors.note_already_signed": {
        "en": "Signed clinical notes cannot be edited; create an addendum instead",
        "ar": "لا يمكن تعديل الملاحظات السريرية الموقعة؛ أنشئ ملحقاً بدلاً من ذلك",
        "fr": "Les notes cliniques signées ne peuvent pas être modifiées ; créez un addendum",
    },
    "errors.transcript_required": {
        "en": "A transcript is required before AI extraction can run",
        "ar": "يلزم وجود نص مكتوب قبل تشغيل استخراج الذكاء الاصطناعي",
        "fr": "Une transcription est requise avant l'extraction IA",
    },
    "errors.ai_feature_disabled": {
        "en": "This AI feature is disabled for your organization",
        "ar": "ميزة الذكاء الاصطناعي هذه معطلة لمنظمتك",
        "fr": "Cette fonctionnalité IA est désactivée pour votre organisation",
    },
    "errors.ai_cloud_blocked": {
        "en": "Cloud AI processing is blocked until external PHI is explicitly allowed",
        "ar": "معالجة الذكاء الاصطناعي السحابية محظورة حتى يُسمح صراحة بمشاركة البيانات الصحية خارجياً",
        "fr": "Le traitement IA cloud est bloqué tant que le PHI externe n'est pas explicitement autorisé",
    },
    "errors.ai_decision_recorded": {
        "en": "A review decision has already been recorded for this suggestion",
        "ar": "تم تسجيل قرار مراجعة لهذا الاقتراح بالفعل",
        "fr": "Une décision de revue a déjà été enregistrée pour cette suggestion",
    },
    "errors.ai_extraction_failed": {
        "en": "AI extraction failed; check the session transcript and try again",
        "ar": "فشل استخراج الذكاء الاصطناعي؛ تحقق من نص الجلسة وحاول مرة أخرى",
        "fr": "L'extraction IA a échoué ; vérifiez la transcription et réessayez",
    },
}


def translate(message_key: str, locale: str | Locale) -> str:
    locale_code = locale.value if isinstance(locale, Locale) else locale
    catalog = MESSAGES.get(message_key, {})
    return catalog.get(locale_code, catalog.get("en", message_key))
