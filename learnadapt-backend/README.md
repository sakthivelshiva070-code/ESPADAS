# LearnAdapt AI - Backend (Flask)

Teacher-controlled adaptive learning API. Closed loop:
**Profile -> Performance -> Adaptation Engine -> AI Generation -> Validation -> Teacher Review -> Student -> Assessment -> repeat**

## Quick start
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env         # Mac/Linux: cp .env.example .env
python seed.py                 # optional demo data
python app.py                  # http://127.0.0.1:5000/api/health
pytest -v                      # run tests
```
No `ANTHROPIC_API_KEY`? The built-in demo generator is used (fractions topics give real questions).

## Project layout
| Path | Blueprint module |
|---|---|
| `routes/auth.py` | Authentication |
| `routes/classrooms.py` | Classroom |
| `routes/profiles.py` | Profile / accessibility |
| `routes/lessons.py` | Lesson |
| `routes/reviews.py` | Teacher Review (Adaptation Card) |
| `routes/activities.py` | Student dashboard + Assessment |
| `routes/analytics.py` | Analytics |
| `routes/support.py` | Support |
| `services/adaptation_engine.py` | Adaptation (rule-based, thresholds in `config.py`) |
| `services/ai_generation.py` | AI Generation (privacy-safe payload) |
| `services/validation.py` | Validation |
| `services/assessment.py` | Scoring |
| `services/pipeline.py` | Glues engine -> AI -> validation -> DB |

## API (all under `/api`, JWT: `Authorization: Bearer <token>`)
**Auth** `POST /auth/register` `POST /auth/login` `GET /auth/me` `POST /auth/logout`
**Classrooms** `POST /classrooms` (T) `GET /classrooms` `GET /classrooms/<id>/students` (T) `POST /classrooms/join` (S)
**Profiles** `GET|PUT /profile/me` (S) `GET|PUT /students/<id>/profile` (T)
**Lessons** `POST /lessons` (T) `GET /lessons?classroom_id=` (T) `POST /lessons/<id>/generate` (T)
**Review** `GET /reviews?status=pending` (T) `GET /reviews/<activity_id>` (T) `POST /reviews/<id>/approve|modify|reject` (T)
**Student** `GET /student/dashboard` `GET /activities` `GET /activities/<id>` `POST /activities/<id>/submit`
**Analytics** `GET /analytics/dashboard` `GET /analytics/classrooms/<id>` `GET /analytics/students/<id>` `GET /analytics/effectiveness` (T) `GET /analytics/me` (S)
**Support** `POST /support` (S) `GET /support` `PATCH /support/<id>` (T)

(T) = teacher only, (S) = student only.

## Team rules
- Never commit `.env` or `*.db`. Branch per feature, open a Pull Request into `main`.
- Teacher/student data access is enforced in `utils/helpers.py` - reuse those helpers in new routes.
- Metrics from `/analytics/effectiveness` are prototype/demo numbers unless backed by a real study.
