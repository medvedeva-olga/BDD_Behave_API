# Тесты мокового Tasks API на behave (Gherkin, ru)

Проект приёмочных тестов для мокового сервиса Tasks API (`tools/mock_tasks_api.py`):
сценарии — Gherkin, шаги — Python + `requests`, ответы валидируются JSON Schema.


## Структура

```
D:\OLGA\QA_AUTOMATION\features\      # корень проекта: отсюда запускаем behave
├── behave.ini             # конфигурация behave (paths, base_url, логи, формат)
├── requirements.txt       # behave, requests, jsonschema
├── README.md
├── .vscode/launch.json    # конфигурации отладки для VS Code
├── docker-compose.yml     # мок Tasks API в Docker (порт 8090)
├── tools/                 # локальный мок-сервис (не входит в прогон behave)
│   ├── Dockerfile          # образ на python:3.12-slim, без зависимостей
│   ├── .dockerignore
│   └── mock_tasks_api.py  # мок Tasks API: задачи, дети, связи
├── api/                   # слой API: HTTP-клиент и endpoints
│   ├── client.py          # сессия, базовый URL, ретраи, токен, логи, методы эндпоинтов
│   └── endpoints.py       # константы путей API
├── models/                # модели и схемы ответов
│   ├── schemas.py         # JSON Schema ответов мока
│   └── __init__.py
└── features/              # базовый каталог behave (paths = features)
    ├── environment.py         # context.api, health-check, сброс и очистка
    ├── tasks_issues.feature      # создание, чтение, валидация задачи
    ├── tasks_relations.feature   # дети задачи и связи между задачами
    ├── tasks_delete.feature      # удаление, 409 при детях, force
    ├── tasks_admin.feature       # health, seed, reset, пустое состояние
    ├── tasks_auth.feature        # логин и режим проверки токена
    ├── support/                  # инфраструктура шагов, не HTTP-транспорт
    │   ├── data.py               # таблицы Gherkin -> payload, доступ к ответу
    │   └── cleanup.py            # реестр созданных ID и DELETE в after_scenario
    ├── steps/                    # только шаги Gherkin, по домену
    │   ├── common_steps.py       # статус, схема, поля, сообщения об ошибках
    │   ├── issues_steps.py       # задачи: создание, чтение, удаление
    │   ├── relations_steps.py    # дети и связи
    │   ├── admin_steps.py        # /health, /__admin/*
    │   └── auth_steps.py         # логин и переключение режима токена
    ├── simpleScheduling.feature      # черновики Gantt — исключены через exclude_re
    ├── parentScheduling.feature
    └── advancedScheduling.feature
```

### Почему так

| Слой | Где | Ответственность |
| --- | --- | --- |
| Транспорт | `api/client.py` | сессия, ретраи, таймауты, логи, Bearer-токен, `last_response`, методы эндпоинтов |
| Endpoints | `api/endpoints.py` | константы путей API |
| Модели / схемы | `models/schemas.py` | JSON Schema ответов мока |
| Шаги | `steps/*_steps.py` | тонкие обёртки: «что» пользователь делает, через клиент |

Доменные шаги (`я запрашиваю задачу с ID 1`) прячут URL внутри шага. Поэтому в
`.feature` нет ни одного адреса: при изменении эндпоинта правится один файл шагов.

## Быстрый старт

```bash
docker compose up -d --wait     # поднять мок и дождаться healthy
python -m behave                # весь набор
docker compose down             # остановить мок
```

Если мок не запущен, `before_all` остановит прогон с подсказкой, как его поднять.

## Установка

```bash
python -m pip install -r requirements.txt
```

## Запуск

Из корня проекта (`D:\OLGA\QA_AUTOMATION\features`):

```bash
python -m behave                             # все сценарии (пути из behave.ini)
python -m behave tasks_issues.feature  # только один файл
python -m behave --name "Создание"           # сценарии с подстрокой в названии
python -m behave --tags=@smoke                # быстрый набор (7 сценариев)
python -m behave --tags=@negative             # только негативные (13 сценариев)
python -m behave -f progress                  # компактные точки вместо дерева шагов
python -m behave -D base_url=http://127.0.0.1:8091  # мок на другом порту
```

Аргументы командной строки всегда важнее `behave.ini`.

> Запускать нужно из корня: `behave.ini` ищется только в текущем каталоге,
> домашнем и `%APPDATA%`, в родительские папки behave не поднимается.

## Конфигурация (`behave.ini`)

| Ключ | Значение | Зачем |
| --- | --- | --- |
| `paths` | `features` | где искать `.feature`, `steps/` и `environment.py` |
| `exclude_re` | `.*Scheduling[.]feature` | черновики Gantt лежат рядом, но в прогон не попадают |
| `default_format` | `pretty` | форматтер по умолчанию |
| `capture_stdout` / `capture_stderr` / `capture_log` | `false` | `print()` и логи идут сразу в консоль — удобно под отладчиком |
| `logging_level` | `INFO` | `DEBUG` показывает параметры запроса, payload и тело ответа |
| `show_source` / `show_timings` / `show_snippets` | `true` | файл:строка шага, тайминги, сниппеты для незарегистрированных шагов |
| `[behave.userdata] base_url` | `http://127.0.0.1:8090` | адрес мока |

Базовый URL читается в `features/environment.py` по приоритету:

1. `behave -D base_url=...`
2. переменная окружения `API_BASE_URL`
3. `[behave.userdata] base_url` из `behave.ini`
4. константа в `environment.py` (на случай запуска без конфига)

> `behave.ini` намеренно написан **только латиницей**: `configparser` читает его в
> системной кодировке (cp1251/cp1252 на Windows), и русские комментарии роняют
> запуск с `UnicodeDecodeError`. Русская документация — здесь, в README.

Проверить, что конфиг подхватился: `python -m behave -v` — в начале вывода будет
`Loading config defaults from ".../behave.ini"`.

## Изоляция сценариев

`features/environment.py` делает это автоматически:

- `before_all` — настраивает логи, создаёт `context.api` и проверяет `GET /health`;
- `before_scenario` — очищает токен, вызывает `POST /__admin/reset` (начальные
  4 задачи), выключает режим проверки токена и обнуляет реестр созданных ID;
- `after_scenario` — удаляет всё, что сценарий создал через API (см. ниже);
- `after_all` — закрывает HTTP-сессию.

Поэтому сценарии не зависят от порядка выполнения, а шаг
`Допустим мок находится в начальном состоянии` — явная страховка для чтения
сценария и для запуска без хуков.

## Очистка данных после сценария

Шаги создания не оставляют мусор в моке: каждый успешный `POST /api/issues`
регистрирует выданный сервером ID, а `after_scenario` удаляет эти задачи.

```
шаг создания → support/cleanup.py: register_created_issue(context, id)
                         ↓  context.created_issue_ids = [5, 6]
after_scenario → support/cleanup.py: cleanup_created_issues(context)
                         ↓  DELETE /api/issues/6?force=true
                         ↓  DELETE /api/issues/5?force=true
```

Правила уборки:

- удаляются только созданные сценарием задачи; seed-данные (id 1–4) не трогаются;
- порядок обратный порядку создания — сначала дочерние, потом родитель;
- `force=true`, чтобы задача с детьми тоже удалялась;
- 404 считается нормой (например, сценарий сам сбросил состояние или удалил задачу);
- любая другая ошибка пишется как `WARNING` и не роняет прогон;
- перед уборкой принудительно выключается режим проверки токена, чтобы
  `after_scenario` не зависел от состояния сценария.

Связи между задачами отдельного `DELETE` не имеют: они удаляются вместе с
задачей при `force=true`, а связи между seed-задачами убирает
`POST /__admin/reset` в начале следующего сценария.

Если добавляете шаг создания новой сущности, регистрируйте её ID так же — через
`register_created_issue` или аналогичный хелпер в `support/cleanup.py`.

## Отладка в VS Code

1. Открыть в VS Code каталог `D:\OLGA\QA_AUTOMATION\features` — корень проекта,
   где лежат `behave.ini` и `.vscode`.
2. Поставить точку останова на номер строки — в `api/client.py`,
   `features/steps/issues_steps.py` или `features/environment.py`.
3. **F5** (или `Run and Debug` → выбрать конфигурацию).

| Конфигурация | Что запускает |
| --- | --- |
| `behave: все сценарии` | весь прогон (пути из `behave.ini`) |
| `behave: текущий .feature` | только открытый `.feature` |
| `behave: сценарий по имени` | спросит название, по умолчанию «Создание» |
| `behave: только @smoke` | быстрый набор по тегу |
| `behave: только @negative` | только негативные сценарии |
| `mock: запустить локально` | `python tools/mock_tasks_api.py` без Docker |

`justMyCode: false` позволяет проваливаться внутрь behave, `PYTHONUTF8=1` — не
ломать кириллицу. Вывод идёт в `integratedTerminal`, логи видны сразу.

Полезные выражения в **Debug Console** на паузе:

```python
context.api.base_url
context.api.last_response.status_code
context.api.last_response.json()
context.api.last_response.request.url
context.api.token
```

Подробный обмен с API без отладчика:

```bash
python -m behave --logging-level DEBUG --name "Создание"
```

Логи клиента: `GET/POST <url>`, статус, тело ответа; при сетевом сбое — `WARNING`
о повторе.

## Что покрыто

Всего: **5 файлов, 33 сценария, 207 шагов**.

### `tasks_issues.feature`

| Проверка | Ожидание |
| --- | --- |
| `GET /api/issues/1` | 200, схема `issue_response`, `subject`, `parentIssue = null`, даты в `standards` |
| `POST /api/issues` (таблица «поле → значение») | 201, тело — число (id), затем `GET` по этому id отдаёт те же поля |
| `POST /api/issues` с `parentIssue = 1` | 201; созданная задача появляется в `/children` и имеет `parentIssue = 1` |
| `POST` с несуществующим родителем | 404 `Parent issue 999 not found` |
| `POST` без обязательного поля (структура сценария: 5 полей) | 400, сообщение содержит имя поля |
| `POST` с пустым `subject` | 400 |
| `POST` без дат | 201; `standards` содержит `null` для `startDate` и `endDate` |

### `tasks_relations.feature`

| Проверка | Ожидание |
| --- | --- |
| `GET /api/issues/1/children` | 200, схема `children_response`, 2 ребёнка (id 2 и 3) |
| `GET /api/issues/4/children` | 200, `count = 0` |
| `GET /api/issues/999/children` | 404 |
| `POST /api/issues/2/related` | 201, схема `relation`, `issueId = 2`, `relatedIssueId = 4` |
| Связь после создания | видна в `GET /__admin/state` (`relations = 1`) |
| Связь с несуществующей целью / от несуществующей задачи | 404 |

### `tasks_delete.feature`

| Проверка | Ожидание |
| --- | --- |
| `DELETE /api/issues/4?force=true` | 200, тело — id; затем `GET` → 404 |
| `DELETE /api/issues/4` (без force) | 200 — у задачи нет детей |
| `DELETE /api/issues/1` (без force) | 409, сообщение про детей; задача остаётся |
| `DELETE /api/issues/1?force=true` | 200; дети 2 и 3 отвязаны (`parentIssue = null`), связи удалены, задач в состоянии 3 |
| `DELETE /api/issues/999?force=true` | 404 |

### `tasks_admin.feature`

| Проверка | Ожидание |
| --- | --- |
| `GET /health` | 200, схема `health`, `{"status": "ok"}` |
| `GET /__admin/state` | 200, схема `state`, 4 начальные задачи |
| `POST /__admin/reset` после создания | снова 4 задачи; созданная задача недоступна |
| `POST /__admin/reset?empty=true` | 0 задач; `GET /api/issues/1` → 404 |
| Создание ребёнка в пустом состоянии | 404 `Parent issue 1 not found` |

### `tasks_auth.feature`

| Проверка | Ожидание |
| --- | --- |
| По умолчанию | `GET /api/issues/1` без токена → 200 |
| `require_auth=true` | без токена → 401 |
| Логин + запрос с токеном | 200, схема `login`, `access_token = mock-access-token` |
| `POST /__admin/reset` | выключает режим проверки токена (возвращает значение при запуске) |
| Логин с пустым паролем | 400 |

## Схемы ответов

Валидация через `jsonschema` (а не проверка пары ключей): проверяются обязательные
поля и типы, включая вложенные объекты. Лишние поля разрешены — мок может добавить
новое поле, и тесты не должны из-за этого падать.

| Схема | Где используется | Что проверяет |
| --- | --- | --- |
| `issue` | `state.issues` | `id`, `projectId`, `trackerId`, `statusId`, `priority`, `subject`, `parentIssue` (int/null), `standards` |
| `issue_response` | `GET /api/issues/<id>` | `{"issue": <issue>}` |
| `children_response` | `GET /api/issues/<id>/children` | `rows` (`rowId`, `subject`), `count` |
| `relation` | `POST /api/issues/<id>/related` | `id`, `issueId`, `relatedIssueId`, `relationType`, `delay` |
| `error` | 400/401/404/409 | `statusCode`, `message` |
| `login` | `POST /api/auth/login` | `access_token`, `token_type`, `expires_in` |
| `health` | `GET /health` | `status = "ok"` |
| `state` | `GET /__admin/state` | `issues` (схема `issue`), `relations` (схема `relation`) |

Сообщение об ошибке показывает схему, поле (например `standards/0/valueId`) и сам объект.

## Теги

| Тег | Сценарии | Зачем |
| --- | --- | --- |
| `@smoke` | 7 | быстрый набор: чтение seed-задачи, создание, дети, связь, удаление, health, авторизация |
| `@negative` | 13 | 400/401/404/409 |
| `@tasks` | все | принадлежность набору |
| `@issues`, `@relations`, `@delete`, `@admin`, `@auth` | по файлам | запуск отдельного домена |

```bash
python -m behave --tags=@smoke
python -m behave --tags=@negative
python -m behave --tags="not @negative"
python -m behave --tags=@delete
```

## Справочник шагов

Таблицы данных в сценариях — в формате «поле → значение»:

```gherkin
Когда я создаю задачу
  | поле      | значение |
  | subject   | Задача   |
  | priority  | 185      |
```

### `steps/common_steps.py`

| Шаг | Что делает |
| --- | --- |
| `Допустим мок находится в начальном состоянии` | `POST /__admin/reset` + выключает проверку токена |
| `Тогда статус ответа равен <N>` | статус + тело в сообщении об ошибке |
| `И ответ соответствует схеме "<name>"` | JSON Schema по имени из `models/schemas.py` |
| `И поле "<path>" равно "<value>"` | значение по пути (`issue.standards.0.valueId`) |
| `И поле "<path>" равно null` | проверка `null` |
| `И поле "<path>" равно числу <N>` | целое число |
| `И сообщение об ошибке содержит "<text>"` | подстрока в `message` |
| `И тело ответа содержит ID новой задачи` | тело — положительное число; id запоминается |
| `И тело ответа содержит ID <N>` | тело — число (для `DELETE`) |

### `steps/issues_steps.py`

| Шаг | Запрос |
| --- | --- |
| `Когда я запрашиваю задачу с ID <id>` | `GET /api/issues/{id}` |
| `Когда я запрашиваю созданную задачу` | `GET /api/issues/{created_id}` |
| `Когда я создаю задачу` (+ необязательная таблица) | `POST /api/issues` |
| `Когда я создаю задачу с родителем <id>` (+ таблица) | `POST /api/issues` с `parentIssue` |
| `Когда я создаю задачу без поля "<field>"` | `POST` без обязательного поля |
| `Когда я создаю задачу без дат` | `startDate` / `endDate` = `null` |
| `Когда я создаю задачу с пустым subject` | `POST` с `subject = ""` |
| `Когда я удаляю задачу с ID <id> с force` | `DELETE /api/issues/{id}?force=true` |
| `Когда я удаляю задачу с ID <id> без force` | `DELETE /api/issues/{id}` |
| `Тогда даты задачи равны "<start>" и "<end>"` | проверка `standards` |
| `Тогда поле "issue.id" равно ID созданной задачи` | сверка с запомненным id |

### `steps/relations_steps.py`

| Шаг | Запрос |
| --- | --- |
| `Когда я запрашиваю дочерние задачи для ID <id>` | `GET /api/issues/{id}/children` |
| `Тогда количество детей равно <N>` | `count` и длина `rows` |
| `Тогда список детей содержит ID <id>` | `rowId` среди `rows` |
| `Тогда список детей содержит созданную задачу` | `rowId = created_id` |
| `Когда я связываю задачу <a> с задачей <b> как "<type>"` | `POST /api/issues/{a}/related` |
| `Тогда связь соединяет задачи <a> и <b>` | проверка `issueId` / `relatedIssueId` |

### `steps/admin_steps.py`

| Шаг | Запрос |
| --- | --- |
| `Когда я запрашиваю здоровье сервиса` | `GET /health` |
| `Когда я запрашиваю состояние мока` | `GET /__admin/state` |
| `Когда я сбрасываю состояние мока` | `POST /__admin/reset` |
| `Когда я очищаю состояние мока` | `POST /__admin/reset?empty=true` |
| `Тогда количество задач в состоянии мока равно <N>` | длина `issues` |
| `Тогда состояние мока содержит задачу с ID <id>` | поиск по `issues[].id` |
| `Тогда количество связей в состоянии мока равно <N>` | длина `relations` |

### `steps/auth_steps.py`

| Шаг | Действие |
| --- | --- |
| `Допустим сервис требует токен` | `POST /__admin/config?require_auth=true` |
| `Допустим сервис не требует токен` | `POST /__admin/config?require_auth=false` |
| `Когда я авторизуюсь с логином "<u>" и паролем "<p>"` | `POST /api/auth/login`, токен запоминается |
| `Когда я авторизуюсь с логином "<u>" и пустым паролем` | `POST /api/auth/login` с `password = ""` |

## Как добавить сценарий

1. Дописать блок в нужный `.feature` в `features/` (новый файл там же подхватится).
2. Использовать существующие шаги из справочника. Если нужен новый:

| Что добавляете | Куда |
| --- | --- |
| действие с конкретной сущностью («запрашиваю связи задачи») | `features/steps/<домен>_steps.py` |
| универсальная проверка (схема, поле, статус) | `features/steps/common_steps.py` |
| вспомогательная функция без `@when/@then` | `features/support/` |

```python
# features/steps/issues_steps.py
@when("я запрашиваю задачу по subject {subject}")
def step_impl(context, subject):
    context.api.get("/api/issues", params={"subject": subject})
```

Если текст шага не совпадает с декоратором, behave покажет готовый сниппет
недостающего шага — можно скопировать его и дописать тело.

## Моковый сервис Tasks API

`tools/mock_tasks_api.py` — самодостаточный мок (stdlib, без зависимостей) для
интеграционных тестов `TasksService` на Node.js. Повторяет только те эндпоинты,
которые реально вызывает этот класс, и хранит состояние в памяти.

### Локально

```bash
python tools/mock_tasks_api.py                  # http://127.0.0.1:8090
python tools/mock_tasks_api.py --port 8091      # другой порт
python tools/mock_tasks_api.py --require-auth   # включить проверку Bearer-токена
```

### Запуск в Docker

```bash
docker compose up -d --build          # собрать и запустить: http://127.0.0.1:8090
docker compose ps                     # статус и health
docker compose logs -f mock-tasks     # логи запросов
docker compose down                   # остановить и удалить контейнер
```

Порт и режим авторизации переопределяются переменными окружения:

```bash
MOCK_PORT=8091 docker compose up -d
MOCK_REQUIRE_AUTH=1 docker compose up -d
```

```powershell
$env:MOCK_PORT = 8091
$env:MOCK_REQUIRE_AUTH = 1
docker compose up -d
```

Без compose:

```bash
docker build -t tasks-mock tools
docker run --rm -p 8090:8090 --name tasks-mock tasks-mock
```

Внутри контейнера мок слушает `0.0.0.0:8090` (иначе порт не пробросится),
снаружи — `http://127.0.0.1:8090`. Если Node-тесты тоже запускаются в compose,
обращайтесь по имени сервиса: `http://mock-tasks:8090`.

В образ встроен `HEALTHCHECK` (`GET /health` каждые 5 с), поэтому
`docker compose ps` показывает `healthy`. Дождаться готовности перед тестами:

```bash
docker compose up -d --wait
```

Состояние мока живёт в памяти контейнера: `docker compose restart` вернёт его
к начальным данным, а `POST /__admin/reset` сделает то же без перезапуска.

В коде на Node достаточно поменять хост:

```js
const TASKS_HOST = "http://127.0.0.1:8090";
```

`TasksService.auth()` возвращает `true` и не выставляет `Authorization`, поэтому
по умолчанию мок **не требует токен**. С `--require-auth` логин выдаёт
`{"access_token": "mock-access-token"}`, а запросы без `Bearer <token>` получают 401.
Режим можно переключать на ходу: `POST /__admin/config?require_auth=true`.

### Начальные данные

Мок стартует не с пустым состоянием: в нём уже есть 4 задачи, поэтому
`GET /api/issues/1` сразу отвечает 200, а `POST /api/issues` с `parentIssue: 1`
не падает с `Parent issue 1 not found`.

| id | subject | parentIssue | startDate | endDate |
| --- | --- | --- | --- | --- |
| 1 | `Project management` | `null` | 2026-01-01 | 2026-12-31 |
| 2 | `Requirements` | 1 | 2026-01-01 | 2026-01-31 |
| 3 | `API development` | 1 | 2026-02-01 | 2026-03-31 |
| 4 | `Release 1.0` | `null` | 2026-04-01 | 2026-04-30 |

У всех задач `projectId = 854`, `trackerId = 34`, `statusId = 13`, `priority = 185`.
Первая созданная задача получит id `5`.

`POST /__admin/reset` возвращает эти данные (удобно между тестами), а
`POST /__admin/reset?empty=true` очищает состояние полностью — если тесту нужен
гарантированно пустой мок. Сброс также возвращает режим авторизации к значению,
с которым мок запустили.

### Эндпоинты

| Метод | Путь | Ответ |
| --- | --- | --- |
| `POST` | `/api/auth/login` | 200, `{"access_token": "mock-access-token", "token_type": "Bearer", "expires_in": 3600}` |
| `POST` | `/api/issues` | 201, тело — **число** (id задачи), т.к. клиент делает `let issueId = data` |
| `GET` | `/api/issues/<id>` | 200, `{"issue": {..., "standards": [{"fieldId": "startDate", "valueId": ...}, {"fieldId": "endDate", "valueId": ...}]}}` |
| `DELETE` | `/api/issues/<id>?force=true` | 200, тело — **число** (id); 404 `{"statusCode": 404}` для несуществующей |
| `POST` | `/api/issues/<id>/related` | 201, `{"id", "issueId", "relatedIssueId", "relationType", "delay"}` |
| `GET` | `/api/issues/<id>/children` | 200, `{"rows": [{"rowId": 2, "subject": "..."}], "count": 1}` |
| `GET` | `/health` | 200, `{"status": "ok"}` — проверка готовности |
| `POST` | `/__admin/reset` | 200, `{"reset": true}` — вернуть начальные данные (`?empty=true` — очистить полностью) |
| `POST` | `/__admin/config?require_auth=true` | 200, `{"require_auth": true}` — включить/выключить проверку токена |
| `GET` | `/__admin/state` | 200, `{"issues": [...], "relations": [...]}` — для отладки |

### Правила поведения

| Что | Как работает мок |
| --- | --- |
| Обязательные поля `POST /api/issues` | `projectId`, `trackerId`, `statusId`, `priority`, `subject`; иначе 400 со списком пропущенных |
| Даты | `startDate` / `endDate` — строки или `null`; отдаются через `standards`, как ждёт `getTask()` |
| Родитель | `parentIssue` должен существовать, иначе 404 — так тест поймает неверный порядок создания; задача 1 есть в начальных данных |
| Дети | `GET /children` возвращает задачи, у которых `parentIssue` равен id; у задачи 1 сразу есть дети 2 и 3 |
| Удаление | без `force=true` при наличии детей — 409; с `force=true` удаляет задачу, отвязывает детей (`parentIssue = null`) и чистит её связи |
| Связи | `POST /related` проверяет существование обеих задач; `relationType` сохраняется как есть (`follows`, `""`) |
| Уникальность subject | не проверяется: клиент сам хранит соответствие subject → id и перезаписывает дубли |

Пример запроса:

```bash
curl -X POST http://127.0.0.1:8090/api/issues ^
  -H "Content-Type: application/json" ^
  -d "{\"projectId\":854,\"trackerId\":34,\"statusId\":13,\"priority\":185,\"subject\":\"Task 1\",\"startDate\":\"2026-11-01\",\"endDate\":\"2026-11-10\"}"
```

Между тестами состояние сбрасывается одним запросом:

```bash
curl -X POST http://127.0.0.1:8090/__admin/reset
```

Если нужен пустой мок (без начальных данных):

```bash
curl -X POST "http://127.0.0.1:8090/__admin/reset?empty=true"
```

## Особенности Windows

Вывод с кириллицей в консоли Windows (`cp1251`/`cp1252`) падает с `UnicodeEncodeError`.
`features/environment.py` принудительно переключает stdout/stderr на UTF-8,
поэтому отдельных действий не требуется. Если запускаете из другого окружения,
помогает переменная `PYTHONUTF8=1` (она же задана в `.vscode/launch.json`).
