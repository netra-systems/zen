/**
 * I18n Test Components
 * All functions ≤8 lines for modular architecture compliance
 */

import React from 'react';
import { 
  createTranslations, 
  createTranslator, 
  saveLanguagePreference,
  updateDocumentLanguage,
  createLanguageConfig,
  updateDocumentDirection,
  updateTextAlignment,
  createCurrencyMap,
  formatDateByLocale,
  formatNumberByLocale,
  formatCurrencyByLocale
} from '../helpers/translation-helpers';
import { simulateNetworkDelay } from '../test-utils';

export const I18nSwitcherComponent = () => {
  const translations = createTranslations();
  const [language, setLanguage] = React.useState<keyof typeof translations>('en');
  const [isLoading, setIsLoading] = React.useState(false);
  const [hasError, setHasError] = React.useState(false);

  const t = createTranslator(translations, language);

  const handleLanguageChange = (newLanguage: keyof typeof translations) => {
    setLanguage(newLanguage);
    saveLanguagePreference(newLanguage);
    updateDocumentLanguage(newLanguage);
  };

  const simulateAction = async () => {
    setIsLoading(true);
    setHasError(false);
    await simulateNetworkDelay(200);
    setHasError(Math.random() > 0.5);
    setIsLoading(false);
  };

  React.useEffect(() => {
    saveLanguagePreference(language);
    updateDocumentLanguage(language);
  }, [language]);

  return (
    <div>
      <select
        data-testid="language-selector"
        value={language}
        onChange={(e) => handleLanguageChange(e.target.value as keyof typeof translations)}
      >
        <option value="en">English</option>
        <option value="es">Español</option>
        <option value="fr">Français</option>
        <option value="zh">中文</option>
      </select>
      
      <div data-testid="welcome-message">{t('welcome')}</div>
      <div data-testid="goodbye-message">{t('goodbye')}</div>
      
      <button onClick={simulateAction} disabled={isLoading}>
        Test Action
      </button>
      
      {isLoading && <div data-testid="loading-message">{t('loading')}</div>}
      {hasError && <div data-testid="error-message">{t('error')}</div>}
      
      <div data-testid="current-lang">{language}</div>
    </div>
  );
};

export const RTLLanguageComponent = () => {
  const languageConfig = createLanguageConfig();
  const [language, setLanguage] = React.useState('en');
  const [direction, setDirection] = React.useState<'ltr' | 'rtl'>('ltr');
  const [textAlign, setTextAlign] = React.useState<'left' | 'right'>('left');

  const updateLanguageSettings = (lang: string) => {
    const config = languageConfig[lang];
    if (!config) return;
    
    setDirection(config.dir);
    setTextAlign(config.align);
    updateDocumentDirection(config.dir);
    updateTextAlignment(config.align);
  };

  React.useEffect(() => {
    updateLanguageSettings(language);
  }, [language]);

  return (
    <div dir={direction} style={{ textAlign }}>
      <select
        data-testid="language-selector"
        value={language}
        onChange={(e) => setLanguage(e.target.value)}
      >
        {Object.entries(languageConfig).map(([code, config]) => (
          <option key={code} value={code}>
            {config.name}
          </option>
        ))}
      </select>
      
      <div data-testid="direction-indicator">{direction}</div>
      <div data-testid="text-align">{textAlign}</div>
      <div data-testid="sample-text">
        This is sample text that should align correctly
      </div>
      <div data-testid="numbers">1234567890</div>
    </div>
  );
};

export const LocaleFormattingComponent = () => {
  const currencyMap = createCurrencyMap();
  const [locale, setLocale] = React.useState('en-US');
  const [sampleDate] = React.useState(new Date('2024-01-15T10:30:00'));
  const [sampleNumber] = React.useState(1234567.89);
  const [sampleCurrency] = React.useState(1000.50);

  const formatDate = (date: Date) => formatDateByLocale(date, locale);
  const formatNumber = (num: number) => formatNumberByLocale(num, locale);
  const formatCurrency = (amount: number) => formatCurrencyByLocale(amount, locale, currencyMap);

  return (
    <div>
      <select
        data-testid="locale-selector"
        value={locale}
        onChange={(e) => setLocale(e.target.value)}
      >
        <option value="en-US">English (US)</option>
        <option value="es-ES">Español (ES)</option>
        <option value="ja-JP">日本語 (JP)</option>
        <option value="ar-SA">العربية (SA)</option>
      </select>
      
      <div data-testid="formatted-date">{formatDate(sampleDate)}</div>
      <div data-testid="formatted-number">{formatNumber(sampleNumber)}</div>
      <div data-testid="formatted-currency">{formatCurrency(sampleCurrency)}</div>
    </div>
  );
};