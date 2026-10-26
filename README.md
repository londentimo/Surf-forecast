# Tulliniemi — Windguru forecast

Windguru GFS 13 km for Hanko spot 1914 now drives all day rankings. FMI WAM at
59.8086,22.9158 supplies wave height, period and direction where available.
The embedded WG blend is a separate comparison: it is not the GFS model.

## Open the snapshot

Open public/index.html in a browser. It contains the forecast fetched when
this package was built, clearly labelled as a saved snapshot. It cannot update
itself from a downloaded file; snapshots older than 24 hours stop recommending.

## Get a shareable URL with GitHub Pages

1. Create a GitHub repository with default branch `main`.
2. Add this folder's contents at the repository root, including
   `.github/workflows/forecast.yml`, `server.py`, and `index.html`.
3. Under Settings → Pages, choose GitHub Actions as the publishing source.
4. Under Actions, run “Refresh surf forecast”. Once the deployment succeeds,
   Settings → Pages shows the URL to share. Open that URL in Safari on iPhone.

The workflow fetches fresh data every three hours and publishes the page plus
forecast.json. Refresh on the page reads the latest published data; it does not
trigger a new GitHub job. Scheduled runs can be delayed or disabled by GitHub;
check the displayed fetch time and Actions status if updates stop.
A failed Windguru fetch fails the build rather than replacing it with FMI wind.
No credentials or third-party proxy are needed for this tested public GFS feed.
This workflow has been supplied, not deployed to your account.

## Run with a live server

Install Python 3.11+ and run `python3 server.py` in this folder. Open
http://localhost:8000. The server serves the page and /api/forecast from the
same origin, with a 30-minute shared fetch cache. PORT defaults to 8000.
A public Python host can run the same command and supply HTTPS. The built-in
HTTP server is intended for simple personal use; for larger deployments use
static publishing or a production web server.

## Forecast interpretation

- Suggestions use 06:00 inclusive to 22:00 exclusive in Europe/Helsinki.
  This is the requested time window, not a daylight calculation.
- Wind speed and direction drive the score. Strong E–SSE winds receive priority
  over the WAM mean wave direction. WAM makes only a small supporting contribution.
- “Good wind potential” is not a guarantee of breaking waves. Missing WAM is
  shown as unavailable, never as zero. No wave heights are extrapolated.
- All available Windguru GFS hours are included. Long-range forecasts are less
  certain; use the model run and fetch timestamp when comparing forecasts.
- GFS differs from the WG blended table and other Windguru models. The text
  service returned no forecast for the blend's model ID 100 in this test.
- Windguru text speeds are knots, converted to m/s. Dates follow Helsinki
  daylight saving time, including the repeated hour on 25 October 2026.

## Sources and upkeep

Windguru documented text service: https://micro.windguru.cz/help.php
Wind source: https://micro.windguru.cz/?s=1914&m=gfs&v=WSPD,WDEG,GUST
Spot: https://www.windguru.cz/1914
Waves: https://opendata.fmi.fi/wfs (FMI WAM point timevaluepair query)
Local comparison: https://www.aaltopoiju.fi/forecast.php?latlon=59.80861,22.91583
GitHub workflow docs: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

Windguru's text service is parsed conservatively: changed headings, units,
invalid dates or expired coverage fail explicitly. Its availability and format
are external dependencies. The public fetch was tested; this package makes no
claim of a redistribution licence or guaranteed API service level.
