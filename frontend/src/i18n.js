import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

i18n
  // detect user language
  // learn more: https://github.com/i18next/i18next-browser-languageDetector
  .use(LanguageDetector)
  // pass the i18n instance to react-i18next.
  .use(initReactI18next)
  // init i18next
  // for all options read: https://www.i18next.com/overview/configuration-options
  .init({
    debug: true,
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false, // not needed for react as it escapes by default
    },
    resources: {
      fr: {
        translation: {
          'All games': 'Tous les jeux',
          'Page not found': 'Page non trouvée',
          'Visit Home': 'Visitez la page d\'accueil',
          'Name': 'Nom',
          'The Game': 'Le jeu',
          'Will end on': 'Se terminera le',
          'Thank you for participating in a game': 'Merci d\'avoir participé à un jeu',
          'Results will be published on': 'Les résultats seront publiés le',
          'Question': 'Question',
          'Start the game': 'Commencer le jeu',
          'Next question': 'Question suivante'
        }
      },
      ru: {
        translation: {
          'All games': 'Все игры',
          'My games': 'Мои игры',
          'Page not found': 'Страница не найдена',
          'Visit Home': 'Перейти на главную',
          'Name': 'Имя',
          'The Game': 'Игра',
          'Will end on': 'Закончится',
          'Thank you for participating in a game': 'Спасибо за участие в игре',
          'Results will be published on': 'Результаты будут опубликованы',
          'Question': 'Вопрос',
          'Start the game': 'Начать игру',
          'Welcome! Please enter or create a name and a password': 'Добро пожаловать! Пожалуйста введите или придумайте имя и пароль:',
          'Logout': 'Выйти',
          'Last score': 'Последние очки',
          'Status': 'Статус',
          'Never': 'Никогда',
          'Position': 'Место',
          'Last start': 'Последний старт',
          'Next question': 'Следующий вопрос'
        }
      }
    }
  });

export default i18n;
