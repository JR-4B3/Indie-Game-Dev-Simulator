# GameDev
Little GameDev (Tycoon) Game, Terminal only (for now) 

## Run

```bash
python main.py
```

Load the default save file:

```bash
python main.py --load
```

Use a custom save file:

```bash
python main.py --load --save-file my_save.json
```

The game starts on `1 Jan 1976`. Time speed can be changed while playing.

## Controls

- `N`: open the new game screen
- `E`: open the employee screen
- `Enter`: confirm/select genre, topic, platform, focus, or employee
- `Backspace`: go back from topic selection or close the current modal screen
- `Up` / `Down`: change the current selection
- `Left` / `Right`: move across topic columns or adjust focus percentages
- `Right`: increase time speed on the main screen
- `Left`: decrease time speed on the main screen
- `Space`: pause/resume time
- `S`: save the current game to `gamedev_save.json`
- `Q`: quit

Games take 8 in-game weeks to develop. Every game chooses a `Genre`, `Topic`,
and active `Platform`. Every game has `Gameplay`, `Graphics`, `Audio`, and
`Tech` points. Employees have the same four abilities and add those points every
development week.

Genre/topic matches, your chosen focus percentages, hidden genre focus ideals,
target groups, platform audiences, platform preferences, and active platform user
bases affect review scores and sales. The data is based on the Mad Games Tycoon
2 guide where it fits this terminal version.

On release, the game receives a press score and public score. These affect how
long the game sells, how much money it earns each week, and how many fans it gains
while it is still on the market. Employees cost monthly wages every 4 in-game weeks.
The activity feed only shows recent events; once old entries leave the screen they
are discarded to keep the terminal responsive.
