/**
 * Translation Helper Functions
 * All functions ≤8 lines for modular architecture compliance
 */

export const createTranslations = () => ({
  en: { 
    welcome: 'Welcome', 
    goodbye: 'Goodbye',
    loading: 'Loading...',
    error: 'An error occurred'
  },
  es: { 
    welcome: 'Bienvenido', 
    goodbye: 'Adiós',
    loading: 'Cargando...',
    error: 'Ha ocurrido un error'
  },
  fr: { 
    welcome: 'Bienvenue', 
    goodbye: 'Au revoir',
    loading: 'Chargement...',
    error: 'Une erreur s\'est produite'
  },
  zh: {
    welcome: '欢迎',
    goodbye: '再见',
    loading: '加载中...',
    error: '发生错误'
  }
});

export const createTranslator = (translations: any, language: string) => {
  return (key: string) => {
    const translation = translations[language]?.[key];
    return translation || key;
  };
};

export const saveLanguagePreference = (language: string) => {
  localStorage.setItem('preferred_language', language);
};

export const updateDocumentLanguage = (language: string) => {
  document.documentElement.lang = language;
};

export const createLanguageConfig = () => ({
  en: { name: 'English', dir: 'ltr' as const, align: 'left' as const },
  ar: { name: 'العربية', dir: 'rtl' as const, align: 'right' as const },
  he: { name: 'עברית', dir: 'rtl' as const, align: 'right' as const },
  fa: { name: 'فارسی', dir: 'rtl' as const, align: 'right' as const },
  es: { name: 'Español', dir: 'ltr' as const, align: 'left' as const }
});

export const updateDocumentDirection = (direction: 'ltr' | 'rtl') => {
  document.documentElement.dir = direction;
};

export const updateTextAlignment = (align: 'left' | 'right') => {
  document.body.style.textAlign = align;
};

export const createCurrencyMap = () => ({
  'en-US': 'USD',
  'es-ES': 'EUR',
  'ja-JP': 'JPY',
  'ar-SA': 'SAR'
});

export const formatDateByLocale = (date: Date, locale: string) => {
  return new Intl.DateTimeFormat(locale).format(date);
};

export const formatNumberByLocale = (num: number, locale: string) => {
  return new Intl.NumberFormat(locale).format(num);
};

export const formatCurrencyByLocale = (amount: number, locale: string, currencyMap: any) => {
  const currency = currencyMap[locale] || 'USD';
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency
  }).format(amount);
};