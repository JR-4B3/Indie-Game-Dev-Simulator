# GameDev
Little GameDev (Tycoon) Game, Terminal only (for now) 

## Run

```bash
python main.py
```

The MVP starts on `1 Jan 1970`. Time speed can be changed while playing.

## Controls

- `N`: open the new game screen
- `E`: open the employee screen
- `Enter`: confirm/select in the new game or employee screen
- `Backspace`: go back from topic selection or close the current modal screen
- `Up` / `Down`: change the current selection
- `Right`: increase time speed on the main screen
- `Left`: decrease time speed on the main screen
- `Space`: pause/resume time
- `Q`: quit

Games take 8 in-game weeks to develop. Every game has `Gameplay`, `Graphics`,
`Audio`, and `Tech` points. Employees have the same four abilities and add those
points every development week.

On release, the game receives a press score and public score. These affect how
long the game sells, how much money it earns each week, and how many fans it gains
while it is still on the market. Employees cost monthly wages every 4 in-game weeks.
The activity feed only shows recent events; once old entries leave the screen they
are discarded to keep the terminal responsive.
