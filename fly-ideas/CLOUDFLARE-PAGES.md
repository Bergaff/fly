# Публикация showcase в Cloudflare Pages

## Что уже подготовлено

Public build отделён от desktop app. Cloudflare получает только статическую папку `dist`:

- результаты серий82–90;
- интерактивную 3D-сцену с крыльями и действиями89E;
- научные ограничения и следующие шаги;
- условия использования и политику конфиденциальности.

Введённые посетителем движения остаются в браузере. Сервер, база данных, API-ключи и локальные результаты пользователя не используются.

Файлы Cloudflare:

- `wrangler.toml` задаёт Pages output `dist`;
- `public/_headers` добавляет CSP и защитные HTTP-заголовки;
- `public/_redirects` возвращает SPA entry для прямых ссылок;
- `npm run build:pages` включает только public showcase mode.

## Развёртывание через интерфейс Cloudflare

1. Войдите в Cloudflare Dashboard.
2. Откройте `Workers & Pages`.
3. Нажмите `Create application` → `Pages` → `Connect to Git`.
4. Подключите GitHub и выберите репозиторий `Bergaff/fly`.
5. Укажите production branch:
   - `arena/01a0b34a-fly`, если хотите немедленно опубликовать текущую рабочую ветку;
   - `main`, после merge текущей ветки в main.
6. В `Build settings` задайте:

| Поле | Значение |
|---|---|
| Framework preset | `Vite` или `None` |
| Root directory | `fly-ideas` |
| Build command | `npm run build:pages` |
| Build output directory | `dist` |
| Node version | `22` |

Для Node version добавьте environment variable `NODE_VERSION` со значением `22`, если Cloudflare не предлагает отдельное поле.

7. Нажмите `Save and Deploy`.
8. После сборки Cloudflare выдаст адрес вида `fly123-research.pages.dev` или другой свободный вариант имени.

Никакие секреты и Cloudflare API token для Git deployment не нужны.

## Если Cloudflare спрашивает имя проекта

Рекомендуемое имя:

```text
fly123-research
```

Если оно занято, выберите любое свободное имя. Оно влияет только на временный адрес `*.pages.dev`, но не на будущий custom domain.

## Что проверить после deploy

1. Открывается заголовок результатов серий82–90.
2. В таймлайне доступны:
   - взмахи крыльями;
   - потирание передних лап;
   - движение лап к голове;
   - вытягивание и убирание лап;
   - пауза.
3. Кнопка запуска проходит фазы observation → delay0,5с → repeat.
4. Работают ссылки `Результаты`, `Ограничения`, `Следующие шаги`, `Данные`.
5. Открываются условия использования и политика конфиденциальности.

## Домен пока подключать не нужно

Выбран режим «только Cloudflare Pages», поэтому сначала достаточно адреса `*.pages.dev`. Подключение `fly123.org` можно выполнить позднее отдельным шагом в `Custom domains`. GitHub TXT challenge для публикации на Cloudflare не нужен.

## Научное ограничение

Browser animation является deterministic explanatory surrogate. Она не запускает exact Python policy89E и не создаёт новый научный результат. Exact trial-level evidence остаётся в committed reports/extract/verifier.
