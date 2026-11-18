"""Settings shared by the whole app. Change the app name here only."""

APP_NAME = "Housemade"
TAGLINE = "Chores, shopping and a shared fund for your flat"

# Used when no DATABASE_URL secret is set. The file is ignored by git.
LOCAL_DATABASE_URL = "sqlite:///housemade.db"

# How often parts of the screen that show shared data from the database
# ask again, so changes by flatmates show up (specs/live-updates.md).
REFRESH_SECONDS = 15

# Activity ideas (specs/activity-suggestions.md).
# Used when the visitor's location cannot be found from their IP address.
DEFAULT_PLACE = {"city": "Lisbon", "country": "PT", "lat": 38.7223, "lon": -9.1393}
