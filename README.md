# Сайт-визитка — Денис Дробышев

Личный сайт-портфолио: контакты, стек, проекты, опыт. Один статический
HTML-файл + немного CSS и ванильного JS. Без сборки, без фреймворков,
без зависимостей — открывается напрямую в браузере.

## Структура

```
index.html            # весь контент страницы
assets/styles.css     # стили (тёмная/светлая тема)
assets/script.js      # тема, фильтр проектов, анимации появления
assets/avatar.jpg     # фото профиля
assets/favicon.svg    # иконка вкладки
resume.html           # резюме (RU)
resume-en.html        # CV (EN)
```

## Как посмотреть локально

Просто открыть `index.html` в браузере. Либо поднять локальный сервер:

```bash
python -m http.server 8000
# http://localhost:8000
```

## Как опубликовать бесплатно (GitHub Pages)

1. Создать публичный репозиторий **`DenisDrobyshev.github.io`** на GitHub.
2. Запушить содержимое этой папки в ветку `main`.
3. Settings → Pages → Source: **Deploy from a branch**, ветка `main`, папка `/ (root)`.
4. Через минуту сайт будет доступен по адресу **https://denisdrobyshev.github.io**.

> Альтернативы в один клик: [Netlify Drop](https://app.netlify.com/drop),
> [Cloudflare Pages](https://pages.cloudflare.com/), [Vercel](https://vercel.com) —
> достаточно перетащить папку.

## Обновить контент

Проекты и тексты правятся прямо в `index.html`. Новый проект — скопировать
блок `<a class="proj" ...>` в секции «Все проекты» и поменять текст/ссылку.
