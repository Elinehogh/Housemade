# Activity suggestions from the weather

## Why

Picking what to do together is hard, and the best plan depends on the day:
a sunny Saturday in Lisbon is a beach day, a rainy one is a board game
evening. Housemade looks at the live weather where the flat is and suggests
things to do as a group, so nobody has to come up with ideas.

## What

- The Activities tab shows today's weather where the visitor is: the city,
  the temperature now, the highest temperature today, the chance of rain and
  a simple kind of weather (sunny, cloudy, foggy, rainy, snowy or stormy).
- The location comes from the visitor's IP address. If it cannot be found,
  the app uses Lisbon.
- The weather comes from Open-Meteo, and the location from ipinfo.io. Neither
  needs a key.
- Up to 3 ideas for today are shown under the weather. They come from fixed
  rules (more rules will be added later):
  - sunny or cloudy, dry and at least 22° today: a beach day first;
  - dry and at least 15°: things to do outside;
  - otherwise (rain, snow, storm, fog, a high chance of rain, or cold):
    things to do inside.
- Every idea has a name (1 to 40 characters), a cost for the whole flat
  (€0 to €1000, rounded to cents) and one sentence on why it fits today.
- Ideas that are already on the flat's list are not shown.
- Each idea has a button to add it to the flat's list, where people can vote.

## Out of scope

- Ideas written by an AI model (this would need a paid API key).
- Choosing another city by hand.
- Forecasts for later days.
- Checking who is free.

## Done when

- The rules are pure functions in `logic.py`, and all calls to outside
  services are in `services.py`.
- Tests cover reading the weather and the location (including a local or
  private IP address, a missing location and an unknown weather code), and
  the ideas for sunny, rainy and cold days, including skipping ideas already
  on the list.
- `uv run pytest` passes.
- The app still works when the weather or the location cannot be reached.
