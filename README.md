# Energy-Aware Daily Planner

A personal scheduling tool that replaces a manual nightly to-do list. You
input fixed commitments (class, gym, commute) and flexible tasks tagged
with a rough energy cost, and it outputs a schedule that places demanding
tasks into your high-energy windows and easy tasks into your low-energy
ones — instead of you guessing every night.

## Why this exists

Grounded in a real problem: a long commute plus school leaves me tired,
and a plain to-do list doesn't account for when I'm actually sharp versus
drained. This tries to fix that by treating "when" as seriously as "what."

## Architecture

```
models.py           Pydantic models — validation layer (rejects bad input
                     before it ever reaches the database)
database.py          SQLite persistence — one connection per call, no
                     import-time side effects
scheduler.py          The actual scheduling algorithm (see below)
main.py              FastAPI backend — exposes commitments/tasks/energy
                     windows as a REST API, plus POST /schedule
streamlit_app.py     Thin frontend — collects input, calls the API,
                     displays the result. No business logic lives here.
test_scheduler.py    pytest tests with real assertions, including tests
                     that confirm invalid input is rejected
```

The backend and frontend are separate processes talking over HTTP. That's
slightly more setup than putting everything in one Streamlit file, but it
means the scheduling logic is a real API that could drive any client
(a CLI, a script, a different frontend) — not something wired directly
into the UI code.

## The scheduling algorithm

1. **`compute_free_windows`** — subtracts your fixed commitments from the
   day, leaving the stretches of time you actually have available.
2. **`tag_windows` / `find_uncovered_gaps`** — splits those free stretches
   at every energy-window boundary, so each piece has one unambiguous
   energy level (or is flagged as uncovered, if you haven't mapped your
   energy curve for that part of the day).
3. **`build_schedule`** — greedily places tasks into windows:
   - High-energy tasks are placed first, since they have the fewest
     windows they can go in.
   - Each task prefers a window whose energy level exactly matches its
     cost.
   - If no exact match has room, it falls back to the closest available
     level rather than going unscheduled — so a demanding task will use a
     Medium window before being dropped entirely.
   - Among tied options, it picks the one that leaves the smallest
     leftover gap (best-fit), so larger windows stay open for later,
     bigger tasks.

This is a greedy heuristic, not a true optimizer — it doesn't backtrack or
try alternative orderings, so it isn't guaranteed to find the globally
best arrangement. For a single day's worth of tasks that's a reasonable
trade-off, and it's fast and easy to explain, which matters more here
than provable optimality.

## Running it

```bash
pip install -r requirements.txt

# terminal 1
uvicorn main:app --reload --port 8000

# terminal 2
streamlit run streamlit_app.py
```

Open the Streamlit URL it prints, add a few commitments, tasks, and
energy windows, then hit "Generate Schedule."

## Running the tests

```bash
pytest test_scheduler.py -v
```

## Known limitations / next steps

- Single day only — no recurring commitments or multi-day planning.
- The fallback logic is greedy, not globally optimal; a task placed early
  could block a better arrangement for a task placed later.
- No auth — this is a single-user local tool, not a deployed multi-user
  app.
- Energy windows and commitments are entered manually each time; a nice
  extension would be saving a default day layout.

https://github.com/user-attachments/assets/1e760ea6-3302-45ec-8dfb-2582d66b918f
