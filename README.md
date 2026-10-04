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
| GET | /api/devices?power_min=&power_max= | Список опубликованных с фильтрацией. Поле is_creator (0/1) |
| GET | /api/device/{id_device}?next=true | Лента: одно устройство + like_count. next=true — следующее |
| GET | /api/device | Получить черновик текущего пользователя |
| POST | /api/device | Создать черновик. Form: name, image (файл), video (файл) |
| PUT | /api/device/{id_device} | Опубликовать. Form: power, resistance, description |
| DELETE | /api/device/{id_device} | Soft delete (только свои) |
| POST | /api/device/{id_device} | Лайк. Form: like (1=поставить, 0=отменить) |

### Домен пользователя

| Метод | URL | Описание |
|-------|-----|----------|
| POST | /api/register | Регистрация. Form: username, password |
| POST | /api/login | Аутентификация (заглушка) |
| POST | /api/logout | Деавторизация (заглушка) |

---

## Статусы устройств

```
черновик → опубликован  (PUT)
черновик → удален      (DELETE)
опубликован → удален   (DELETE)
```

Нельзя: вернуть в черновик, удалённый → любой.