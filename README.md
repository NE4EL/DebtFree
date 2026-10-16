# DebtFree — планировщик погашения долгов

Веб-приложение на Python, которое помогает спланировать погашение кредитов и долгов: рассчитывает платежи, строит график остатка, сравнивает стратегии погашения и показывает общую переплату, в том числе при досрочных платежах.

> **Статус:** этап проектирования (диаграммы + базовый отчёт). Код будет добавлен на следующем этапе.
> Полный отчёт с ТЗ и бизнес-логикой: [`docs/REPORT.md`](docs/REPORT.md)

## Содержание

1. [Функциональные возможности](#1-функциональные-возможности)
2. [Диаграмма вариантов использования (Use Case)](#2-диаграмма-вариантов-использования-use-case)
3. [Диаграмма бизнес-процесса (BPMN)](#3-диаграмма-бизнес-процесса-bpmn)
4. [ER-диаграмма базы данных](#4-er-диаграмма-базы-данных)
5. [Макет интерфейса](#5-макет-интерфейса)
6. [Дополнительные диаграммы](#6-дополнительные-диаграммы)
7. [Технологии и структура проекта](#7-технологии-и-структура-проекта)

---

## 1. Функциональные возможности

| № | Функция | Описание |
|---|---------|----------|
| F1 | Учёт долгов | Добавление, изменение и удаление кредитов: остаток, годовая ставка, минимальный платёж, срок, тип платежа |
| F2 | Ежемесячные платежи | Расчёт аннуитетного и дифференцированного платежа |
| F3 | График остатка долга | Помесячный график погашения (платёж, основной долг, проценты, остаток) |
| F4 | Сравнение стратегий | «Лавина», «Снежный ком» и базовый вариант «только минимальные платежи» |
| F5 | Общая переплата | Сумма процентов и срок погашения для каждой стратегии |
| F6 | Досрочное погашение | Пересчёт с разовым или регулярным досрочным платежом (сократить срок / снизить платёж) |
| F7 | Сценарии | Сохранение расчётов, чтобы вернуться к ним позже |

---

## 2. Диаграмма вариантов использования (Use Case)

Нотация UML: актёры — вне границы системы, варианты использования — внутри границы «Система DebtFree». Пунктирные стрелки: `«include»` — обязательное включение, `«extend»` — необязательное расширение (стрелка направлена от расширяющего варианта к базовому).

```mermaid
flowchart LR
    G["👤 Гость"]
    U["👤 Пользователь"]

    subgraph SYS["Система DebtFree"]
        direction TB
        UC1(["UC-1<br/>Зарегистрироваться / войти"])
        UC2(["UC-2<br/>Управлять долгами"])
        UC3(["UC-3<br/>Рассчитать ежемесячные платежи"])
        UC4(["UC-4<br/>Построить график остатка долга"])
        UC5(["UC-5<br/>Сравнить стратегии погашения"])
        UC6(["UC-6<br/>Рассчитать общую переплату"])
        UC7(["UC-7<br/>Смоделировать досрочное погашение"])
        UC8(["UC-8<br/>Сохранить сценарий"])
    end

    G --- UC1
    U --- UC1
    U --- UC2
    U --- UC4
    U --- UC5
    U --- UC7

    UC4 -. "«include»" .-> UC3
    UC5 -. "«include»" .-> UC3
    UC5 -. "«include»" .-> UC6
    UC7 -. "«extend»" .-> UC5
    UC8 -. "«extend»" .-> UC5
    U --- UC8
```

**Описание актёров**

| Актёр | Описание |
|-------|----------|
| Гость | Неавторизованный посетитель, может только зарегистрироваться или войти |
| Пользователь | Авторизованный пользователь, владелец своих долгов и сценариев |

**Краткая спецификация основных вариантов**

| ID | Название | Предусловие | Основной поток | Результат |
|----|----------|-------------|----------------|-----------|
| UC-2 | Управлять долгами | Пользователь авторизован | Открыть «Мои долги» → ввести данные → система проверяет и сохраняет | Долг добавлен / изменён / удалён |
| UC-5 | Сравнить стратегии | Есть ≥ 1 долг, задан бюджет ≥ суммы мин. платежей | Ввести бюджет → система моделирует все стратегии → вывод сравнительной таблицы | Срок и переплата по каждой стратегии |
| UC-7 | Досрочное погашение | Выполнено сравнение (UC-5) | Ввести сумму и эффект → пересчёт | Новый график, экономия переплаты |

---

## 3. Диаграмма бизнес-процесса (BPMN)

Процесс «Планирование погашения долгов» в нотации BPMN 2.0: две дорожки (lanes) внутри пула, события (круги), задачи (прямоугольники), исключающие шлюзы (ромбы). Диаграмма построена средствами Mermaid, поэтому изображение приближено к BPMN-нотации: дорожки показаны как вложенные группы.

```mermaid
%%{init: {'theme':'base','themeVariables': {'edgeLabelBackground':'#ffffff','lineColor':'#333333','textColor':'#000000'}}}%%
flowchart LR
    subgraph POOL["Пул: DebtFree — планирование погашения"]
        direction LR

        subgraph LU["Дорожка: Пользователь"]
            direction TB
            S(("Начало"))
            A1["Ввести данные<br/>долгов и бюджет"]
            A2["Просмотреть план<br/>и график остатка"]
            A3["Сравнить стратегии"]
            G3{"Нужен<br/>досрочный<br/>платёж?"}
            A4["Ввести сумму<br/>и тип эффекта"]
            A5["Сохранить сценарий"]
            E((("Конец")))
        end

        subgraph LS["Дорожка: Система DebtFree"]
            direction TB
            B1["Проверить<br/>введённые данные"]
            G1{"Данные<br/>корректны?"}
            G2{"Бюджет ≥ суммы<br/>мин. платежей?"}
            B2["Показать<br/>сообщение об ошибке"]
            B3["Рассчитать платежи<br/>и график остатка"]
            B4["Смоделировать стратегии:<br/>Лавина, Снежный ком, Базовая"]
            B5["Рассчитать срок<br/>и общую переплату"]
            B6["Пересчитать с учётом<br/>досрочного платежа"]
            B7["Записать сценарий в БД"]
        end
    end

    S --> A1 --> B1 --> G1
    G1 -- "Нет" --> B2 --> A1
    G1 -- "Да" --> G2
    G2 -- "Нет" --> B2
    G2 -- "Да" --> B3 --> A2 --> A3 --> B4 --> B5 --> G3
    G3 -- "Да" --> A4 --> B6 --> B5
    G3 -- "Нет" --> A5 --> B7 --> E

    %% цвет текста задаётся параметром color
    classDef event   fill:#ffffff,stroke:#333,stroke-width:2px,color:#000000;
    classDef gateway fill:#fff7d6,stroke:#8a5a00,color:#5c3b00;
    classDef task    fill:#e4f0ff,stroke:#1a3d6d,color:#0b2545;
    class S,E event;
    class G1,G2,G3 gateway;
    class A1,A2,A3,A4,A5,B1,B2,B3,B4,B5,B6,B7 task;

    %% заголовки дорожек и пула
    style POOL fill:#ffffff,stroke:#333,color:#000000
    style LU   fill:#f6f8fb,stroke:#1a3d6d,color:#0b2545
    style LS   fill:#f6fbf6,stroke:#2e7d32,color:#1b4d1f
```

| Элемент BPMN | Обозначение на диаграмме |
|--------------|--------------------------|
| Начальное событие | Круг «Начало» |
| Конечное событие | Двойной круг «Конец» |
| Задача (Task) | Прямоугольник |
| Исключающий шлюз (XOR) | Ромб с вопросом, исходящие потоки подписаны «Да» / «Нет» |
| Дорожки (Lanes) | Группы «Пользователь» и «Система DebtFree» внутри пула |

---

## 4. ER-диаграмма базы данных

Нотация: таблицы содержат поля с типами; **PK** — первичный ключ, **FK** — внешний ключ. Каждая стрелка начинается в поле-FK дочерней таблицы (точка, `N`) и заканчивается в конкретном поле-PK родительской таблицы (наконечник, `1`).

![ER-диаграмма DebtFree](docs/erd.svg)

**Перечень связей (поле → поле)**

| Дочернее поле (FK) | Родительское поле (PK) | Кратность | Смысл |
|--------------------|------------------------|-----------|-------|
| `debts.user_id` | `users.id` | N : 1 | Долг принадлежит пользователю |
| `scenarios.user_id` | `users.id` | N : 1 | Сценарий принадлежит пользователю |
| `scenarios.strategy_id` | `strategies.id` | N : 1 | Сценарий использует стратегию |
| `scenario_debts.scenario_id` | `scenarios.id` | N : 1 | Состав сценария (связь M:N с долгами) |
| `scenario_debts.debt_id` | `debts.id` | N : 1 | Состав сценария (связь M:N со сценариями) |
| `payment_schedule.scenario_id` | `scenarios.id` | N : 1 | Строка графика относится к сценарию |
| `payment_schedule.debt_id` | `debts.id` | N : 1 | Строка графика относится к долгу |
| `extra_payments.scenario_id` | `scenarios.id` | N : 1 | Досрочный платёж в рамках сценария |
| `extra_payments.debt_id` | `debts.id` | N : 1 | Досрочный платёж по долгу |

---

## 5. Макет интерфейса

Низкодетальный макет (wireframe) четырёх основных экранов: список долгов, форма добавления долга, сравнение стратегий, график остатка с досрочным погашением.

![Макет интерфейса DebtFree](docs/mockup.svg)

---

## 6. Дополнительные диаграммы

### 6.1. Архитектура (компонентная диаграмма)

```mermaid
flowchart LR
    subgraph CL["Клиент"]
        UI["Веб-интерфейс<br/>HTML + JS + Chart.js"]
    end
    subgraph SRV["Сервер (Python)"]
        API["REST API<br/>FastAPI"]
        SVC["Слой сервисов<br/>DebtService, ScenarioService"]
        CALC["Модуль расчётов<br/>calculator, strategies, simulator"]
        ORM["SQLAlchemy ORM"]
    end
    DB[("БД<br/>SQLite / PostgreSQL")]

    UI -- "HTTP / JSON" --> API
    API --> SVC
    SVC --> CALC
    SVC --> ORM
    ORM --> DB
```

### 6.2. Диаграмма классов (модуль расчётов)

```mermaid
classDiagram
    class Debt {
        +int id
        +str name
        +Decimal balance
        +Decimal annual_rate
        +Decimal min_payment
        +int term_months
        +PaymentType payment_type
        +monthly_rate() Decimal
    }
    class PaymentType {
        <<enumeration>>
        ANNUITY
        DIFFERENTIATED
    }
    class Strategy {
        <<abstract>>
        +order(debts) list~Debt~
    }
    class AvalancheStrategy {
        +order(debts) list~Debt~
    }
    class SnowballStrategy {
        +order(debts) list~Debt~
    }
    class MinimumOnlyStrategy {
        +order(debts) list~Debt~
    }
    class Calculator {
        +annuity_payment(balance, rate, months) Decimal
        +build_schedule(debt) list~PaymentRow~
    }
    class RepaymentSimulator {
        +simulate(debts, budget, strategy, extras) ScenarioResult
    }
    class ExtraPayment {
        +int month
        +Decimal amount
        +Effect effect
    }
    class PaymentRow {
        +int month_no
        +Decimal payment
        +Decimal principal_part
        +Decimal interest_part
        +Decimal balance_after
    }
    class ScenarioResult {
        +Decimal total_paid
        +Decimal total_interest
        +int months_to_payoff
    }

    Debt --> PaymentType
    Strategy <|-- AvalancheStrategy
    Strategy <|-- SnowballStrategy
    Strategy <|-- MinimumOnlyStrategy
    RepaymentSimulator ..> Strategy : использует
    RepaymentSimulator ..> Calculator : использует
    RepaymentSimulator o-- ExtraPayment : учитывает
    RepaymentSimulator --> ScenarioResult : создаёт
    ScenarioResult "1" *-- "many" PaymentRow : содержит
    Calculator ..> Debt
```

### 6.3. Диаграмма последовательности: сравнение стратегий

```mermaid
sequenceDiagram
    actor U as Пользователь
    participant UI as Веб-интерфейс
    participant API as REST API
    participant SIM as RepaymentSimulator
    participant DB as База данных

    U->>UI: Ввести бюджет, нажать «Рассчитать»
    UI->>API: POST /api/compare {budget}
    API->>DB: SELECT долги пользователя
    DB-->>API: список долгов
    alt бюджет < суммы мин. платежей
        API-->>UI: 422 Ошибка валидации
        UI-->>U: Сообщение «Бюджет слишком мал»
    else бюджет корректен
        loop для каждой стратегии
            API->>SIM: simulate(debts, budget, strategy)
            SIM-->>API: ScenarioResult
        end
        API-->>UI: 200 сравнительная таблица (срок, переплата)
        UI-->>U: Карточки стратегий и диаграмма
        opt пользователь сохраняет сценарий
            U->>UI: Нажать «Сохранить»
            UI->>API: POST /api/scenarios
            API->>DB: INSERT scenarios, payment_schedule
            DB-->>API: OK
            API-->>UI: 201 Created
        end
    end
```

---

## 7. Технологии и структура проекта

| Слой | Технологии |
|------|------------|
| Язык и расчёты | Python 3.11+, `decimal` |
| Backend | FastAPI, Pydantic |
| БД | SQLite (разработка) / PostgreSQL, SQLAlchemy, Alembic |
| Frontend | HTML, CSS, JavaScript, Chart.js |
| Тесты | pytest |

```text
debtfree/
├── app/
│   ├── api/            # маршруты FastAPI
│   ├── core/           # расчёты: calculator.py, strategies.py, simulator.py
│   ├── models/         # SQLAlchemy-модели
│   ├── schemas/        # Pydantic-схемы
│   └── services/       # бизнес-сервисы
├── frontend/           # статические страницы и JS
├── tests/              # unit-тесты расчётного модуля
├── docs/
│   ├── REPORT.md       # отчёт (ТЗ, бизнес-логика)
│   ├── erd.svg         # ER-диаграмма
│   └── mockup.svg      # макет интерфейса
└── README.md
```
