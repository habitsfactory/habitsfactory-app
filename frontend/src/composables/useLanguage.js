import { ref, computed, watchEffect } from 'vue'
import { translations } from '@/composables/translations'

const supportedLanguages = ['en', 'fr']

const getInitialLanguage = () => {
    const stored = localStorage.getItem('language')
    if (stored && supportedLanguages.includes(stored)) {
        return stored
    }

    // Detect browser/OS language
    const browserLang = navigator.language || navigator.userLanguage
    const langCode = browserLang?.split('-')[0] // e.g., 'en-US' -> 'en'

    if (langCode && supportedLanguages.includes(langCode)) {
        return langCode
    }

    return 'en'
}

const currentLanguage = ref(getInitialLanguage())

const languages = [
    { code: 'en', name: 'English' },
    { code: 'fr', name: 'Français' },
]

watchEffect(() => {
    document.documentElement.lang = currentLanguage.value
})

export const useLanguage = () => {
    const setLanguage = (lang) => {
        currentLanguage.value = lang
        localStorage.setItem('language', lang)
    }

    const currentLanguageInfo = computed(() => {
        return languages.find(lang => lang.code === currentLanguage.value) || languages[0]
    })

    // Translate a key. `params` fills `{placeholders}` in the string:
    //   t('trackedDays', { tracked: 4, total: 30 })
    const t = (key, params) => {
        let text = translations[currentLanguage.value]?.[key] || translations['en'][key] || key
        if (params) {
            for (const [name, value] of Object.entries(params)) {
                text = text.replaceAll(`{${name}}`, value)
            }
        }
        return text
    }

    return {
        currentLanguage,
        // BCP 47 tag for Intl / toLocaleDateString
        locale: currentLanguage,
        setLanguage,
        languages,
        currentLanguageInfo,
        t
    }
}
