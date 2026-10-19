# Auto Power Calc — REST API

## Таблицы БД

### devices
| Поле | Тип | Описание |
|------|-----|----------|
| id_device | INTEGER PK | Идентификатор |
| name | VARCHAR(100) | Название |
| description | TEXT | Описание |
| status | VARCHAR(11) | черновик / опубликован / удален |
| image_url | VARCHAR(255) | URL изображения в MinIO |
| video_url | VARCHAR(255) | URL видео в MinIO |
| power | NUMERIC(6,2) | Мощность, Вт |
| resistance | NUMERIC(6,3) | Сопротивление, Ом |
| date_created | DATETIME | Дата создания |
| id_user | INTEGER FK | Создатель |
| date_formed | DATETIME | Дата публикации |
| date_completed | DATETIME | Дата удаления |

### users
| Поле | Тип | Описание |
|------|-----|----------|
| id_user | INTEGER PK | Идентификатор |
| username | VARCHAR(50) UNIQUE | Логин |
| password | VARCHAR(255) | Пароль |

### likes
| Поле | Тип | Описание |
|------|-----|----------|
| id_like | INTEGER PK | Идентификатор |
| id_user | INTEGER FK | Пользователь |
| id_device | INTEGER FK | Устройство |

---

## HTTP-методы

### Домен устройства

| Метод | URL | Описание |
|-------|-----|----------|
| GET | /api/devices?power_min=&power_max= | Список опубликованных с фильтрацией. Поле is_creator (0/1) — нужна ли кнопка удаления в плитке |
| GET | /api/devices/feed?id_device=&next=true | Лента: устройство + like_count + is_liked. Без id — первое опубликованное; с id_device — это устройство; next=true — следующее |
| GET | /api/devices/draft | Получить черновик текущего пользователя |
| POST | /api/devices | Создать черновик. Form: name, image (файл), video (файл) |
| PUT | /api/devices/{id_device} | Опубликовать. Form: power, resistance, description |
| DELETE | /api/devices/{id_device} | Soft delete (только свои). Ответ: 200, пустое тело |
| POST | /api/devices/{id_device}/likes | Лайк. Form: like (1=поставить, 0=отменить) |

### Домен пользователя

| Метод | URL | Описание |
|-------|-----|----------|
| POST | /api/register | Регистрация. Form: username, password |
| POST | /api/login | Аутентификация (заглушка) |
| POST | /api/logout | Деавторизация (заглушка) |
